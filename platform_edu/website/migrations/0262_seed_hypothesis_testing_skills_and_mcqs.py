# Hypothesis testing revision skills + MCQ import for Math AI SL (18 questions, 86 subquestions).

import json
from pathlib import Path

from django.db import migrations

DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / 'data'
    / 'ib_math_ai_sl_hypothesis_testing_mcqs_skillkeys.json'
)

HYPOTHESIS_TESTING_SKILLS = (
    ('one_sample_t_test', 'One-Sample t-Test', 1),
    ('two_sample_t_test', 'Two-Sample t-Test', 2),
    ('chi_squared_goodness_of_fit', 'Chi-Squared Goodness of Fit', 3),
    ('chi_squared_independence', 'Chi-Squared Test of Independence', 4),
)


def _seed_skills(apps):
    RevisionChapter = apps.get_model('website', 'RevisionChapter')
    RevisionTopic = apps.get_model('website', 'RevisionTopic')
    RevisionSkill = apps.get_model('website', 'RevisionSkill')

    chapter = RevisionChapter.objects.filter(slug='statistics_probability').first()
    if not chapter:
        return {}

    topic, _ = RevisionTopic.objects.get_or_create(
        slug='hypothesis_testing',
        defaults={
            'chapter': chapter,
            'display_name': 'Hypothesis Testing',
            'order': 5,
        },
    )

    skill_map = {}
    for slug, display_name, order in HYPOTHESIS_TESTING_SKILLS:
        skill, _ = RevisionSkill.objects.get_or_create(
            slug=slug,
            defaults={
                'topic': topic,
                'display_name': display_name,
                'order': order,
            },
        )
        skill_map[slug] = skill
    return skill_map


def _import_mcqs(apps, skill_slug_map):
    MathQB = apps.get_model('website', 'Math_AI_SL_Questionbank')
    RevisionSubQuestion = apps.get_model('website', 'RevisionSubQuestion')
    RevisionMCQOption = apps.get_model('website', 'RevisionMCQOption')

    if not DATA_FILE.exists():
        return

    with DATA_FILE.open(encoding='utf-8') as f:
        data = json.load(f)

    for entry in data:
        qid = entry.get('question_id')
        if qid is None or not MathQB.objects.filter(pk=qid).exists():
            continue

        question = MathQB.objects.get(pk=qid)
        for order_idx, sq_data in enumerate(entry.get('subquestions') or []):
            part = sq_data.get('part_label')
            q_text = sq_data.get('question_text')
            opts = sq_data.get('options') or []
            skill_keys = sq_data.get('skill_keys') or []

            if part is None or q_text is None:
                continue

            sq, _ = RevisionSubQuestion.objects.update_or_create(
                question=question,
                part_label=str(part),
                defaults={
                    'question_text': q_text,
                    'order': order_idx,
                },
            )

            RevisionMCQOption.objects.filter(subquestion=sq).delete()
            for opt in opts:
                RevisionMCQOption.objects.create(
                    subquestion=sq,
                    label=opt['label'],
                    option_text=opt['text'],
                    is_correct=opt['is_correct'],
                )

            if skill_keys:
                resolved = [skill_slug_map[s] for s in skill_keys if s in skill_slug_map]
                sq.skills.set(resolved)


def forwards(apps, schema_editor):
    skill_map = _seed_skills(apps)
    if skill_map:
        _import_mcqs(apps, skill_map)


def backwards(apps, schema_editor):
    MathQB = apps.get_model('website', 'Math_AI_SL_Questionbank')
    RevisionSubQuestion = apps.get_model('website', 'RevisionSubQuestion')
    RevisionMCQOption = apps.get_model('website', 'RevisionMCQOption')
    RevisionSkill = apps.get_model('website', 'RevisionSkill')
    RevisionTopic = apps.get_model('website', 'RevisionTopic')

    if not DATA_FILE.exists():
        return

    with DATA_FILE.open(encoding='utf-8') as f:
        data = json.load(f)

    parts_by_qid = {
        e['question_id']: {str(sq['part_label']) for sq in (e.get('subquestions') or [])}
        for e in data
        if e.get('question_id') is not None
    }

    for qid, labels in parts_by_qid.items():
        if not MathQB.objects.filter(pk=qid).exists():
            continue
        sq_ids = list(
            RevisionSubQuestion.objects.filter(question_id=qid, part_label__in=labels)
            .values_list('pk', flat=True)
        )
        if sq_ids:
            RevisionMCQOption.objects.filter(subquestion_id__in=sq_ids).delete()
            RevisionSubQuestion.objects.filter(pk__in=sq_ids).delete()

    slugs = [slug for slug, _, _ in HYPOTHESIS_TESTING_SKILLS]
    RevisionSkill.objects.filter(slug__in=slugs).delete()
    RevisionTopic.objects.filter(slug='hypothesis_testing').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('website', '0261_seed_distributions_skills_and_mcqs'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
