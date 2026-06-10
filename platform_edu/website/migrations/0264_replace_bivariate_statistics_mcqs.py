# Replace all bivariate statistics MCQ subquestions (16 questions, 81 subquestions).

import json
from pathlib import Path

from django.db import migrations

DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / 'data'
    / 'ib_math_ai_sl_bivariate_statistics_mcqs_skillkeys_full.json'
)

BIVARIATE_QUESTION_IDS = (
    161, 162, 163, 164, 165, 166, 167,
    183, 184, 185,
    232, 233, 234,
    285, 286, 287,
)


def _delete_chapter_subquestions(apps, question_ids):
    RevisionSubQuestion = apps.get_model('website', 'RevisionSubQuestion')
    RevisionMCQOption = apps.get_model('website', 'RevisionMCQOption')

    sq_ids = list(
        RevisionSubQuestion.objects.filter(question_id__in=question_ids)
        .values_list('pk', flat=True)
    )
    if sq_ids:
        RevisionMCQOption.objects.filter(subquestion_id__in=sq_ids).delete()
        RevisionSubQuestion.objects.filter(pk__in=sq_ids).delete()


def _import_mcqs(apps, skill_slug_map):
    MathQB = apps.get_model('website', 'Math_AI_SL_Questionbank')
    RevisionSubQuestion = apps.get_model('website', 'RevisionSubQuestion')
    RevisionMCQOption = apps.get_model('website', 'RevisionMCQOption')
    RevisionSkill = apps.get_model('website', 'RevisionSkill')

    if not DATA_FILE.exists():
        return

    skill_slug_map = dict(skill_slug_map)
    skill_slug_map.update({s.slug: s for s in RevisionSkill.objects.all()})

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

            sq = RevisionSubQuestion.objects.create(
                question=question,
                part_label=str(part),
                question_text=q_text,
                order=order_idx,
            )

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
    _delete_chapter_subquestions(apps, BIVARIATE_QUESTION_IDS)
    _import_mcqs(apps, {})


def backwards(apps, schema_editor):
    _delete_chapter_subquestions(apps, BIVARIATE_QUESTION_IDS)


class Migration(migrations.Migration):
    dependencies = [
        ('website', '0263_seed_interquartile_range_and_q287_mcqs'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
