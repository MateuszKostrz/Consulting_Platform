"""
Revision Engine – mastery update service.

Isolated here so the scoring logic can be improved without touching views.

Scoring summary
---------------
Base delta (before difficulty multiplier):
  correct, no help          +0.08
  correct, hint only        +0.05
  correct, explanation seen +0.03   (looked at mark scheme)
  correct, video seen       +0.02   (watched full solution)
  incorrect, no help        -0.10   (decay > growth intentionally)
  incorrect, any help       -0.06

Time bonus (correct only, added after difficulty multiplier):
  solved faster than FAST threshold → +0.03
  (no penalty for slow — careful thinking is fine)

Difficulty multiplier scales the base delta:
  Easy ×0.8, Medium ×1.0, Hard ×1.2
"""

from django.utils import timezone


# Base score deltas keyed by (is_correct, help_level)
# help_level: 0 = none, 1 = hint only, 2 = explanation viewed, 3 = video viewed
_BASE_DELTA = {
    (True,  0): 0.08,
    (True,  1): 0.05,
    (True,  2): 0.03,
    (True,  3): 0.02,
    (False, 0): -0.10,
    (False, 1): -0.06,
    (False, 2): -0.06,
    (False, 3): -0.06,
}

DIFFICULTY_MULTIPLIER = {
    'Easy':   0.8,
    'Medium': 1.0,
    'Hard':   1.2,
}

# Seconds within which a correct answer earns the speed bonus
TIME_FAST_THRESHOLD = {
    'Easy':   20,
    'Medium': 40,
    'Hard':   60,
}
TIME_FAST_BONUS = 0.03

MASTERY_MIN = 0.05
MASTERY_MAX = 0.95
CONFIDENCE_MAX = 1.0


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _help_level(hint_viewed, explanation_viewed, video_viewed):
    """Return an integer 0–3 representing the most significant help used."""
    if video_viewed:
        return 3
    if explanation_viewed:
        return 2
    if hint_viewed:
        return 1
    return 0


def update_mastery(user, skill, is_correct, difficulty,
                   hint_viewed=False, explanation_viewed=False, video_viewed=False,
                   time_spent=None):
    """
    Update StudentSkillMastery for a user/skill pair after one attempt.

    Parameters
    ----------
    time_spent : int or None
        Seconds the student spent on this sub-question. Used to award a
        speed bonus when the student answers correctly and quickly.

    Returns the updated StudentSkillMastery instance.
    """
    from .models import StudentSkillMastery  # local import avoids circular dependency

    mastery, _ = StudentSkillMastery.objects.get_or_create(user=user, skill=skill)

    level = _help_level(hint_viewed, explanation_viewed, video_viewed)
    base  = _BASE_DELTA.get((is_correct, level), 0.0)
    mult  = DIFFICULTY_MULTIPLIER.get(difficulty, 1.0)
    delta = base * mult

    # Speed bonus: correct answer within the fast threshold
    if is_correct and time_spent is not None:
        threshold = TIME_FAST_THRESHOLD.get(difficulty, 45)
        if time_spent <= threshold:
            delta += TIME_FAST_BONUS

    mastery.mastery_score = _clamp(mastery.mastery_score + delta, MASTERY_MIN, MASTERY_MAX)

    # Confidence grows on correct answers, shrinks on incorrect
    conf_delta = 0.05 if is_correct else -0.03
    mastery.confidence_score = _clamp(mastery.confidence_score + conf_delta, 0.0, CONFIDENCE_MAX)

    mastery.attempts_count += 1
    if is_correct:
        mastery.correct_count += 1
    mastery.last_practiced_at = timezone.now()
    mastery.save()

    return mastery


def get_mastery_color(mastery_score):
    """Return a Bootstrap colour name based on mastery score."""
    if mastery_score >= 0.75:
        return 'success'
    elif mastery_score >= 0.5:
        return 'info'
    elif mastery_score >= 0.3:
        return 'warning'
    return 'danger'
