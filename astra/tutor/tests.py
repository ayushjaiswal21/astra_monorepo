from django.contrib.auth.models import User
from django.test import TestCase

from .models import Choice, Course, Lesson, Module, Question, Quiz, SkillMastery


class CourseOwnershipAndMasterySmokeTest(TestCase):
    """Real, executed smoke test for this session's auth/ownership + mastery
    wiring — not just py_compile. Run with: python manage.py test tutor"""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pw12345!')
        self.stranger = User.objects.create_user(username='stranger', password='pw12345!')

        self.course = Course.objects.create(title="Smoke Test Course", description="x", created_by=self.owner)
        module = Module.objects.create(course=self.course, title="M1", description="d", order=0)
        self.lesson = Lesson.objects.create(module=module, title="Intro to Testing", content="Some real lesson content.")
        self.quiz = Quiz.objects.create(lesson=self.lesson)
        self.question = Question.objects.create(quiz=self.quiz, question_text="2+2?", order=0)
        self.correct_choice = Choice.objects.create(question=self.question, choice_text="4", is_correct=True)
        Choice.objects.create(question=self.question, choice_text="5", is_correct=False)

    def test_lesson_detail_renders_for_anonymous_user(self):
        resp = self.client.get(f'/course/{self.course.id}/module/{self.quiz.lesson.module.id}/lesson/{self.lesson.id}/')
        self.assertEqual(resp.status_code, 200)

    def test_submit_quiz_and_mastery_update(self):
        resp = self.client.post(
            f'/api/quiz/{self.quiz.id}/submit/',
            data=f'{{"answers": {{"{self.question.id}": "{self.correct_choice.id}"}}}}',
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['score'], 100.0)

        mastery = SkillMastery.objects.filter(skill_name=self.lesson.title).first()
        self.assertIsNotNone(mastery)
        self.assertGreater(mastery.score, 0.5, "mastery should increase after a correct answer")

        resp = self.client.get(f'/course/{self.course.id}/module/{self.quiz.lesson.module.id}/lesson/{self.lesson.id}/')
        self.assertIn(b'Mastery:', resp.content)

    def test_delete_course_requires_ownership(self):
        # A stranger (even if logged in as a different real user) cannot delete it.
        self.client.login(username='stranger', password='pw12345!')
        resp = self.client.post(f'/api/courses/{self.course.id}/delete/')
        self.assertEqual(resp.status_code, 403)
        self.client.logout()

        # An unauthenticated caller cannot delete it either.
        resp = self.client.post(f'/api/courses/{self.course.id}/delete/')
        self.assertEqual(resp.status_code, 403)

        # The real owner can.
        self.client.login(username='owner', password='pw12345!')
        resp = self.client.post(f'/api/courses/{self.course.id}/delete/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Course.objects.filter(id=self.course.id).exists())

    def test_ownerless_course_stays_deletable_by_anyone(self):
        legacy_course = Course.objects.create(title="Legacy", description="x", created_by=None)
        resp = self.client.post(f'/api/courses/{legacy_course.id}/delete/')
        self.assertEqual(resp.status_code, 200)

    def test_register_view_creates_and_logs_in_a_real_user(self):
        resp = self.client.post('/register/', {
            'username': 'newuser', 'password1': 'VeryStrongPass123!', 'password2': 'VeryStrongPass123!',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_dashboard_renders_with_delete_modal(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'delete-modal', resp.content)
        self.assertIn(b'Updated', resp.content)  # the course card's updated_at label

    def test_analytics_idor_is_blocked(self):
        # The analytics endpoint takes a session_key as `user_id`; it must
        # reject one that isn't the caller's own session key.
        self.client.get('/')  # force a session to exist
        resp = self.client.get('/api/analytics/some-other-sessions-key/')
        self.assertEqual(resp.status_code, 403)
