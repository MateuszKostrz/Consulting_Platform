from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import (
    AcademicProfile,
    Deadline,
    DiagnosticStage,
    InterviewPreparation,
    InterviewPrepSession,
    Offer,
    Offers,
    PersonalProfile,
    PlatformUser,
    PortfolioDesign,
    ProfileNarrative,
    StrategicApplication,
    UniversityChoice,
)


class PlatformUserInline(admin.StackedInline):
    model = PlatformUser
    can_delete = False
    extra = 0
    fields = ('role', 'first_name', 'last_name', 'email', 'account_created_at', 'created_at', 'updated_at')
    readonly_fields = ('first_name', 'last_name', 'email', 'account_created_at', 'created_at', 'updated_at')


class CustomUserAdmin(DjangoUserAdmin):
    inlines = (PlatformUserInline,)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(PlatformUser)
class PlatformUserAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'first_name',
        'last_name',
        'role',
        'application_type',
        'account_created_at',
        'created_at',
    )
    list_filter = ('role', 'application_type')
    search_fields = ('email', 'first_name', 'last_name')
    readonly_fields = ('account_created_at', 'created_at', 'updated_at')
    fields = (
        'user',
        'first_name',
        'last_name',
        'email',
        'role',
        'application_type',
        'account_created_at',
        'created_at',
        'updated_at',
    )


@admin.register(PersonalProfile)
class PersonalProfileAdmin(admin.ModelAdmin):
    list_display = (
        'display_owner',
        'personal_email',
        'school_name',
        'curriculum',
        'graduation_year',
        'updated_at',
    )
    list_filter = ('curriculum', 'graduation_year')
    search_fields = (
        'personal_email',
        'edunade_email',
        'parent_email',
        'phone_number',
        'school_name',
        'session_key',
        'platform_user__email',
    )
    readonly_fields = ('session_key', 'created_at', 'updated_at')
    autocomplete_fields = ('platform_user',)

    @admin.display(description='Owner')
    def display_owner(self, obj):
        if obj.platform_user:
            return obj.platform_user.email
        return f'Guest ({obj.session_key[:8]}...)' if obj.session_key else '—'


@admin.register(AcademicProfile)
class AcademicProfileAdmin(admin.ModelAdmin):
    list_display = (
        'display_student',
        'budget_expectations',
        'updated_at',
    )
    search_fields = (
        'personal_profile__platform_user__email',
        'personal_profile__personal_email',
        'personal_profile__edunade_email',
        'personal_profile__school_name',
        'intended_course_interests',
        'career_goals',
    )
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Student')
    def display_student(self, obj):
        platform_user = obj.personal_profile.platform_user
        if platform_user:
            return platform_user.email
        return obj.personal_profile.personal_email or obj.personal_profile.edunade_email or '—'


