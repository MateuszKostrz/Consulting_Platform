from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import models
from django.utils import timezone

from .constants import DEADLINE_TIMEZONE_CHOICES


class PlatformUser(models.Model):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        PARENT = 'parent', 'Parent'
        ADMIN = 'admin', 'Admin'

    class ApplicationType(models.TextChoices):
        BACHELOR = 'bachelor', 'Bachelor'
        MASTERS = 'masters', 'Masters'
        PHD = 'phd', 'PhD'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='platform_account',
    )
    first_name = models.CharField(max_length=150, blank=True, default='')
    last_name = models.CharField(max_length=150, blank=True, default='')
    email = models.EmailField(max_length=254, blank=True, default='')
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    application_type = models.CharField(
        max_length=20,
        choices=ApplicationType.choices,
        blank=True,
        default='',
    )
    account_created_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Platform User'
        verbose_name_plural = 'Platform Users'

    def sync_from_user(self):
        if not self.user_id:
            return
        self.first_name = self.user.first_name
        self.last_name = self.user.last_name
        self.email = self.user.email
        if self.account_created_at is None:
            self.account_created_at = self.user.date_joined

    def save(self, *args, **kwargs):
        self.sync_from_user()
        super().save(*args, **kwargs)

    def __str__(self):
        name = f'{self.first_name} {self.last_name}'.strip()
        label = name or self.email or str(self.user_id)
        return f'{label} ({self.get_role_display()})'

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_parent(self):
        return self.role == self.Role.PARENT

    def get_personal_profile(self):
        if not self.is_student:
            return None
        try:
            return self.personal_profile
        except PersonalProfile.DoesNotExist:
            return None


class PersonalProfile(models.Model):
    """Student personal information. Owned by a student account or a guest session."""

    platform_user = models.OneToOneField(
        PlatformUser,
        on_delete=models.CASCADE,
        related_name='personal_profile',
        null=True,
        blank=True,
        limit_choices_to={'role': PlatformUser.Role.STUDENT},
    )
    session_key = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    address = models.TextField(blank=True, default='')
    personal_email = models.EmailField(max_length=200, blank=True, default='')
    edunade_email = models.EmailField(max_length=200, blank=True, default='')
    phone_number = models.CharField(max_length=30, blank=True, default='')
    parent_email = models.EmailField(max_length=254, blank=True, default='')
    nationality = models.CharField(max_length=100, blank=True, default='')
    passport_number = models.CharField(max_length=50, blank=True, default='')
    school_name = models.CharField(max_length=200, blank=True, default='')
    curriculum = models.CharField(max_length=50, blank=True, default='')
    graduation_year = models.CharField(max_length=20, blank=True, default='')
    subjects = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Personal Profile'
        verbose_name_plural = 'Personal Profiles'

    def __str__(self):
        if self.platform_user:
            return f'Personal profile ({self.platform_user.email})'
        label = self.personal_email or self.edunade_email or (self.session_key or '')[:8]
        return f'Personal profile ({label})'

    def is_complete(self):
        required = (
            self.address,
            self.personal_email,
            self.edunade_email,
            self.phone_number,
            self.nationality,
            self.passport_number,
            self.school_name,
            self.curriculum,
            self.graduation_year,
            self.subjects,
        )
        return all(value.strip() for value in required)


class AcademicProfile(models.Model):
    personal_profile = models.OneToOneField(
        PersonalProfile,
        on_delete=models.CASCADE,
        related_name='academic_profile',
    )
    predicted_grades = models.TextField(blank=True, default='')
    standardized_tests = models.TextField(blank=True, default='')
    extracurricular_activities = models.TextField(blank=True, default='')
    awards_competitions = models.TextField(blank=True, default='')
    transcripts = models.FileField(upload_to='academic/transcripts/', blank=True, null=True)
    cv_upload = models.FileField(upload_to='academic/cv/', blank=True, null=True)
    personal_statement_upload = models.FileField(
        upload_to='academic/personal_statements/',
        blank=True,
        null=True,
    )
    intended_course_interests = models.TextField(blank=True, default='')
    country_preferences = models.TextField(blank=True, default='')
    budget_expectations = models.CharField(max_length=50, blank=True, default='')
    parent_input = models.TextField(blank=True, default='')
    career_goals = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Academic Profile'
        verbose_name_plural = 'Academic Profiles'

    def __str__(self):
        return f'Academic profile ({self.personal_profile})'


