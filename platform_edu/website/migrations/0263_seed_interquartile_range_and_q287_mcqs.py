# Add interquartile_range skill and refresh Math AI SL Q287 MCQ subquestions.

import json
from pathlib import Path

from django.db import migrations

DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'q287_bivariate_mcqs.json'


def _ensure_interquartile_range_skill(apps):
    RevisionChapter = apps.get_model('website', 'RevisionChapter')
    RevisionTopic = apps.get_model('website', 'RevisionTopic')
    RevisionSkill = apps.get_model('website', 'RevisionSkill')

    chapter = RevisionChapter.objects.filter(slug='statistics_probability').first()
    if not chapter:
        return None

    topic = RevisionTopic.objects.filter(slug='descriptive_statistics').first()
    if not topic:
        return None

    skill, _ = RevisionSkill.objects.get_or_create(
        slug='interquartile_range',
        defaults={
            'topic': topic,
            'display_name': 'Interquartile Range',
            'order': 7,
        },
    )
    return skill


def _import_q287(apps, skill_slug_map):
    MathQB = apps.get_model('website', 'Math_AI_SL_Questionbank')
    RevisionSubQuestion = apps.get_model('website', 'RevisionSubQuestion')
    RevisionMCQOption = apps.get_model('website', 'RevisionMCQOption')
    RevisionSkill = apps.get_model('website', 'RevisionSkill')

    if not DATA_FILE.exists() or not MathQB.objects.filter(pk=287).exists():
        return

    skill_slug_map = dict(skill_slug_map)
    skill_slug_map.update({s.slug: s for s in RevisionSkill.objects.all()})

    with DATA_FILE.open(encoding='utf-8') as f:
        data = json.load(f)

    entry = data[0]
    question = MathQB.objects.get(pk=287)
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
    skill = _ensure_interquartile_range_skill(apps)
    skill_map = {'interquartile_range': skill} if skill else {}
    _import_q287(apps, skill_map)


def backwards(apps, schema_editor):
    RevisionSkill = apps.get_model('website', 'RevisionSkill')
    RevisionSkill.objects.filter(slug='interquartile_range').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('website', '0262_seed_hypothesis_testing_skills_and_mcqs'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
