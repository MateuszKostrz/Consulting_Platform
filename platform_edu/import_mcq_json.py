"""
Import MCQ subquestions, options, and skill tags from a JSON file.

Usage (from platform_edu/):
    python manage.py shell < ../import_mcq_json.py
    OR run directly:
    python import_mcq_json.py
"""
import os, sys, json, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'platform_edu.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from website.models import (
    Math_AI_SL_Questionbank,
    RevisionSubQuestion, RevisionMCQOption,
    QuestionSkillTag, RevisionSkill,
)

JSON_PATH = '/Users/mateuszkostrz/Downloads/ib_math_ai_sl_trigonometry_mcqs_skillkeys.json'

with open(JSON_PATH, encoding='utf-8') as f:
    data = json.load(f)

# Build skill display_name → slug lookup
skill_map = {s.display_name: s for s in RevisionSkill.objects.all()}

sq_created = sq_updated = opt_created = 0
sq_skill_set = sq_skill_skip = 0
q_tag_created = q_tag_skipped = 0
errors = []

# Also build slug → skill lookup for per-subquestion skill_keys
skill_slug_map = {s.slug: s for s in RevisionSkill.objects.all()}

for entry in data:
    qid = entry['question_id']

    try:
        question = Math_AI_SL_Questionbank.objects.get(id=qid)
    except Math_AI_SL_Questionbank.DoesNotExist:
        errors.append(f'Q{qid}: question not found in DB — skipped')
        continue

    # ── MCQ subquestions, options, and per-subquestion skill tags ───────
    for sq_data in entry.get('subquestions', []):
        part      = sq_data['part_label']
        q_text    = sq_data['question_text']
        opts      = sq_data['options']
        skill_keys = sq_data.get('skill_keys', [])

        sq, created = RevisionSubQuestion.objects.update_or_create(
            question=question,
            part_label=part,
            defaults={'question_text': q_text},
        )
        if created:
            sq_created += 1
        else:
            sq_updated += 1

        # Wipe and recreate options to avoid stale data
        RevisionMCQOption.objects.filter(subquestion=sq).delete()
        for opt in opts:
            RevisionMCQOption.objects.create(
                subquestion=sq,
                label=opt['label'],
                option_text=opt['text'],
                is_correct=opt['is_correct'],
            )
            opt_created += 1

        # Set per-subquestion skills (replace all existing)
        if skill_keys:
            resolved = []
            for slug in skill_keys:
                skill = skill_slug_map.get(slug)
                if skill:
                    resolved.append(skill)
                    sq_skill_set += 1
                else:
                    errors.append(f'Q{qid}({part}): skill slug "{slug}" not found — skipped')
                    sq_skill_skip += 1
            sq.skills.set(resolved)

    # ── Question-level skill tags (revision_tags by display_name) ───────
    for tag_name in entry.get('revision_tags', []):
        skill = skill_map.get(tag_name)
        if not skill:
            errors.append(f'Q{qid}: revision_tag "{tag_name}" not found — skipped')
            q_tag_skipped += 1
            continue
        _, created = QuestionSkillTag.objects.get_or_create(
            question=question, skill=skill, defaults={'weight': 1.0},
        )
        if created:
            q_tag_created += 1
        else:
            q_tag_skipped += 1

print(f'\n✓ Done.')
print(f'  Subquestions:        {sq_created} created, {sq_updated} updated')
print(f'  Options:             {opt_created} created')
print(f'  Subquestion skills:  {sq_skill_set} set, {sq_skill_skip} skipped')
print(f'  Question-level tags: {q_tag_created} new, {q_tag_skipped} already existed / skipped')
if errors:
    print(f'\nWarnings ({len(errors)}):')
    for e in errors:
        print(' ', e)
