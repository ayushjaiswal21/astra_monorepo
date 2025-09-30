from django.db import models
from django.utils import timezone

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    # Removed user dependency
    
    def __str__(self):
        return self.title

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    simplified_content = models.TextField(blank=True, null=True)
    example_content = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"

class Quiz(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='quiz')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"Quiz for {self.lesson.title}"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.question_text[:50] + "..."

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.choice_text

class UserProgress(models.Model):
    # Using session key instead of user
    session_key = models.CharField(max_length=40, db_index=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_progress')
    completed = models.BooleanField(default=False)
    last_reviewed = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'User progress'
        unique_together = ('session_key', 'lesson')
    
    def __str__(self):
        return f"{self.session_key} - {self.lesson.title}"

class UserQuizAttempt(models.Model):
    # Using session key instead of user
    session_key = models.CharField(max_length=40, default='')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.FloatField()
    completed_at = models.DateTimeField(auto_now_add=True)
    passed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.session_key}'s attempt on {self.quiz.title}"

class ModuleProgress(models.Model):
    session_key = models.CharField(max_length=40, db_index=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='user_progress')
    completed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('session_key', 'module')