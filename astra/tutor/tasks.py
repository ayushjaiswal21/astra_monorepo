import json
import re
import requests
import google.generativeai as genai
from celery import shared_task
from django.conf import settings
from django.db import transaction
from .models import Course, Module, Lesson, Quiz, Question, Choice

# --- OLLAMA AI Configuration ---
OLLAMA_MODEL = "phi3:mini" # Changed from phi3:3.8b-mini-4k-instruct-q4_0 for faster inference

def call_ollama(prompt):
    """
    Sends a prompt to the Ollama API, cleans the response, and parses it as JSON.
    Raises exceptions on errors.
    """
    print(f"Sending prompt to Ollama: {prompt}")
    try:
        response = requests.post(settings.OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": f"{prompt}\n\nPlease ensure the output is only a single, valid JSON object as requested, with no additional text or markdown.",
            "stream": False,
            "options": {"num_predict": 2048}
        }, headers={"Content-Type": "application/json"}, timeout=120) # 120 second timeout
        
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx) 
        
        response_text = response.json().get('response', '')
        print(f"Received response from Ollama: {response_text}")

        cleaned_text = clean_llm_response(response_text)
        if not cleaned_text:
            raise ValueError("Received an empty response from Ollama.")

        return json.loads(cleaned_text)

    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama: {e}")
        # Re-raise as a more generic exception to be caught by the view or task
        raise ValueError(f"AI service request failed: {e}")
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON from Ollama: {e}")
        raise ValueError(f"AI service returned invalid JSON: {e}")

def clean_llm_response(response_text):
    """
    Cleans the raw text response from the LLM by finding all possible JSON objects
    and returning the first one that is valid.
    """
    # Regex to find all substrings that look like JSON objects
    json_pattern = re.compile(r'\{.*?\}', re.DOTALL)
    potential_matches = json_pattern.findall(response_text)

    if not potential_matches:
        print(f"Warning: Could not find any potential JSON objects in the response: {response_text}")
        return ""

    for match in potential_matches:
        try:
            # Try to parse the found substring as JSON
            json.loads(match)
            return match.strip()  # Return the first valid JSON object found
        except json.JSONDecodeError:
            continue  # Not a valid JSON object, try the next one

    print(f"Warning: Found potential JSON but failed to parse any of them: {response_text}")
    return ""

# --- Celery Tasks ---

# It's good practice to configure the client within the task
# to ensure it's initialized in the worker process.
genai.configure(api_key=settings.GEMINI_API_KEY)

@shared_task
def generate_modules_and_lessons(course_id, topic):
    """
    Background task to generate the full course structure.
    """
    course = None
    try:
        course = Course.objects.get(id=course_id)

        # --- Step 1: Generate Course Title and Description ---
        prompt_title_desc = f"""
        Generate a course title and a brief description for a course on the topic: '{topic}'.
        Provide the output as a single JSON object with two keys: "course_title" and "course_description".
        For example:
        {{
            "course_title": "Introduction to Python",
            "course_description": "A beginner-friendly course on Python."
        }}
        """
        title_desc_json = call_ollama(prompt_title_desc)
        
        # Update the placeholder course with the real title and description
        course.title = title_desc_json.get('course_title', course.title)
        course.description = title_desc_json.get('course_description', course.description)
        course.save()

        # --- Step 2: Generate Module Titles ---
        prompt_modules = f"""
        For a course titled '{course.title}', generate a list of 5 to 7 relevant module titles.
        Provide the output as a single JSON object with one key: "module_titles", which contains a list of strings.
        For example:
        {{
            "module_titles": ["Getting Started", "Data Structures", "Control Flow"]
        }}
        """
        module_titles_json = call_ollama(prompt_modules)
        module_titles = module_titles_json.get('module_titles', [])

        lessons_to_generate_async = []

        # --- Step 3 & 4: Loop through modules to get lessons and create everything ---
        for i, module_title in enumerate(module_titles):
            prompt_lessons = f"""
            For a module named '{module_title}' in a course about '{topic}', generate a concise learning objective and a list of 3-5 lesson titles.
            Provide the output as a single JSON object with two keys: "objective" and "lesson_titles".
            For example:
            {{
                "objective": "Understand the basics of Python syntax.",
                "lesson_titles": ["Variables and Data Types", "Your First Python Script"]
            }}
            """
            lessons_json = call_ollama(prompt_lessons)
            
            with transaction.atomic():
                module = Module.objects.create(
                    course=course,
                    title=module_title,
                    description=lessons_json.get('objective', ''),
                    order=i
                )

                for j, lesson_title in enumerate(lessons_json.get('lesson_titles', [])):
                    lesson = Lesson.objects.create(module=module, title=lesson_title, content="", order=j)
                    lessons_to_generate_async.append(lesson.id)
        
        # --- Step 5: Trigger async tasks for lesson content generation ---
        for lesson_id in lessons_to_generate_async:
            generate_lesson_content.delay(lesson_id)

        return f"Successfully generated modules and lessons for course {course_id}."

    except Exception as e:
        # If something goes wrong, update the course description with an error
        if course:
            course.description = f"### Error Generating Course Content\n\nWe encountered an issue while building this course: `{str(e)}`\n\nThis is often a temporary issue with the AI service. Please try deleting this course and creating it again in a few moments."
            course.save()
        return f"Failed to generate modules and lessons for course {course_id}: {str(e)}"



@shared_task
def generate_lesson_content(lesson_id):
    """
    Background task to generate content and a quiz for a single lesson.
    """
    lesson = None
    try:
        lesson = Lesson.objects.get(id=lesson_id)
        if lesson.content:
            return f"Lesson {lesson_id} already has content."

        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"""
        You are an expert educator. Generate the content for a lesson titled \"{lesson.title}\" within the module \"{lesson.module.title}\".
        The module's objective is: {lesson.module.description}
        
        The output must be a JSON object with the following structure:
        - \"lesson_content\": The full lesson content in Markdown format. It should be detailed, clear, and easy to understand.
        - \"quiz_question\": A multiple-choice question to test the core concept of the lesson.
        - \"options\": A list of 4 strings representing the choices for the multiple-choice question.
        - \"answer\": The correct choice from the options list.
        """
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('`', '').replace('json', '', 1)
        ai_response_json = json.loads(cleaned_response)

        with transaction.atomic():
            lesson.content = ai_response_json['lesson_content']
            lesson.save()

            quiz = Quiz.objects.create(lesson=lesson, title=f"Quiz for {lesson.title}")
            question = Question.objects.create(
                quiz=quiz,
                question_text=ai_response_json['quiz_question'],
                order=0
            )
            for choice_text in ai_response_json['options']:
                Choice.objects.create(
                    question=question,
                    choice_text=choice_text,
                    is_correct=(choice_text == ai_response_json['answer'])
                )
        return f"Successfully generated content for lesson {lesson_id}."

    except Lesson.DoesNotExist:
        return f"Error: Lesson with ID {lesson_id} not found."
    except Exception as e:
        if lesson:
            lesson.content = f"### Error Generating Content\n\nWe encountered an issue while preparing this lesson: `{str(e)}`\n\nPlease try refreshing later or contact support."
            lesson.save()
        return f"Failed to generate content for lesson {lesson_id}: {str(e)}"