# Replace Math AI SL Q287 MCQ subquestions (10 parts, mixed descriptive + bivariate tags).

import json
from pathlib import Path

from django.db import migrations

DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'q287_bivariate_mcqs.json'
QUESTION_ID = 287


def _delete_subquestions(apps, question_id):
    RevisionSubQuestion = apps.get_model('website', 'RevisionSubQuestion')
    RevisionMCQOption = apps.get_model('website', 'RevisionMCQOption')

    sq_ids = list(
        RevisionSubQuestion.objects.filter(question_id=question_id)
        .values_list('pk', flat=True)
    )
    if sq_ids:
        RevisionMCQOption.objects.filter(subquestion_id__in=sq_ids).delete()
        RevisionSubQuestion.objects.filter(pk__in=sq_ids).delete()


def _import_q287(apps):
    MathQB = apps.get_model('website', 'Math_AI_SL_Questionbank')
    RevisionSubQuestion = apps.get_model('website', 'RevisionSubQuestion')
    RevisionMCQOption = apps.get_model('website', 'RevisionMCQOption')
    RevisionSkill = apps.get_model('website', 'RevisionSkill')

    if not DATA_FILE.exists() or not MathQB.objects.filter(pk=QUESTION_ID).exists():
        return

    skill_slug_map = {s.slug: s for s in RevisionSkill.objects.all()}
    question = MathQB.objects.get(pk=QUESTION_ID)

    with DATA_FILE.open(encoding='utf-8') as f:
        entry = json.load(f)[0]

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
    _delete_subquestions(apps, QUESTION_ID)
    _import_q287(apps)


def backwards(apps, schema_editor):
    _delete_subquestions(apps, QUESTION_ID)


class Migration(migrations.Migration):
    dependencies = [
        ('website', '0264_replace_bivariate_statistics_mcqs'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
