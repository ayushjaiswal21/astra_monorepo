import json
import logging
import random
import httpx
import jwt
from django.contrib.auth.models import User
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg
from django.conf import settings
from django.utils import timezone
import google.generativeai as genai

# Dummy function to resolve F821 error until proper AI service is integrated
def call_ollama(prompt):
    print(f"--- DUMMY AI CALL ---\nPrompt: {prompt}\n--- END DUMMY AI CALL ---")
    return {"response": "This is a placeholder response from the dummy call_ollama function."}

from .models import Course, Module, Lesson, Quiz, Question, Choice, UserProgress, UserQuizAttempt, ModuleProgress, CourseTestSession, CourseTestQuestion, CourseTestAttempt, SkillMastery
from .prompts import get_test_generation_prompt
from .tasks import generate_course_content
from .mastery import update_mastery

logger = logging.getLogger(__name__)


def _safe_error_response(exc, status=500, generic_message="An unexpected error occurred. Please try again."):
    """Log the real exception server-side; never echo exception internals to the client."""
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JsonResponse({'error': generic_message}, status=status)


def _get_adjacent_lessons(course_id, lesson):
    """Return (prev_lesson, next_lesson) for `lesson` within its course's lesson order."""
    course_lessons = list(Lesson.objects.filter(module__course_id=course_id).order_by('module__order', 'order'))
    current_index = course_lessons.index(lesson)
    prev_lesson = course_lessons[current_index - 1] if current_index > 0 else None
    next_lesson = course_lessons[current_index + 1] if current_index + 1 < len(course_lessons) else None
    return prev_lesson, next_lesson


def _generate_lesson_variant(lesson_id, field_name, prompt_template):
    """Fetch/generate a cached Gemini-produced variant of a lesson's content (simplified/example)."""
    lesson = get_object_or_404(Lesson, id=lesson_id)

    cached = getattr(lesson, field_name)
    if cached:
        return JsonResponse({'content': cached})

    if not lesson.content:
        return JsonResponse({'content': f'Cannot generate {field_name.replace("_", " ")} for an empty lesson.'})

    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = prompt_template.format(title=lesson.title, content=lesson.content)
    response = model.generate_content(prompt)
    generated_text = response.text.strip()

    setattr(lesson, field_name, generated_text)
    lesson.save()

    return JsonResponse({'content': generated_text})