class DiagnosticStage(models.Model):
    class StageKey(models.TextChoices):
        READINESS = 'readiness', 'Readiness & Profile Assessment'
        HOMEWORK = 'homework', 'Profile Self-Assessment (Homework)'
        TEST = 'test', 'Diagnostic Test'
        REPORT = 'report', 'Diagnostics Report'

    personal_profile = models.ForeignKey(
        PersonalProfile,
        on_delete=models.CASCADE,
        related_name='diagnostic_stages',
    )
    stage_key = models.CharField(max_length=32, choices=StageKey.choices)
    sort_order = models.PositiveSmallIntegerField(default=1)
    template_file = models.FileField(
        upload_to='diagnostics/templates/',
        blank=True,
        null=True,
    )
    student_submission = models.FileField(
        upload_to='diagnostics/student/',
        blank=True,
        null=True,
    )
    admin_document = models.FileField(
        upload_to='diagnostics/admin/',
        blank=True,
        null=True,
    )
    student_submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Diagnostic Stage'
        verbose_name_plural = 'Diagnostic Stages'
        ordering = ['sort_order', 'stage_key']
        constraints = [
            models.UniqueConstraint(
                fields=['personal_profile', 'stage_key'],
                name='unique_diagnostic_stage_per_profile',
            ),
        ]

    def __str__(self):
        owner = self.personal_profile
        if owner.platform_user:
            label = owner.platform_user.email
        else:
            label = owner.personal_email or owner.edunade_email or owner.pk
        return f'{self.get_stage_key_display()} ({label})'

    @property
    def has_student_submission(self):
        return bool(self.student_submission)

    @property
    def has_report(self):
        return self.stage_key == self.StageKey.REPORT and bool(self.admin_document)


