from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Course, Module, Lesson, Quiz, Question, Choice, UserProgress, UserQuizAttempt

@receiver(post_save, sender=Course)
def update_course_updated_at(sender, instance, **kwargs):
    """Update the updated_at timestamp when a course is saved."""
    Course.objects.filter(id=instance.id).update(updated_at=instance.updated_at)

@receiver(post_save, sender=Module)
def update_module_course_updated_at(sender, instance, **kwargs):
    """Update the parent course's updated_at when a module is saved."""
    if instance.course:
        instance.course.save()

@receiver(post_save, sender=Lesson)
def update_lesson_module_updated_at(sender, instance, **kwargs):
    """Update the parent module's course updated_at when a lesson is saved."""
    if instance.module and instance.module.course:
        instance.module.course.save()

@receiver(post_save, sender=Quiz)
def update_quiz_lesson_updated_at(sender, instance, **kwargs):
    """Update the parent lesson's module's course updated_at when a quiz is saved."""
    if instance.lesson and instance.lesson.module and instance.lesson.module.course:
        instance.lesson.module.course.save()

@receiver(post_save, sender=Question)
def update_question_quiz_updated_at(sender, instance, **kwargs):
    """Update the parent quiz's lesson's module's course updated_at when a question is saved."""
    if instance.quiz and instance.quiz.lesson and instance.quiz.lesson.module and instance.quiz.lesson.module.course:
        instance.quiz.lesson.module.course.save()

@receiver(post_save, sender=Choice)
def update_choice_question_updated_at(sender, instance, **kwargs):
    """Update the parent question's quiz's lesson's module's course updated_at when a choice is saved."""
    if instance.question and instance.question.quiz and instance.question.quiz.lesson and instance.question.quiz.lesson.module and instance.question.quiz.lesson.module.course:
        instance.question.quiz.lesson.module.course.save()

@receiver(post_save, sender=UserProgress)
def handle_lesson_completion(sender, instance, created, **kwargs):
    """Handle actions when a lesson is marked as completed."""
    if instance.completed:
        try:
            # Check if the lesson has a quiz
            if instance.lesson.quiz:
                # If the lesson has a quiz, we might want to do something special
                pass
        except Quiz.DoesNotExist:
            # Lesson does not have a quiz, so do nothing related to quiz
            pass

@receiver(post_save, sender=UserQuizAttempt)
def handle_quiz_attempt(sender, instance, created, **kwargs):
    """Handle actions when a quiz is attempted."""
    if created and instance.score >= 70:  # If passing score
        # Mark the lesson as completed
        UserProgress.objects.update_or_create(
            session_key=instance.session_key,
            lesson=instance.quiz.lesson,
            defaults={'completed': True}
        )

# Connect the signals
def connect_signals():
    # These are connected via the @receiver decorator
    pass