@admin.register(DiagnosticStage)
class DiagnosticStageAdmin(admin.ModelAdmin):
    list_display = (
        'display_student',
        'stage_key',
        'has_student_submission',
        'updated_at',
    )
    list_filter = ('stage_key',)
    search_fields = (
        'personal_profile__platform_user__email',
        'personal_profile__personal_email',
        'personal_profile__edunade_email',
    )
    readonly_fields = ('student_submitted_at', 'created_at', 'updated_at')
    autocomplete_fields = ('personal_profile',)

    @admin.display(description='Student')
    def display_student(self, obj):
        platform_user = obj.personal_profile.platform_user
        if platform_user:
            return platform_user.email
        return obj.personal_profile.personal_email or obj.personal_profile.edunade_email or '—'

    @admin.display(boolean=True, description='Submitted')
    def has_student_submission(self, obj):
        return obj.has_student_submission


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'display_student',
        'urgency',
        'due_at',
        'created_at',
    )
    list_filter = ('urgency',)
    search_fields = (
        'name',
        'student__email',
        'student__first_name',
        'student__last_name',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('student', 'created_by')

    @admin.display(description='Student')
    def display_student(self, obj):
        return f'{obj.student.first_name} {obj.student.last_name}'.strip() or obj.student.email


@admin.register(PortfolioDesign)
class PortfolioDesignAdmin(admin.ModelAdmin):
    list_display = (
        'display_student',
        'is_unlocked',
        'google_doc_url',
        'updated_at',
    )
    list_filter = ('is_unlocked',)
    search_fields = (
        'personal_profile__platform_user__email',
        'personal_profile__personal_email',
        'personal_profile__edunade_email',
        'google_doc_url',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('personal_profile',)

    @admin.display(description='Student')
    def display_student(self, obj):
        platform_user = obj.personal_profile.platform_user
        if platform_user:
            return platform_user.email
        return obj.personal_profile.personal_email or obj.personal_profile.edunade_email or '—'


@admin.register(StrategicApplication)
class StrategicApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'display_student',
        'is_unlocked',
        'updated_at',
    )
    list_filter = ('is_unlocked',)
    search_fields = (
        'personal_profile__platform_user__email',
        'personal_profile__personal_email',
        'personal_profile__edunade_email',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('personal_profile',)

    @admin.display(description='Student')
    def display_student(self, obj):
        platform_user = obj.personal_profile.platform_user
        if platform_user:
            return platform_user.email
        return obj.personal_profile.personal_email or obj.personal_profile.edunade_email or '—'


@admin.register(ProfileNarrative)
class ProfileNarrativeAdmin(admin.ModelAdmin):
    list_display = (
        'display_student',
        'is_unlocked',
        'updated_at',
    )
    list_filter = ('is_unlocked',)
    search_fields = (
        'personal_profile__platform_user__email',
        'personal_profile__personal_email',
        'personal_profile__edunade_email',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('personal_profile',)

    @admin.display(description='Student')
    def display_student(self, obj):
        platform_user = obj.personal_profile.platform_user
        if platform_user:
            return platform_user.email
        return obj.personal_profile.personal_email or obj.personal_profile.edunade_email or '—'


@admin.register(InterviewPreparation)
class InterviewPreparationAdmin(admin.ModelAdmin):
    list_display = (
        'display_student',
        'is_unlocked',
        'updated_at',
    )
    list_filter = ('is_unlocked',)
    search_fields = (
        'personal_profile__platform_user__email',
        'personal_profile__personal_email',
        'personal_profile__edunade_email',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('personal_profile',)

    @admin.display(description='Student')
    def display_student(self, obj):
        platform_user = obj.personal_profile.platform_user
        if platform_user:
            return platform_user.email
        return obj.personal_profile.personal_email or obj.personal_profile.edunade_email or '—'


@admin.register(InterviewPrepSession)
class InterviewPrepSessionAdmin(admin.ModelAdmin):
    list_display = (
        'slot',
        'display_student',
        'meeting_link',
        'has_feedback',
        'updated_at',
    )
    list_filter = ('slot',)
    search_fields = (
        'meeting_link',
        'personal_profile__platform_user__email',
        'personal_profile__personal_email',
        'personal_profile__edunade_email',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('personal_profile',)

    @admin.display(description='Student')
    def display_student(self, obj):
        platform_user = obj.personal_profile.platform_user
        if platform_user:
            return platform_user.email
        return obj.personal_profile.personal_email or obj.personal_profile.edunade_email or '—'

    @admin.display(boolean=True, description='Feedback')
    def has_feedback(self, obj):
        return obj.has_feedback


@admin.register(Offers)
class OffersAdmin(admin.ModelAdmin):
    list_display = (
        'display_student',
        'is_unlocked',
        'updated_at',
    )
    list_filter = ('is_unlocked',)
    search_fields = (
        'personal_profile__platform_user__email',
        'personal_profile__personal_email',
        'personal_profile__edunade_email',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('personal_profile',)

    @admin.display(description='Student')
    def display_student(self, obj):
        platform_user = obj.personal_profile.platform_user
        if platform_user:
            return platform_user.email
        return obj.personal_profile.personal_email or obj.personal_profile.edunade_email or '—'


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        'university_name',
        'degree_name',
        'display_student',
        'updated_at',
    )
    search_fields = (
        'university_name',
        'degree_name',
        'offer_requirements',
        'personal_profile__platform_user__email',
        'personal_profile__personal_email',
        'personal_profile__edunade_email',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('personal_profile',)

    @admin.display(description='Student')
    def display_student(self, obj):
        platform_user = obj.personal_profile.platform_user
        if platform_user:
            return platform_user.email
        return obj.personal_profile.personal_email or obj.personal_profile.edunade_email or '—'


@admin.register(UniversityChoice)
class UniversityChoiceAdmin(admin.ModelAdmin):
    list_display = (
        'university_name',
        'degree',
        'riskiness',
        'display_student',
        'updated_at',
    )
    list_filter = ('riskiness',)
    search_fields = (
        'university_name',
        'degree',
        'personal_profile__platform_user__email',
        'personal_profile__personal_email',
        'personal_profile__edunade_email',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('personal_profile',)

    @admin.display(description='Student')
    def display_student(self, obj):
        platform_user = obj.personal_profile.platform_user
        if platform_user:
            return platform_user.email
        return obj.personal_profile.personal_email or obj.personal_profile.edunade_email or '—'
