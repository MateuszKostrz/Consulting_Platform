"""Export all university choices to JSON before schema/UI changes."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from portal.models import UniversityChoice


class Command(BaseCommand):
    help = 'Backup UniversityChoice rows to platform_edu/data/backups/ as JSON.'

    def handle(self, *args, **options):
        backup_dir = Path(__file__).resolve().parents[3] / 'data' / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = backup_dir / f'university_choices_{stamp}.json'

        rows = []
        for choice in UniversityChoice.objects.select_related(
            'personal_profile',
            'personal_profile__platform_user',
        ).order_by('id'):
            profile = choice.personal_profile
            student_email = ''
            if profile.platform_user_id:
                student_email = profile.platform_user.email
            rows.append(
                {
                    'id': choice.id,
                    'personal_profile_id': profile.id,
                    'student_email': student_email,
                    'university_name': choice.university_name,
                    'country': choice.country,
                    'degree': choice.degree,
                    'riskiness': choice.riskiness,
                    'comments': choice.comments,
                    'sort_order': choice.sort_order,
                    'created_at': choice.created_at.isoformat(),
                    'updated_at': choice.updated_at.isoformat(),
                }
            )

        payload = {
            'exported_at': datetime.now().isoformat(),
            'count': len(rows),
            'choices': rows,
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Backed up {len(rows)} rows -> {path}'))
