import json
import logging
import re
import httpx
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from celery import shared_task
from pydantic import ValidationError
from django.conf import settings
from django.db import transaction
from .models import Course, Module, Lesson, Quiz, Question, Choice
from .prompts import (
    get_course_generation_prompt,
    get_structure_generation_prompt,
    get_lesson_content_prompt,
)
from .schemas import StructureResponse, CourseGenerationResponse, LessonContentResponse
from .mastery import difficulty_for_score

logger = logging.getLogger(__name__)


def clean_gemini_response(response_text):
    """
    Cleans the raw text response from the Gemini API by finding the first valid JSON object.
    """
    # Find the first '{' and the last '}' to extract the JSON part.
    try:
        start_index = response_text.index('{')
        end_index = response_text.rindex('}') + 1
        json_text = response_text[start_index:end_index]
        return json.loads(json_text)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error cleaning/parsing Gemini response: {e}")
        raise ValueError(f"AI service returned invalid JSON: {response_text}")


def call_ollama(prompt, timeout=30):
    """
    Calls the local Ollama server to generate text. Returns the generated text (str).
    Raises httpx.HTTPError/httpx.TimeoutException/httpx.ConnectError on failure, so
    callers can catch those and fall back to another provider.
    """
    response = httpx.post(
        settings.OLLAMA_URL,
        json={
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["response"]


def call_openrouter(prompt, timeout=60):
    """
    Calls OpenRouter's free tier (OpenAI-chat-completions-compatible, no credit
    card required - see settings.OPENROUTER_MODEL). Returns the generated text
    (str). Raises httpx.HTTPError/httpx.TimeoutException on failure, same as
    call_ollama, so callers can catch those and fall back to another provider.
    Raises RuntimeError immediately if no API key is configured, so callers can
    skip straight past this provider without wasting a network round-trip.
    """
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
        json={
            "model": settings.OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def generate_structure_via_ollama(topic, difficulty="intermediate"):
    """Asks Ollama for the course structure (titles only) and returns the validated dict."""
    raw_text = call_ollama(get_structure_generation_prompt(topic, difficulty))
    parsed = clean_gemini_response(raw_text)
    return StructureResponse.model_validate(parsed).model_dump()


def generate_structure_via_openrouter(topic, difficulty="intermediate"):
    """Same structure-only prompt as Ollama, answered by OpenRouter's free tier instead."""
    raw_text = call_openrouter(get_structure_generation_prompt(topic, difficulty))
    parsed = clean_gemini_response(raw_text)
    return StructureResponse.model_validate(parsed).model_dump()


def generate_structure_via_gemini(topic, difficulty="intermediate"):
    """Fallback: asks Gemini for the full course (structure + content) in one call."""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    response = model.generate_content(get_course_generation_prompt(topic, difficulty))
    parsed = clean_gemini_response(response.text)
    return CourseGenerationResponse.model_validate(parsed).model_dump()


def generate_structure_via_openrouter_full(topic, difficulty="intermediate"):
    """Fallback: asks OpenRouter for the full course (structure + content) in one
    call, same prompt/shape as generate_structure_via_gemini - used when neither
    Ollama nor Gemini are usable (e.g. a free host with no Gemini billing set up
    and nowhere to run Ollama)."""
    raw_text = call_openrouter(get_course_generation_prompt(topic, difficulty))
    parsed = clean_gemini_response(raw_text)
    return CourseGenerationResponse.model_validate(parsed).model_dump()


def generate_lesson_content_text(prompt):
    """
    Generates one lesson's content + quiz. Tries Gemini first (if configured),
    falls back to OpenRouter on any Gemini failure (quota, no key, transient
    error) or if Gemini was never configured - mirrors the Ollama/OpenRouter/
    Gemini fallback chain used for the course structure, but Gemini is tried
    first here since it was already the one always used for lesson content.
    Raises whatever the last attempted provider raised if all fail.
    """
    has_real_gemini_key = bool(settings.GEMINI_API_KEY) and settings.GEMINI_API_KEY != 'your-gemini-api-key-placeholder'
    if has_real_gemini_key:
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            return model.generate_content(prompt).text
        except Exception as e:
            logger.warning(
                "Gemini lesson-content call failed (falling back to OpenRouter if configured): %s", e,
            )
            if not settings.OPENROUTER_API_KEY:
                raise
    return call_openrouter(prompt)


def _lookup_difficulty(session_key, skill_name):
    """Looks up the SkillMastery score for (session_key, skill_name) and maps it to a
    difficulty label. Returns "intermediate" if there's no session_key or no row yet."""
    if not session_key:
        return "intermediate"
    from .models import SkillMastery  # local import: avoid app-loading-order issues

    mastery = SkillMastery.objects.filter(session_key=session_key, skill_name=skill_name).first()
    return difficulty_for_score(mastery.score if mastery else None)


@shared_task
def generate_course_content(course_id, topic, session_key=None):
    """
    Background task to generate the full course structure, content, and quizzes.

    Dual-LLM flow: Ollama (local) generates the course/module/lesson structure first;
    Gemini then generates the actual content for each lesson. If Ollama is unreachable
    (not installed/running), falls back to a single Gemini call that produces the
    structure AND content together, so the pipeline keeps working end-to-end.
    """
    course = None
    try:
        course = Course.objects.get(id=course_id)

        # Overall course difficulty, driven by the learner's mastery of this topic so far
        # (if any). Per-lesson difficulty is re-derived below from each lesson's own skill.
        course_difficulty = _lookup_difficulty(session_key, topic)

        structure_only = True
        structure_errors = []
        ai_response_json = None
        try:
            ai_response_json = generate_structure_via_ollama(topic, course_difficulty)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError, ValueError, KeyError, ValidationError) as e:
            structure_errors.append(("Ollama", e))

        if ai_response_json is None and settings.OPENROUTER_API_KEY:
            try:
                ai_response_json = generate_structure_via_openrouter(topic, course_difficulty)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError, RuntimeError, ValueError, KeyError, ValidationError) as e:
                structure_errors.append(("OpenRouter", e))

        if ai_response_json is None:
            # Last resort: one Gemini call that produces structure + content +
            # quizzes together, instead of Ollama/OpenRouter's structure-only
            # response (which needs a second call per lesson below).
            ai_response_json = generate_structure_via_gemini(topic, course_difficulty)
            structure_only = False

        if structure_errors:
            logger.warning(
                "Structure generation fell through %d provider(s) before succeeding: %s",
                len(structure_errors),
                "; ".join(f"{name}: {err}" for name, err in structure_errors),
            )

        course_title = ai_response_json.get('course_title', course.title)

        with transaction.atomic():
            # Update course title and description
            course.title = course_title
            course.description = ai_response_json.get('course_description', course.description)
            course.save()

            # Create modules, lessons, and quizzes
            for i, module_data in enumerate(ai_response_json.get('modules', [])):
                module = Module.objects.create(
                    course=course,
                    title=module_data.get('module_title', 'Untitled Module'),
                    description=module_data.get('module_objective', ''),
                    order=i
                )

                for j, lesson_data in enumerate(module_data.get('lessons', [])):
                    lesson_title = lesson_data.get('lesson_title', 'Untitled Lesson')

                    if structure_only:
                        # Ollama/OpenRouter only gave us the title; ask for this
                        # lesson's content (Gemini first, OpenRouter fallback).
                        lesson_difficulty = _lookup_difficulty(session_key, lesson_title)
                        content_text = generate_lesson_content_text(
                            get_lesson_content_prompt(course_title, module.title, lesson_title, lesson_difficulty)
                        )
                        lesson_content_json = LessonContentResponse.model_validate(
                            clean_gemini_response(content_text)
                        ).model_dump()
                    else:
                        # Gemini fallback already produced content + quiz for every lesson.
                        lesson_content_json = lesson_data

                    lesson = Lesson.objects.create(
                        module=module,
                        title=lesson_title,
                        content=lesson_content_json.get('lesson_content', ''),
                        order=j
                    )

                    quiz_data = lesson_content_json.get('quiz')
                    if quiz_data:
                        quiz = Quiz.objects.create(lesson=lesson, title=f"Quiz for {lesson.title}")
                        question = Question.objects.create(
                            quiz=quiz,
                            question_text=quiz_data.get('question', ''),
                            order=0
                        )
                        for choice_text in quiz_data.get('options', []):
                            Choice.objects.create(
                                question=question,
                                choice_text=choice_text,
                                is_correct=(choice_text == quiz_data.get('answer'))
                            )

        return f"Successfully generated all content for course {course_id}."

    except ResourceExhausted as e:
        # Gemini 429 (quota/rate-limit). Give a specific, actionable message instead
        # of the generic failure below; no DB rows are created before this point
        # (lesson/module creation is inside the atomic block further down), so
        # nothing is orphaned.
        logger.error("Gemini quota exceeded while generating course %s: %s", course_id, e)
        if course:
            course.description = "### AI Quota Exceeded\n\nThe AI service's usage quota has been reached. Please try generating this course again in a few minutes."
            course.save()
        return f"Failed to generate content for course {course_id}: AI quota exceeded"

    except ValidationError as e:
        bad_fields = ", ".join(".".join(str(p) for p in err["loc"]) for err in e.errors())
        logger.error(
            "AI response for course %s failed schema validation (field(s): %s): %s",
            course_id, bad_fields, e, exc_info=True,
        )
        if course:
            course.description = "### Error Generating Course Content\n\nWe encountered an issue while building this course.\n\nPlease try deleting this course and creating it again."
            course.save()
        return f"Failed to generate content for course {course_id}"

    except Exception as e:
        logger.error("Failed to generate content for course %s: %s", course_id, e, exc_info=True)
        if course:
            course.description = "### Error Generating Course Content\n\nWe encountered an issue while building this course.\n\nPlease try deleting this course and creating it again."
            course.save()
        return f"Failed to generate content for course {course_id}"
