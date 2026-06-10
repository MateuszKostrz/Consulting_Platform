"""Align Q275 part (b) MCQ with stem: both (3,7) and (6,4) giving two equations in a,b."""

from django.db import migrations


NEW_STEM = (
    'With \\(y=ax^2+bx+c\\) and \\(c=4\\) from part (a), which pair of equations in \\(a\\) and \\(b\\) '
    'comes from the points \\((3,7)\\) and \\((6,4)\\)?'
)

NEW_OPTIONS = (
    ('A', False, r'\(9a+3b=7,\ 36a+6b=0\)'),
    ('B', False, r'\(9a+3b=3,\ 36a+6b=4\)'),
    ('C', True, r'\(9a+3b=3,\ 36a+6b=0\)'),
    ('D', False, r'\(9a+3b=3,\ 6a+b=3\)'),
)


def forwards(apps, schema_editor):
    RevisionSubQuestion = apps.get_model('website', 'RevisionSubQuestion')
    RevisionMCQOption = apps.get_model('website', 'RevisionMCQOption')

    try:
        sq = RevisionSubQuestion.objects.get(question_id=275, part_label='b')
    except RevisionSubQuestion.DoesNotExist:
        return

    sq.question_text = NEW_STEM
    sq.save(update_fields=['question_text'])

    RevisionMCQOption.objects.filter(subquestion=sq).delete()
    for label, is_correct, text in NEW_OPTIONS:
        RevisionMCQOption.objects.create(
            subquestion=sq,
            label=label,
            option_text=text,
            is_correct=is_correct,
        )


def backwards(apps, schema_editor):
    RevisionSubQuestion = apps.get_model('website', 'RevisionSubQuestion')
    RevisionMCQOption = apps.get_model('website', 'RevisionMCQOption')

    try:
        sq = RevisionSubQuestion.objects.get(question_id=275, part_label='b')
    except RevisionSubQuestion.DoesNotExist:
        return

    sq.question_text = 'Write the equation from the point \\((3,7)\\).'
    sq.save(update_fields=['question_text'])

    RevisionMCQOption.objects.filter(subquestion=sq).delete()
    for label, is_correct, text in (
        ('A', False, r'\(9a+3b=7\)'),
        ('B', True, r'\(9a+3b=3\)'),
        ('C', False, r'\(3a+9b=3\)'),
        ('D', False, r'\(9a+b=3\)'),
    ):
        RevisionMCQOption.objects.create(
            subquestion=sq,
            label=label,
            option_text=text,
            is_correct=is_correct,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('website', '0255_seed_revision_q179_systems_lin_eq'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
