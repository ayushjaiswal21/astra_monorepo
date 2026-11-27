import json
import logging
import re
import httpx
import google.generativeai as genai
from celery import shared_task
from django.conf import settings
from django.db import transaction
from .models import Course, Module, Lesson, Quiz, Question, Choice
from .prompts import (
    get_course_generation_prompt,
    get_structure_generation_prompt,
    get_lesson_content_prompt,
)

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
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["response"]


def generate_structure_via_ollama(topic):
    """Asks Ollama for the course structure (titles only) and returns the parsed dict."""
    raw_text = call_ollama(get_structure_generation_prompt(topic))
    return clean_gemini_response(raw_text)


def generate_structure_via_gemini(topic):
    """Fallback: asks Gemini for the full course (structure + content) in one call."""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    response = model.generate_content(get_course_generation_prompt(topic))
    return clean_gemini_response(response.text)


@shared_task
def generate_course_content(course_id, topic):
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

        structure_only = True
        try:
            ai_response_json = generate_structure_via_ollama(topic)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError, ValueError, KeyError) as e:
            logger.warning(
                "Ollama unreachable at %s, falling back to Gemini-only structure generation: %s",
                settings.OLLAMA_URL, e,
            )
            ai_response_json = generate_structure_via_gemini(topic)
            structure_only = False  # Gemini fallback already includes lesson content + quizzes

        genai.configure(api_key=settings.GEMINI_API_KEY)
        content_model = genai.GenerativeModel('gemini-1.5-flash-latest')
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
                        # Ollama only gave us the title; ask Gemini for this lesson's content.
                        content_response = content_model.generate_content(
                            get_lesson_content_prompt(course_title, module.title, lesson_title)
                        )
                        lesson_content_json = clean_gemini_response(content_response.text)
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

    except Exception as e:
        if course:
            course.description = f"### Error Generating Course Content\n\nWe encountered an issue while building this course: `{str(e)}`\n\nPlease try deleting this course and creating it again."
            course.save()
        return f"Failed to generate content for course {course_id}: {str(e)}"
