from django.urls import path
from . import views

app_name = 'tutor'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard, name='dashboard'),

    # Page rendering
    path('courses/', views.course_list, name='course_list'),

    # New dedicated page for creating a course
    path('create/', views.create_course_page, name='create_course_page'),

    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('course/<int:course_id>/module/<int:module_id>/lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('quiz/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),

    # API endpoints
    path('api/courses/', views.course_list_api, name='course_list_api'),
    path('api/courses/create/', views.create_course, name='create_course'),
    path('api/courses/<int:course_id>/delete/', views.delete_course, name='delete_course'),
    path('api/ai_assistant/', views.ai_assistant, name='ai_assistant'),

    # --- New and Updated API endpoints ---
    path('api/quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('api/lesson/<int:lesson_id>/simplify/', views.simplify_content, name='simplify_content'),
    path('api/lesson/<int:lesson_id>/example/', views.generate_example, name='generate_example'),

    path('lesson/<int:lesson_id>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
]