class Deadline(models.Model):
    class Urgency(models.TextChoices):
        URGENT = 'urgent', 'Urgent'
        STANDARD = 'standard', 'Standard'
        RELAXED = 'relaxed', 'Relaxed'

    name = models.CharField(max_length=200)
    due_at = models.DateTimeField()
    timezone = models.CharField(
        max_length=64,
        choices=DEADLINE_TIMEZONE_CHOICES,
        default='Europe/Warsaw',
    )
    urgency = models.CharField(
        max_length=20,
        choices=Urgency.choices,
        default=Urgency.STANDARD,
    )
    student = models.ForeignKey(
        PlatformUser,
        on_delete=models.CASCADE,
        related_name='deadlines',
        limit_choices_to={'role': PlatformUser.Role.STUDENT},
    )
    created_by = models.ForeignKey(
        PlatformUser,
        on_delete=models.SET_NULL,
        related_name='created_deadlines',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Deadline'
        verbose_name_plural = 'Deadlines'
        ordering = ['due_at']

    def __str__(self):
        return f'{self.name} ({self.student})'

    @property
    def is_approaching(self):
        return self.due_at <= timezone.now() + timedelta(days=3)

    @property
    def due_at_local(self):
        return self.due_at.astimezone(ZoneInfo(self.timezone))

    @property
    def due_at_local_input(self):
        return self.due_at_local.strftime('%Y-%m-%dT%H:%M')

    @property
    def timezone_display(self):
        return dict(DEADLINE_TIMEZONE_CHOICES).get(self.timezone, self.timezone)


class StudentTodo(models.Model):
    name = models.CharField(max_length=200)
    due_date = models.DateField()
    link = models.URLField(max_length=500, blank=True, default='')
    student = models.ForeignKey(
        PlatformUser,
        on_delete=models.CASCADE,
        related_name='todos',
        limit_choices_to={'role': PlatformUser.Role.STUDENT},
    )
    created_by = models.ForeignKey(
        PlatformUser,
        on_delete=models.SET_NULL,
        related_name='created_todos',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Student to-do'
        verbose_name_plural = 'Student to-dos'
        ordering = ['due_date', 'name']

    def __str__(self):
        return f'{self.name} ({self.student})'


class PortfolioDesign(models.Model):
    personal_profile = models.OneToOneField(
        PersonalProfile,
        on_delete=models.CASCADE,
        related_name='portfolio_design',
    )
    google_doc_url = models.URLField(max_length=500, blank=True, default='')
    is_unlocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Portfolio Design'
        verbose_name_plural = 'Portfolio Designs'

    def __str__(self):
        owner = self.personal_profile
        if owner.platform_user:
            label = owner.platform_user.email
        else:
            label = owner.personal_email or owner.edunade_email or owner.pk
        status = 'unlocked' if self.is_unlocked else 'locked'
        return f'Portfolio Design ({label}, {status})'


class StrategicApplication(models.Model):
    personal_profile = models.OneToOneField(
        PersonalProfile,
        on_delete=models.CASCADE,
        related_name='strategic_application',
    )
    is_unlocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Strategic Application'
        verbose_name_plural = 'Strategic Applications'

    def __str__(self):
        owner = self.personal_profile
        if owner.platform_user:
            label = owner.platform_user.email
        else:
            label = owner.personal_email or owner.edunade_email or owner.pk
        status = 'unlocked' if self.is_unlocked else 'locked'
        return f'Strategic Application ({label}, {status})'


class UniversityChoice(models.Model):
    class Riskiness(models.TextChoices):
        VERY_RISKY = 'very_risky', 'Very risky'
        RISKY = 'risky', 'Risky'
        REALISTIC = 'realistic', 'Realistic'
        SAFE = 'safe', 'Safe'
        VERY_SAFE = 'very_safe', 'Very safe'

    personal_profile = models.ForeignKey(
        PersonalProfile,
        on_delete=models.CASCADE,
        related_name='university_choices',
    )
    university_name = models.CharField(max_length=200)
    degree = models.CharField(max_length=200)
    riskiness = models.CharField(
        max_length=20,
        choices=Riskiness.choices,
        default=Riskiness.REALISTIC,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'University Choice'
        verbose_name_plural = 'University Choices'
        ordering = ['university_name', 'degree', 'id']

    def __str__(self):
        return f'{self.university_name} — {self.degree} ({self.get_riskiness_display()})'


class ProfileNarrative(models.Model):
    personal_profile = models.OneToOneField(
        PersonalProfile,
        on_delete=models.CASCADE,
        related_name='profile_narrative',
    )
    is_unlocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profile Narrative'
        verbose_name_plural = 'Profile Narratives'

    def __str__(self):
        owner = self.personal_profile
        if owner.platform_user:
            label = owner.platform_user.email
        else:
            label = owner.personal_email or owner.edunade_email or owner.pk
        status = 'unlocked' if self.is_unlocked else 'locked'
        return f'Profile Narrative ({label}, {status})'


class InterviewPreparation(models.Model):
    personal_profile = models.OneToOneField(
        PersonalProfile,
        on_delete=models.CASCADE,
        related_name='interview_preparation',
    )
    is_unlocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Interview Preparation'
        verbose_name_plural = 'Interview Preparations'

    def __str__(self):
        owner = self.personal_profile
        if owner.platform_user:
            label = owner.platform_user.email
        else:
            label = owner.personal_email or owner.edunade_email or owner.pk
        status = 'unlocked' if self.is_unlocked else 'locked'
        return f'Interview Preparation ({label}, {status})'


class InterviewPrepSession(models.Model):
    personal_profile = models.ForeignKey(
        PersonalProfile,
        on_delete=models.CASCADE,
        related_name='interview_prep_sessions',
    )
    slot = models.PositiveSmallIntegerField()
    meeting_link = models.URLField(max_length=500, blank=True, default='')
    feedback_file = models.FileField(
        upload_to='interview_prep/feedback/',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Interview Prep Session'
        verbose_name_plural = 'Interview Prep Sessions'
        ordering = ['slot']
        constraints = [
            models.UniqueConstraint(
                fields=['personal_profile', 'slot'],
                name='unique_interview_prep_session_per_profile',
            ),
        ]

    def __str__(self):
        return f'Interview prep session {self.slot} ({self.personal_profile})'

    @property
    def has_meeting_link(self):
        return bool(self.meeting_link.strip())

    @property
    def has_feedback(self):
        return bool(self.feedback_file)

    @property
    def feedback_is_pdf(self):
        if not self.feedback_file:
            return False
        return self.feedback_file.name.lower().endswith('.pdf')


class Offers(models.Model):
    personal_profile = models.OneToOneField(
        PersonalProfile,
        on_delete=models.CASCADE,
        related_name='offers_access',
    )
    is_unlocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Offers'
        verbose_name_plural = 'Offers'

    def __str__(self):
        owner = self.personal_profile
        if owner.platform_user:
            label = owner.platform_user.email
        else:
            label = owner.personal_email or owner.edunade_email or owner.pk
        status = 'unlocked' if self.is_unlocked else 'locked'
        return f'Offers ({label}, {status})'


class Offer(models.Model):
    personal_profile = models.ForeignKey(
        PersonalProfile,
        on_delete=models.CASCADE,
        related_name='offers',
    )
    university_name = models.CharField(max_length=200)
    degree_name = models.CharField(max_length=200)
    offer_requirements = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Offer'
        verbose_name_plural = 'Offers'
        ordering = ['university_name', 'degree_name', 'id']

    def __str__(self):
        return f'{self.university_name} — {self.degree_name}'
