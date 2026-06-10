"""
Import RevisionSubQuestion + RevisionMCQOption rows (and optional QuestionSkillTag)
from a JSON file in the format used by scripts like import_mcq_json.py.

Each top-level object:
  {
    "question_id": <int>,
    "subquestions": [
      {
        "part_label": "a",
        "question_text": "...",
        "skill_keys": ["slug1", ...],   # optional but recommended
        "options": [{"label": "A", "text": "...", "is_correct": bool}, ...]
      },
      ...
    ],
    "revision_tags": ["Display Name", ...]  # optional; question-level QuestionSkillTag by display_name
  }

Usage:
  python manage.py import_revision_mcqs_json /path/to/file.json
  python manage.py import_revision_mcqs_json /path/to/file.json --dry-run
"""

import json
from django.core.management.base import BaseCommand

from website.models import (
    Math_AI_SL_Questionbank,
    RevisionSubQuestion,
    RevisionMCQOption,
    QuestionSkillTag,
    RevisionSkill,
)


class Command(BaseCommand):
    help = 'Import revision MCQ subquestions from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_path',
            type=str,
            help='Path to the JSON file',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse file and report counts without writing to the database',
        )

    def handle(self, *args, **options):
        json_path = options['json_path']
        dry_run = options['dry_run']

        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            self.stderr.write(self.style.ERROR('JSON root must be an array'))
            return

        skill_map_name = {s.display_name: s for s in RevisionSkill.objects.all()}
        skill_slug_map = {s.slug: s for s in RevisionSkill.objects.all()}

        sq_created = sq_updated = opt_created = 0
        sq_skill_set = sq_skill_skip = 0
        q_tag_created = q_tag_skipped = 0
        errors = []

        for entry in data:
            qid = entry.get('question_id')
            if qid is None:
                errors.append('Entry missing question_id — skipped')
                continue

            try:
                question = Math_AI_SL_Questionbank.objects.get(id=qid)
            except Math_AI_SL_Questionbank.DoesNotExist:
                errors.append(f'Q{qid}: question not found — skipped')
                continue

            sub_list = entry.get('subquestions') or []
            if not sub_list:
                errors.append(f'Q{qid}: no subquestions — skipped')
                continue

            if dry_run:
                self.stdout.write(f'[dry-run] Q{qid}: would import {len(sub_list)} subquestions')
                continue

            for order_idx, sq_data in enumerate(sub_list):
                part = sq_data.get('part_label')
                q_text = sq_data.get('question_text')
                opts = sq_data.get('options') or []
                skill_keys = sq_data.get('skill_keys') or []

                if part is None or q_text is None:
                    errors.append(f'Q{qid}: subquestion missing part_label or question_text — skipped')
                    continue

                sq, created = RevisionSubQuestion.objects.update_or_create(
                    question=question,
                    part_label=str(part),
                    defaults={
                        'question_text': q_text,
                        'order': order_idx,
                    },
                )
                sq_created += 1 if created else 0
                sq_updated += 0 if created else 1

                RevisionMCQOption.objects.filter(subquestion=sq).delete()
                for opt in opts:
                    RevisionMCQOption.objects.create(
                        subquestion=sq,
                        label=opt['label'],
                        option_text=opt['text'],
                        is_correct=opt['is_correct'],
                    )
                    opt_created += 1

                if skill_keys:
                    resolved = []
                    for slug in skill_keys:
                        skill = skill_slug_map.get(slug)
                        if skill:
                            resolved.append(skill)
                            sq_skill_set += 1
                        else:
                            errors.append(
                                f'Q{qid}({part}): skill slug "{slug}" not found — skipped for M2M'
                            )
                            sq_skill_skip += 1
                    sq.skills.set(resolved)

            for tag_name in entry.get('revision_tags') or []:
                skill = skill_map_name.get(tag_name)
                if not skill:
                    errors.append(f'Q{qid}: revision_tag "{tag_name}" not found — skipped')
                    q_tag_skipped += 1
                    continue
                _, created_tag = QuestionSkillTag.objects.get_or_create(
                    question=question,
                    skill=skill,
                    defaults={'weight': 1.0},
                )
                q_tag_created += 1 if created_tag else 0
                q_tag_skipped += 1 if not created_tag else 0

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run only — nothing written.'))
            return

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Subquestions: {sq_created} created, {sq_updated} updated.'
        ))
        self.stdout.write(f'Options created: {opt_created}')
        self.stdout.write(f'Subquestion skills set: {sq_skill_set}; skipped refs: {sq_skill_skip}')
        self.stdout.write(
            f'Question-level tags: {q_tag_created} new get_or_create, {q_tag_skipped} duplicates / skipped refs'
        )
        if errors:
            self.stderr.write(self.style.WARNING(f'{len(errors)} warning(s):'))
            for e in errors[:80]:
                self.stderr.write(f'  {e}')
            if len(errors) > 80:
                self.stderr.write(f'  … and {len(errors) - 80} more')