def dashboard(request):
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    courses_qs = Course.objects.all().order_by('-created_at')
    paginator = Paginator(courses_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    total_courses = paginator.count

    all_lessons = Lesson.objects.filter(module__course__in=courses_qs)
    total_lessons = all_lessons.count()

    completed_lessons = UserProgress.objects.filter(
        session_key=session_key,
        completed=True
    ).count()

    progress_percentage = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0

    context = {
        'courses': page_obj,
        'page_obj': page_obj,
        'total_courses': total_courses,
        'completed_lessons': completed_lessons,
        'total_lessons': total_lessons,
        'progress_percentage': progress_percentage,
    }
    return render(request, 'tutor/dashboard.html', context)

def course_list(request):
    courses_qs = Course.objects.all().order_by('-created_at')
    paginator = Paginator(courses_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'courses': page_obj,
        'page_obj': page_obj,
        'total_courses': paginator.count,
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
            description="Course content is being generated in the background. Please check back in a few moments.",
            created_by=request.user if request.user.is_authenticated else None
        )

        # --- Step 2: Dispatch the background task to do all the work ---
        generate_course_content.delay(course.id, topic)

        # --- Step 3: Return an immediate response ---
        return JsonResponse({'success': True, 'course_id': course.id})

    except Exception as e:
        return _safe_error_response(e)



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

GENERATION_STALE_AFTER = timedelta(minutes=3)
GENERATION_PLACEHOLDER_TEXT = "Course content is being generated in the background."

def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    modules = course.modules.all().prefetch_related('lessons').order_by('order')
    # If a course is still showing the "being generated" placeholder well
    # past when generation should have finished, the Celery worker is
    # probably down/stuck — surface that instead of letting the user wait
    # forever with no feedback.
    generation_possibly_stuck = (
        GENERATION_PLACEHOLDER_TEXT in (course.description or '')
        and timezone.now() - course.created_at > GENERATION_STALE_AFTER
    )
    return render(request, 'tutor/course_detail.html', {
        'course': course,
        'modules': modules,
        'generation_possibly_stuck': generation_possibly_stuck,
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
    prev_lesson, next_lesson = _get_adjacent_lessons(course_id, lesson)

    module_progress = ModuleProgress.objects.filter(
        session_key=session_key,
        module__course_id=course_id
    ).values_list('module_id', flat=True)

    mastery = SkillMastery.objects.filter(session_key=session_key, skill_name=lesson.title).first()

    return render(request, 'tutor/lesson_detail.html', {
        'course': lesson.module.course,
        'module': lesson.module,
        'lesson': lesson,
        'progress': progress,
        'next_lesson': next_lesson,
        'prev_lesson': prev_lesson,
        'has_quiz': hasattr(lesson, 'quiz'),
        'module_progress': list(module_progress),
        'mastery_score': round(mastery.score * 100) if mastery else None,
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
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

        data = json.loads(request.body)
        # select_related/prefetch avoids a Question + Choice query per submitted answer.
        quiz = Quiz.objects.prefetch_related('questions__choices').get(id=quiz_id)
        answers = data.get('answers', {})

        questions_by_id = {str(q.id): q for q in quiz.questions.all()}
        total_questions = len(questions_by_id)
        correct_answers = 0

        for question_id, choice_id in answers.items():
            question = questions_by_id.get(str(question_id))
            if question is None:
                continue
            correct_choice = next((c for c in question.choices.all() if c.is_correct), None)
            if correct_choice and str(correct_choice.id) == choice_id:
                correct_answers += 1

        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

        # Marking the lesson complete on a passing score is handled by the
        # handle_quiz_attempt signal (tutor/signals.py), triggered by this create().
        UserQuizAttempt.objects.create(
            session_key=session_key,
            quiz=quiz,
            score=score
        )
        update_mastery(session_key, quiz.lesson.title, score >= 70)

        return JsonResponse({
            'success': True,
            'score': score,
            'correct_answers': correct_answers,
            'total_questions': total_questions,
            'passed': score >= 70
        })
    
    except Exception as e:
        logger.error("Unhandled error in submit_quiz: %s", e, exc_info=True)
        return JsonResponse({
            'success': False,
            'error': "Could not submit quiz. Please try again."
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
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        return JsonResponse({
            'response': response_text,
            'context': data.get('context', {})
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return _safe_error_response(e)

# Analytics endpoint for aggregated learning data
@require_http_methods(["GET"])
def analytics(request, user_id):
    """Get aggregated analytics data for learning progress for a specific user.

    `user_id` is actually this app's anonymous session_key (there is no real
    login system here), so it must match the caller's own session_key or
    anyone could read anyone else's learning analytics by guessing/sharing it.
    """
    if not request.session.session_key:
        request.session.create()
    if user_id != request.session.session_key:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    try:
        # Filter courses, modules, lessons, quizzes by user's progress
        user_courses = Course.objects.filter(module__lessons__userprogress__session_key=user_id).distinct()
        total_courses = user_courses.count()

        user_lessons = Lesson.objects.filter(userprogress__session_key=user_id).distinct()
        total_lessons = user_lessons.count()

        completed_lessons = UserProgress.objects.filter(
            session_key=user_id,
            completed=True
        ).count()

        overall_progress = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0

        total_quiz_attempts = UserQuizAttempt.objects.filter(session_key=user_id).count()
        avg_quiz_score = UserQuizAttempt.objects.filter(session_key=user_id).aggregate(avg_score=Avg('score'))['avg_score'] or 0

        # Recent activity (last 30 days) for this user
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_progress = UserProgress.objects.filter(session_key=user_id, last_reviewed__gte=thirty_days_ago).count()

        return JsonResponse({
            'total_courses': total_courses,
            'total_lessons': total_lessons,
            'total_completed_lessons': completed_lessons,
            'overall_progress': round(overall_progress, 2),
            'total_quiz_attempts': total_quiz_attempts,
            'avg_quiz_score': round(avg_quiz_score, 2),
            'recent_activity': recent_progress,
        })
    except Exception as e:
        return _safe_error_response(e)

@require_http_methods(["POST"])
def delete_course(request, course_id):
    try:
        course = get_object_or_404(Course, id=course_id)
        # Ownerless (legacy/anonymous) courses stay deletable by anyone, matching
        # prior behavior. An owned course can only be deleted by its own owner.
        if course.created_by_id is not None and (
            not request.user.is_authenticated or course.created_by_id != request.user.id
        ):
            return JsonResponse(
                {'success': False, 'error': 'You do not have permission to delete this course.'},
                status=403,
            )
        course.delete()
        return JsonResponse({'success': True, 'message': 'Course deleted successfully.'})

    except Exception as e:
        return _safe_error_response(e)

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
    _, next_lesson = _get_adjacent_lessons(lesson.module.course.id, lesson)

    if next_lesson:
        return redirect('tutor:lesson_detail', course_id=next_lesson.module.course.id, module_id=next_lesson.module.id, lesson_id=next_lesson.id)
    else:
        # If there are no more lessons, redirect to the course detail page
        return redirect('tutor:course_detail', course_id=lesson.module.course.id)

# --- New Views for Simplify and Example ---

@require_http_methods(["GET"])
def simplify_content(request, lesson_id):
    try:
        return _generate_lesson_variant(
            lesson_id,
            'simplified_content',
            "Simplify the following lesson content for a beginner. Focus on core concepts, "
            "use simple language, and keep it concise.\nLesson Title: {title}\nLesson Content:\n{content}"
        )
    except Exception as e:
        return _safe_error_response(e)

@require_http_methods(["GET"])
def generate_example(request, lesson_id):
    try:
        return _generate_lesson_variant(
            lesson_id,
            'example_content',
            "Provide a clear and practical example for the following lesson content. Focus on "
            "demonstrating the main concepts in a concise way.\nLesson Title: {title}\nLesson Content:\n{content}"
        )
    except Exception as e:
        return _safe_error_response(e)

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

        prompt = get_test_generation_prompt(course.title)

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
        logger.error("Unhandled error in generate_course_test_api: %s", e, exc_info=True)
        return JsonResponse({'success': False, 'error': 'Failed to generate test. Please try again.'}, status=500)

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
        pending_review_count = 0

        # Coding questions have no automated grading path yet (no sandboxed
        # execution is wired up), so they're excluded from the score instead
        # of silently counting as wrong and capping the max possible score.
        scored_questions = [q for q in questions if q.question_type == 'mcq']

        for question in scored_questions:
            if str(question.id) in answers:
                if answers[str(question.id)] == question.correct_answer_key:
                    correct_answers += 1
                else:
                    wrong_questions.append(question.question_text)

        pending_review_count = questions.count() - len(scored_questions)
        total_questions = len(scored_questions)
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
            'recommendations': recommendations,
            'pending_review_count': pending_review_count,
        })

    except Exception as e:
        return _safe_error_response(e)


def register(request):
    """Minimal signup using Django's built-in UserCreationForm; logs the new
    user in immediately so they can start owning courses right away."""
    if request.user.is_authenticated:
        return redirect('tutor:dashboard')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('tutor:dashboard')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


def sso_login(request):
    """Cross-app SSO handoff from Astra Auth (Flask hub): verifies the JWT the
    hub signed, logs the matching Django user in (the signature IS the auth
    proof - no password needed), and creates the user on first visit."""
    token = request.GET.get('token', '')
    try:
        payload = jwt.decode(token, settings.SSO_SHARED_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return redirect(f"{reverse('tutor:dashboard')}?sso_error=Your+sign-in+link+expired.+Please+try+again.")
    except jwt.InvalidTokenError:
        return redirect(f"{reverse('tutor:dashboard')}?sso_error=Invalid+sign-in+link.")

    email = payload.get('email')
    username = payload.get('username') or email
    # username is unique on Django's User model - if it already belongs to a
    # *different* account (matched by email instead), disambiguate up front
    # rather than letting get_or_create's INSERT crash on the constraint.
    if User.objects.filter(username=username).exclude(email=email).exists():
        username = f"{username}-sso-{payload.get('sub', '')}"
    user, created = User.objects.get_or_create(
        email=email,
        defaults={'username': username},
    )

    login(request, user)
    return redirect('tutor:dashboard')


@require_http_methods(["POST"])
def ask_ai_guru_about_lesson(request, lesson_id):
    """Embedded-tutor integration: ground AI Guru's answer in this specific
    lesson's content via its RAG endpoints, instead of general knowledge.
    AI Guru is a separate FastAPI service/process (no shared DB), so this
    is a real HTTP call, not a local function call."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    try:
        data = json.loads(request.body)
        question = (data.get('question') or '').strip()
        if not question:
            return JsonResponse({'error': 'A question is required.'}, status=400)
        if not lesson.content:
            return JsonResponse({'error': 'This lesson has no content yet to ask about.'}, status=400)

        document_id = f"astralearn-lesson-{lesson.id}"
        base_url = settings.AI_GURU_BASE_URL

        with httpx.Client(timeout=20) as client:
            # Re-indexing is cheap and idempotent (the RAG service replaces
            # a document's chunks on each index call), so there's no need
            # to track "already indexed" state here.
            index_resp = client.post(f"{base_url}/rag/index", json={
                "document_id": document_id,
                "text": lesson.content,
            })
            index_resp.raise_for_status()

            query_resp = client.post(f"{base_url}/rag/query", json={
                "document_id": document_id,
                "question": question,
            })
            query_resp.raise_for_status()
            result = query_resp.json()

        return JsonResponse({
            'answer': result.get('answer', ''),
            'sources': result.get('sources', []),
        })
    except httpx.HTTPError as e:
        logger.warning("AI Guru RAG call failed for lesson %s: %s", lesson_id, e)
        return JsonResponse({'error': 'AI Guru is unavailable right now. Please try again later.'}, status=503)
    except Exception as e:
        return _safe_error_response(e)
