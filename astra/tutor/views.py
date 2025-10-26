import json
import random
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.conf import settings
import google.generativeai as genai

from .models import Course, Module, Lesson, Quiz, Question, Choice, UserProgress, UserQuizAttempt, ModuleProgress, CourseTestSession, CourseTestQuestion, CourseTestAttempt

from .tasks import generate_course_content



def dashboard(request):
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    courses = Course.objects.all().order_by('-created_at')
    total_courses = courses.count()

    all_lessons = Lesson.objects.filter(module__course__in=courses)
    total_lessons = all_lessons.count()

    completed_lessons = UserProgress.objects.filter(
        session_key=session_key,
        completed=True
    ).count()

    progress_percentage = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0

    context = {
        'courses': courses,
        'total_courses': total_courses,
        'completed_lessons': completed_lessons,
        'total_lessons': total_lessons,
        'progress_percentage': progress_percentage,
    }
    return render(request, 'tutor/dashboard.html', context)

def course_list(request):
    courses = Course.objects.all().order_by('-created_at')
    context = {
        'courses': courses,
    }
    return render(request, 'tutor/course_list.html', context)



# New view to render the dedicated "Create Course" page
def create_course_page(request):
    return render(request, 'tutor/create_course.html')

@require_http_methods(["POST"])
def create_course(request):
    """
    Handles the initial course creation request. It creates a placeholder course
    and dispatches a background task to generate the actual content.
    """
    try:
        data = json.loads(request.body)
        topic = data.get('topic', 'Unnamed Topic')

        # --- Step 1: Create a placeholder Course object ---
        course = Course.objects.create(
            title=f"New Course on {topic}", 
            description="Course content is being generated in the background. Please check back in a few moments."
        )

        # --- Step 2: Dispatch the background task to do all the work ---
        generate_course_content.delay(course.id, topic)

        # --- Step 3: Return an immediate response ---
        return JsonResponse({'success': True, 'course_id': course.id})

    except Exception as e:
        # Catches critical errors
        return JsonResponse({'error': f'A critical error occurred: {str(e)}'}, status=500)



