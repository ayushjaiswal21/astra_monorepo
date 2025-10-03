import json
import re
import google.generativeai as genai
from celery import shared_task
from django.conf import settings
from django.db import transaction
from .models import Course, Module, Lesson, Quiz, Question, Choice

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


@shared_task
def generate_course_content(course_id, topic):
    """
    Background task to generate the full course structure, content, and quizzes in a single API call.
    """
    course = None
    try:
        course = Course.objects.get(id=course_id)

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        prompt = f'''
        You are an expert instructional designer. Generate a complete course on the topic: '{topic}'.
        The output must be a single, valid JSON object.
        The JSON structure should be:
        {{
          "course_title": "Course Title",
          "course_description": "A brief description of the course.",
          "modules": [
            {{
              "module_title": "Module 1 Title",
              "module_objective": "The learning objective for this module.",
              "lessons": [
                {{
                  "lesson_title": "Lesson 1.1 Title",
                  "lesson_content": "The full lesson content in Markdown format. It should be detailed, clear, and easy to understand.",
                  "quiz": {{
                    "question": "A multiple-choice question to test the core concept of the lesson.",
                    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
                    "answer": "The correct option from the list."
                  }}
                }}
              ]
            }}
          ]
        }}

        Generate 3-5 modules for the course.
        Each module should have 2-4 lessons.
        Ensure the JSON is well-formed and contains all the requested fields.
        '''

        response = model.generate_content(prompt)
        ai_response_json = clean_gemini_response(response.text)

        with transaction.atomic():
            # Update course title and description
            course.title = ai_response_json.get('course_title', course.title)
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
                    lesson = Lesson.objects.create(
                        module=module,
                        title=lesson_data.get('lesson_title', 'Untitled Lesson'),
                        content=lesson_data.get('lesson_content', ''),
                        order=j
                    )

                    quiz_data = lesson_data.get('quiz')
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