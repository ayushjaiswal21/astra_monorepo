from django.contrib import admin
from .models import (
    Course, Module, Lesson, 
    Quiz, Question, Choice,
    UserProgress, UserQuizAttempt
)

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True

class QuizInline(admin.StackedInline):
    model = Quiz
    extra = 0
    show_change_link = True

class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1
    show_change_link = True
    fields = ('title', 'order', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

class ModuleInline(admin.StackedInline):
    model = Module
    extra = 1
    show_change_link = True

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'description')
    inlines = [ModuleInline]

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'description')
    inlines = [LessonInline]

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order', 'created_at', 'updated_at')
    list_filter = ('module__course', 'module')
    search_fields = ('title', 'content')
    inlines = [QuizInline]

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'question_count')
    list_filter = ('lesson__module__course', 'lesson__module')
    inlines = [QuestionInline]
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'quiz', 'order')
    list_filter = ('quiz__lesson__module__course', 'quiz')
    inlines = [ChoiceInline]

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('choice_text', 'question', 'is_correct')
    list_filter = ('is_correct', 'question__quiz')
    search_fields = ('choice_text', 'question__question_text')

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'lesson', 'completed', 'last_reviewed')
    list_filter = ('completed', 'lesson__module__course')
    search_fields = ('session_key', 'lesson__title')

@admin.register(UserQuizAttempt)
class UserQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'quiz', 'score', 'completed_at')
    list_filter = ('quiz__lesson__module__course', 'quiz')
    search_fields = ('session_key', 'quiz__title')
