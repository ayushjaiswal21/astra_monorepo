# astra/tutor/prompts.py

"""
Centralized location for all AI prompt generation.
This helps to avoid code duplication and makes prompts easier to manage.
"""

def get_course_generation_prompt(topic):
    """Returns the formatted prompt for generating a full course structure."""
    return f'''
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

def get_test_generation_prompt(course_title):
    """Returns the formatted prompt for generating a comprehensive test for a course."""
    return f"""
    You are a helpful quiz generation assistant.
    Generate a comprehensive test for the course titled '{course_title}'.
    The test should contain a mix of 5 multiple-choice questions and 2 coding problems.
    The difficulty level should be medium.
    You MUST respond with ONLY a valid JSON object.
    The JSON object must follow this exact format:
    {{
      "questions": [
        {{
          "question_type": "mcq",
          "question_text": "What is the capital of France?",
          "options": [
            "A) London",
            "B) Berlin",
            "C) Paris",
            "D) Madrid"
          ],
          "correct_answer": "C"
        }},
        {{
          "question_type": "coding",
          "question_text": "### Sum Calculator\n\n**Scenario:** You are given two integers, a and b. **Task:** Write a function that returns their sum.\n\n**Input Format:** Two integers, a and b.\n\n**Output Format:** A single integer representing the sum.\n\n**Example:**\n\n- **Input:** a = 2, b = 3\n- **Output:** 5",
          "starter_code": "def solve(a, b):\n  # Your code here\n  return 0",
          "test_cases": [
            {{"input": "2 3", "expected_output": "5"}},
            {{"input": "-1 5", "expected_output": "4"}}
          ]
        }}
      ]
    }}
    """
