import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from portal.models import PlatformUser, StudentTodo

TODO_ITEMS = [
    ('Complete UCAS profile', 'https://www.ucas.com/dashboard'),
    ('Upload passport scan', 'https://drive.google.com'),
    ('Submit personal statement draft', 'https://docs.google.com'),
    ('Book mock interview slot', 'https://calendly.com'),
    ('Pay application fee', 'https://www.studyinholland.nl'),
    ('Fill out housing preference form', 'https://www.kamernet.nl'),
    ('Send teacher reference reminder', 'https://mail.google.com'),
    ('Register for admissions test', 'https://www.admissionstesting.org'),
    ('Update extracurricular activities list', 'https://docs.google.com/spreadsheets'),
    ('Review scholarship eligibility', 'https://www.studyportals.com'),
    ('Complete visa checklist', 'https://www.gov.uk/student-visa'),
    ('Upload IELTS certificate', 'https://drive.google.com'),
    ('Confirm university open day attendance', 'https://www.opendays.com'),
    ('Submit portfolio samples', 'https://www.behance.net'),
    ('Review offer conditions', 'https://www.ucas.com/track'),
    ('Complete financial declaration form', 'https://forms.fillout.com'),
    ('Watch pre-departure webinar', 'https://www.youtube.com'),
    ('Sign enrollment agreement', 'https://www.docusign.com'),
    ('Update emergency contact details', 'https://forms.google.com'),
    ('Prepare questions for advisor call', 'https://meet.google.com'),
    ('Submit course preference ranking', 'https://www.universityadmissions.se'),
    ('Upload proof of funds', 'https://drive.google.com'),
    ('Complete health insurance form', 'https://www.zorgverzekeringslijn.nl'),
    ('Review accommodation contract', 'https://www.room.nl'),
]


class Command(BaseCommand):
    help = 'Create sample to-do items for existing students.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of to-do items to create (default: 20).',
        )
        parser.add_argument(
            '--clear-sample',
            action='store_true',
            help='Delete previously seeded sample to-do items before creating new ones.',
        )

    def handle(self, *args, **options):
        count = options['count']
        students = list(
            PlatformUser.objects.filter(role=PlatformUser.Role.STUDENT).order_by('id')
        )
        if not students:
            self.stderr.write(self.style.ERROR('No students found. Create students first.'))
            return

        sample_names = [item[0] for item in TODO_ITEMS]
        if options['clear_sample']:
            deleted, _ = StudentTodo.objects.filter(name__in=sample_names).delete()
            self.stdout.write(f'Removed {deleted} existing sample to-do item(s).')

        today = timezone.localdate()
        pool = TODO_ITEMS.copy()
        random.shuffle(pool)

        created = 0
        for i in range(count):
            name, link = pool[i % len(pool)]
            due_date = today + timedelta(days=random.randint(3, 90))
            StudentTodo.objects.create(
                name=name,
                due_date=due_date,
                link=link,
                student=students[i % len(students)],
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Created {created} to-do item(s) for {len(students)} student(s). '
                f'Total to-do items now: {StudentTodo.objects.count()}.'
            )
        )
