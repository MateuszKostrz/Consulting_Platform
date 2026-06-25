import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from portal.models import Deadline, PlatformUser
from portal.constants import DEADLINE_TIMEZONE_CHOICES

DEADLINE_NAMES = [
    'UCAS application submission',
    'Oxford interview preparation',
    'Cambridge written assessment',
    'Amsterdam payment deadline',
    'Personal statement final draft',
    'Reference letter follow-up',
    'SAT registration deadline',
    'Portfolio upload',
    'Scholarship application',
    'Visa document submission',
    'Housing deposit payment',
    'IELTS score submission',
    'Extracurricular summary update',
    'Mock interview session',
    'Financial aid form',
    'Transcript request',
    'Summer program application',
    'Research proposal draft',
    'Recommendation reminder',
    'Enrollment confirmation',
    'Course selection deadline',
    'Medical form submission',
    'Insurance policy upload',
    'Orientation registration',
    'Foundation year payment',
]

URGENCY_WEIGHTS = [
    (Deadline.Urgency.URGENT, 3),
    (Deadline.Urgency.STANDARD, 4),
    (Deadline.Urgency.RELAXED, 3),
]


class Command(BaseCommand):
    help = 'Create sample deadlines for existing students.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of deadlines to create (default: 50).',
        )
        parser.add_argument(
            '--clear-sample',
            action='store_true',
            help='Delete previously seeded sample deadlines before creating new ones.',
        )

    def handle(self, *args, **options):
        count = options['count']
        students = list(
            PlatformUser.objects.filter(role=PlatformUser.Role.STUDENT).order_by('id')
        )
        if not students:
            self.stderr.write(self.style.ERROR('No students found. Create students first.'))
            return

        if options['clear_sample']:
            deleted, _ = Deadline.objects.filter(name__in=DEADLINE_NAMES).delete()
            self.stdout.write(f'Removed {deleted} existing sample deadline(s).')

        urgencies = []
        for urgency, weight in URGENCY_WEIGHTS:
            urgencies.extend([urgency] * weight)

        now = timezone.now()
        created = 0
        for _ in range(count):
            days_ahead = random.choice([
                random.randint(1, 7),
                random.randint(8, 30),
                random.randint(31, 44),
                random.randint(45, 90),
                random.randint(45, 120),
            ])
            due_at = now + timedelta(
                days=days_ahead,
                hours=random.randint(9, 17),
                minutes=random.choice([0, 15, 30, 45]),
            )
            Deadline.objects.create(
                name=random.choice(DEADLINE_NAMES),
                due_at=due_at,
                timezone=random.choice(DEADLINE_TIMEZONE_CHOICES)[0],
                urgency=random.choice(urgencies),
                student=random.choice(students),
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Created {created} deadline(s) for {len(students)} student(s). '
                f'Total deadlines now: {Deadline.objects.count()}.'
            )
        )
