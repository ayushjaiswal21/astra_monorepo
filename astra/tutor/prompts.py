# astra/tutor/prompts.py

"""
Centralized location for all AI prompt generation.
This helps to avoid code duplication and makes prompts easier to manage.
"""

_DIFFICULTY_GUIDANCE = {
    "beginner": (
        "Target audience: complete beginners. Avoid jargon, define any technical term the "
        "first time it is used, and prefer simple everyday analogies over formal definitions."
    ),
    "intermediate": (
        "Target audience: learners with some basic familiarity with the subject. You can use "
        "standard terminology, but still briefly clarify any non-obvious concept."
    ),
    "advanced": (
        "Target audience: experienced learners. Use precise technical terminology freely, cover "
        "edge cases and nuance, and prefer depth over hand-holding explanations."
    ),
}

_NO_FENCE_INSTRUCTION = (
    "Respond with ONLY the raw JSON object - no other text, and no markdown code fences "
    "(do not wrap the JSON in ```json or ``` blocks)."
)

_QUIZ_QUALITY_INSTRUCTION = (
    "The quiz must have exactly one unambiguously correct option and three other options "
    "that are genuinely plausible distractors (believable mistakes someone learning the "
    "material could make), not random trivia or obviously-wrong filler."
)

_LESSON_LENGTH_INSTRUCTION = (
    "The lesson content should be roughly 300-600 words of Markdown, structured as: a short "
    "introduction, 2-4 subsections (each with its own heading) covering the core ideas, a "
    "worked example, and a brief closing summary."
)


def _difficulty_text(difficulty):
    return _DIFFICULTY_GUIDANCE.get(difficulty, _DIFFICULTY_GUIDANCE["intermediate"])


def get_course_generation_prompt(topic, difficulty="intermediate"):
    """Returns the formatted prompt for generating a full course structure."""
    return f'''
    You are an expert instructional designer. Generate a complete course on the topic: '{topic}'.
    Difficulty level: {difficulty}. {_difficulty_text(difficulty)}

    The output must be a single, valid JSON object. {_NO_FENCE_INSTRUCTION}
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
              "lesson_content": "The full lesson content in Markdown format.",
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

    Generate 3-5 modules for the course. Each module should have 2-4 lessons.
    {_LESSON_LENGTH_INSTRUCTION}
    {_QUIZ_QUALITY_INSTRUCTION}
    Ensure the JSON is well-formed and contains all the requested fields.
    '''


def get_structure_generation_prompt(topic, difficulty="intermediate"):
    """Returns the prompt asking for ONLY the course/module/lesson structure (titles), no content."""
    return f'''
    You are an expert instructional designer. Plan the structure of a complete course on the topic: '{topic}'.
    Difficulty level: {difficulty}. {_difficulty_text(difficulty)}
    {_NO_FENCE_INSTRUCTION}
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
              "lesson_title": "Lesson 1.1 Title"
            }}
          ]
        }}
      ]
    }}

    Do NOT include lesson content or quizzes, titles only.
    Generate 3-5 modules for the course.
    Each module should have 2-4 lessons.
    '''


def get_lesson_content_prompt(course_title, module_title, lesson_title, difficulty="intermediate"):
    """Returns the prompt asking Gemini to generate the content + quiz for a single lesson."""
    return f'''
    You are an expert instructional designer writing a lesson for the course '{course_title}',
    module '{module_title}', lesson '{lesson_title}'.
    Difficulty level: {difficulty}. {_difficulty_text(difficulty)}
    {_NO_FENCE_INSTRUCTION}
    The JSON structure should be:
    {{
      "lesson_content": "The full lesson content in Markdown format.",
      "quiz": {{
        "question": "A multiple-choice question to test the core concept of the lesson.",
        "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
        "answer": "The correct option from the list."
      }}
    }}

    {_LESSON_LENGTH_INSTRUCTION}
    {_QUIZ_QUALITY_INSTRUCTION}
    '''


def get_test_generation_prompt(course_title, language="python", difficulty="intermediate"):
    """Returns the formatted prompt for generating a comprehensive test for a course."""
    return f"""
    You are a helpful quiz generation assistant.
    Generate a comprehensive test for the course titled '{course_title}'.
    The test should contain a mix of 5 multiple-choice questions and 2 coding problems.
    Difficulty level: {difficulty}. {_difficulty_text(difficulty)}
    Any coding problem's starter code, expected solution, and test cases must be written in {language}.
    {_NO_FENCE_INSTRUCTION}
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
