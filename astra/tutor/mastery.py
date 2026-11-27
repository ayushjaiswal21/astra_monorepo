"""Per-skill mastery scoring (Elo-style EMA update).

No topic/skill taxonomy exists yet in this app's data model (Lesson/Quiz have
no topic field), so the skill identifier is the Lesson's title -- the
simplest real thing that works with the current schema.

Wired into tutor/views.py's submit_quiz(), right after the
UserQuizAttempt.objects.create(...) call.
"""
K = 0.1


def update_mastery(session_key, skill_name, passed):
    """Update (and return) the SkillMastery row for (session_key, skill_name).

    Elo-style EMA: new_score = old_score + K * (actual - expected), where
    expected is the current score itself (a 0..1 mastery probability) and
    actual is 1 if passed else 0. Score is clamped to [0, 1].
    """
    from .models import SkillMastery  # local import: avoid app-loading-order issues

    mastery, _ = SkillMastery.objects.get_or_create(
        session_key=session_key, skill_name=skill_name
    )
    expected = mastery.score
    actual = 1.0 if passed else 0.0
    new_score = mastery.score + K * (actual - expected)
    mastery.score = max(0.0, min(1.0, new_score))
    mastery.save(update_fields=['score', 'updated_at'])
    return mastery


def difficulty_for_score(score):
    """Maps a SkillMastery 0-1 score (or None, when no row exists yet) to a
    difficulty label usable by the prompts in tutor/prompts.py."""
    if score is None:
        return "intermediate"
    if score < 0.4:
        return "beginner"
    if score <= 0.75:
        return "intermediate"
    return "advanced"