def course_list_api(request):
    courses = Course.objects.all().order_by('-created_at')
    course_list = []
    for course in courses:
        course_list.append({
            'id': course.id,
            'title': course.title,
            'description': course.description,
            'created_at': course.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    return JsonResponse({'courses': course_list})

def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    modules = course.modules.all().prefetch_related('lessons').order_by('order')
    return render(request, 'tutor/course_detail.html', {
        'course': course,
        'modules': modules,
    })

def lesson_detail(request, course_id, module_id, lesson_id):
    lesson = get_object_or_404(
        Lesson.objects.select_related('module__course'), 
        id=lesson_id, module_id=module_id, module__course_id=course_id
    )

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    if not lesson.content:
        lesson.content = '''
        <div class="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-md my-5">
            <div class="flex">
                <div class="flex-shrink-0">
                    <i class="fas fa-robot h-5 w-5 text-blue-400"></i>
                </div>
                <div class="ml-3">
                    <h3 class="text-sm font-medium text-blue-800">Content Generation in Progress</h3>
                    <div class="mt-2 text-sm text-blue-700">
                        <p>Our AI tutor is currently preparing this lesson for you. Please check back in a moment. You can refresh the page to see the update.</p>
                    </div>
                </div>
            </div>
        </div>
        '''

    progress, created = UserProgress.objects.get_or_create(
        session_key=session_key,
        lesson=lesson
    )
    all_lessons = list(Lesson.objects.filter(module__course_id=course_id).order_by('module__order', 'order'))
    current_index = all_lessons.index(lesson)
    next_lesson = all_lessons[current_index + 1] if current_index + 1 < len(all_lessons) else None
    prev_lesson = all_lessons[current_index - 1] if current_index > 0 else None

    module_progress = ModuleProgress.objects.filter(
        session_key=session_key,
        module__course_id=course_id
    ).values_list('module_id', flat=True)
    
    return render(request, 'tutor/lesson_detail.html', {
        'course': lesson.module.course,
        'module': lesson.module,
        'lesson': lesson,
        'progress': progress,
        'next_lesson': next_lesson,
        'prev_lesson': prev_lesson,
        'has_quiz': hasattr(lesson, 'quiz'),
        'module_progress': list(module_progress)
    })

def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz.objects.prefetch_related('questions__choices'), id=quiz_id)
    questions = quiz.questions.all().order_by('order')
    
    quiz_data = []
    for question in questions:
        # Thanks to prefetch_related, this does not hit the database again
        choices = [
            {'id': choice.id, 'text': choice.choice_text}
            for choice in question.choices.all()
        ]
        random.shuffle(choices)
        quiz_data.append({
            'id': question.id,
            'text': question.question_text,
            'explanation': question.explanation,
            'choices': choices
        })
    
    return render(request, 'tutor/quiz_detail.html', {
        'quiz': quiz,
        'quiz_data': json.dumps(quiz_data),
        'lesson': quiz.lesson
    })

@require_http_methods(["POST"])
def submit_quiz(request, quiz_id):
    try:
        data = json.loads(request.body)
        quiz = Quiz.objects.get(id=quiz_id)
        answers = data.get('answers', {})
        
        total_questions = quiz.questions.count()
        correct_answers = 0
        
        for question_id, choice_id in answers.items():
            try:
                question = Question.objects.get(id=question_id, quiz=quiz)
                correct_choice = question.choices.get(is_correct=True)
                if str(correct_choice.id) == choice_id:
                    correct_answers += 1
            except (Question.DoesNotExist, Choice.DoesNotExist):
                pass
        
        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        UserQuizAttempt.objects.create(
            session_key=request.session.session_key or 'anonymous',
            quiz=quiz,
            score=score
        )
        
        if score >= 70:
            UserProgress.objects.update_or_create(
                session_key=request.session.session_key or 'anonymous',
                lesson=quiz.lesson,
                defaults={'completed': True}
            )
        
        return JsonResponse({
            'success': True,
            'score': score,
            'correct_answers': correct_answers,
            'total_questions': total_questions,
            'passed': score >= 70
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@require_http_methods(["POST"])
def ai_assistant(request):
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        lesson_id = data.get('context', {}).get('lesson_id')

        if not message or not lesson_id:
            return JsonResponse({'error': 'Message and lesson_id are required'}, status=400)

        lesson = get_object_or_404(Lesson, id=lesson_id)

        context_text = lesson.content

        prompt = f'''
        Context: You are an AI tutor explaining a lesson. The lesson content is as follows:
        ---
        {context_text}
        ---
        Based ONLY on the context above, answer the user's question.
        User Question: {message}
        '''
        
        response_json = call_ollama(prompt)
        response_text = response_json.get('response', 'Sorry, I could not generate a response.')


        return JsonResponse({
            'response': response_text,
            'context': data.get('context', {})
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def delete_course(request, course_id):
    try:
        course = get_object_or_404(Course, id=course_id)
        course.delete()
        return JsonResponse({'success': True, 'message': 'Course deleted successfully.'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def mark_lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    # Mark the current lesson as complete
    progress, created = UserProgress.objects.get_or_create(
        session_key=session_key,
        lesson=lesson
    )
    progress.completed = True
    progress.save()
    
    # Check if this completes the module
    module = lesson.module
    all_lessons_in_module = module.lessons.all()
    completed_lessons_count = UserProgress.objects.filter(
        session_key=session_key,
        lesson__in=all_lessons_in_module,
        completed=True
    ).count()
    
    if completed_lessons_count >= all_lessons_in_module.count():
        ModuleProgress.objects.update_or_create(
            session_key=session_key,
            module=module,
            defaults={'completed': True}
        )

    # Determine the next lesson
    all_course_lessons = list(Lesson.objects.filter(module__course_id=lesson.module.course.id).order_by('module__order', 'order'))
    current_index = all_course_lessons.index(lesson)
    next_lesson = all_course_lessons[current_index + 1] if current_index + 1 < len(all_course_lessons) else None

    if next_lesson:
        return redirect('tutor:lesson_detail', course_id=next_lesson.module.course.id, module_id=next_lesson.module.id, lesson_id=next_lesson.id)
    else:
        # If there are no more lessons, redirect to the course detail page
        return redirect('tutor:course_detail', course_id=lesson.module.course.id)

# --- New Views for Simplify and Example ---

@require_http_methods(["GET"])
def simplify_content(request, lesson_id):
    try:
        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        if lesson.simplified_content:
            return JsonResponse({'content': lesson.simplified_content})
        
        if not lesson.content:
            return JsonResponse({'content': 'Cannot simplify an empty lesson.'})

        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"""
        Simplify the following lesson content for a beginner. Focus on core concepts, use simple language, and keep it concise.
        Lesson Title: {lesson.title}
        Lesson Content:
        {lesson.content}
        """
        response = model.generate_content(prompt)
        simplified_text = response.text.strip()
        
        lesson.simplified_content = simplified_text
        lesson.save()
        
        return JsonResponse({'content': simplified_text})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def generate_example(request, lesson_id):
    try:
        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        if lesson.example_content:
            return JsonResponse({'content': lesson.example_content})
        
        if not lesson.content:
             return JsonResponse({'content': 'Cannot generate an example for an empty lesson.'})

        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"""
        Provide a clear and practical example for the following lesson content. Focus on demonstrating the main concepts in a concise way.
        Lesson Title: {lesson.title}
        Lesson Content:
        {lesson.content}
        """
        response = model.generate_content(prompt)
        example_text = response.text.strip()
        
        lesson.example_content = example_text
        lesson.save()
        
        return JsonResponse({'content': example_text})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# --- Comprehensive Test Views ---

def start_course_test_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    return render(request, 'tutor/course_test_detail.html', {'course': course})

@require_http_methods(["POST"])
def generate_course_test_api(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not course.title:
        return JsonResponse({'success': False, 'error': 'Course title cannot be empty.'}, status=400)
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')

        prompt = f"""
        You are a helpful quiz generation assistant.
        Generate a comprehensive test for the course titled '{course.title}'.
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
              "question_text": "### Sum Calculator\\n\\n**Scenario:** You are given two integers, a and b. **Task:** Write a function that returns their sum.\\n\\n**Input Format:** Two integers, a and b.\\n\\n**Output Format:** A single integer representing the sum.\\n\\n**Example:**\\n\\n- **Input:** a = 2, b = 3\\n- **Output:** 5",
              "starter_code": "def solve(a, b):\\n  # Your code here\\n  return 0",
              "test_cases": [
                {{"input": "2 3", "expected_output": "5"}},
                {{"input": "-1 5", "expected_output": "4"}}
              ]
            }}
          ]
        }}
        """

        response = model.generate_content(prompt)
        quiz_data = json.loads(response.text)

        test_session = CourseTestSession.objects.create(course=course, session_key=session_key)

        for q_data in quiz_data['questions']:
            CourseTestQuestion.objects.create(
                test_session=test_session,
                question_text=q_data['question_text'],
                options=q_data.get('options'),
                correct_answer_key=q_data.get('correct_answer'),
                question_type=q_data['question_type'],
                starter_code=q_data.get('starter_code'),
                test_cases=q_data.get('test_cases')
            )

        questions = CourseTestQuestion.objects.filter(test_session=test_session)
        sanitized_questions = []
        for q in questions:
            sanitized_questions.append({
                'id': q.id,
                'question_text': q.question_text,
                'options': q.options,
                'question_type': q.question_type,
                'starter_code': q.starter_code,
            })

        return JsonResponse({'test_session_id': test_session.id, 'questions': sanitized_questions})

    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Failed to generate test: {str(e)}'}, status=500)

@require_http_methods(["POST"])
def submit_course_test_api(request, test_session_id):
    try:
        data = json.loads(request.body)
        answers = data.get('answers', {})
        test_session = get_object_or_404(CourseTestSession, id=test_session_id)
        if test_session.session_key != request.session.session_key:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        # No N+1 query problem here, as we are fetching all questions in a single query.
        questions = test_session.questions.all()

        correct_answers = 0
        wrong_questions = []

        for question in questions:
            if str(question.id) in answers:
                if question.question_type == 'mcq':
                    if answers[str(question.id)] == question.correct_answer_key:
                        correct_answers += 1
                    else:
                        wrong_questions.append(question.question_text)
            # For coding questions, we assume they are manually graded for now

        total_questions = questions.count()
        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

        # Generate recommendations
        recommendations = ""
        if wrong_questions:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""
            A user got the following questions wrong in a test on the course '{test_session.course.title}':
            {wrong_questions}
            Please provide some recommendations for what the user should study to improve.
            """
            response = model.generate_content(prompt)
            recommendations = response.text

        CourseTestAttempt.objects.create(
            test_session=test_session,
            session_key=request.session.session_key,
            submitted_answers=answers,
            score=score,
            percentage=score,
            recommendations=recommendations
        )

        return JsonResponse({
            'score': score,
            'recommendations': recommendations
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def run_code_api(request):
    try:
        data = json.loads(request.body)
        code = data.get('code')
        question_id = data.get('question_id')

        question = get_object_or_404(CourseTestQuestion, id=question_id)
        test_cases = question.test_cases

        if not test_cases:
            return JsonResponse({'error': 'No test cases found for this question.'}, status=400)

        # For simplicity, we'll just run the first test case for now
        test_case = test_cases[0]
        source_code = code
        language_id = 71 # Python

        headers = {
            "X-RapidAPI-Key": settings.JUDGE0_API_KEY,
            "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
            "Content-Type": "application/json"
        }

        payload = {
            "source_code": source_code,
            "language_id": language_id,
            "stdin": test_case['input']
        }

        try:
            # Create submission
            response = httpx.post("https://judge0-ce.p.rapidapi.com/submissions", headers=headers, json=payload)
            response.raise_for_status()
            token = response.json()['token']

            # Get submission result
            response = httpx.get(f"https://judge0-ce.p.rapidapi.com/submissions/{token}", headers=headers)
            response.raise_for_status()
            result = response.json()

            return JsonResponse(result)
        except httpx.HTTPStatusError as e:
            return JsonResponse({'error': f'Judge0 API error: {e.response.text}'}, status=500)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)