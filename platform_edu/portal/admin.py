from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import AcademicProfile, DiagnosticStage, PersonalProfile, PlatformUser


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
        'account_created_at',
        'created_at',
    )
    list_filter = ('role',)
    search_fields = ('email', 'first_name', 'last_name')
    readonly_fields = ('account_created_at', 'created_at', 'updated_at')
    fields = (
        'user',
        'first_name',
        'last_name',
        'email',
        'role',
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
