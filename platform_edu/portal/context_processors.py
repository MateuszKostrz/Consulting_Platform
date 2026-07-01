from django.urls import resolve

from .constants import PHONE_COUNTRY_CODES
from .models import PlatformUser
from .profile_access import (
    get_admin_viewing_student,
    get_admin_viewing_student_id,
    get_platform_user,
    get_profile_for_request,
    get_student_platform_users,
    is_impersonating,
    portfolio_design_is_unlocked,
    portfolio_design_is_unlocked_for_platform_user,
    profile_narrative_is_unlocked_for_platform_user,
    interview_preparation_is_unlocked_for_platform_user,
    offers_is_unlocked_for_platform_user,
    strategic_application_is_unlocked_for_platform_user,
)


def consulting_context(request):
    try:
        url_name = resolve(request.path_info).url_name or ''
    except Exception:
        url_name = ''

    platform_user = get_platform_user(request)
    profile = get_profile_for_request(request, create=False)
    viewing_student = get_admin_viewing_student(request)
    impersonating = is_impersonating(request)

    site_name = 'Edunade Consulting'
    role_label = ''
    is_admin = bool(platform_user and platform_user.is_admin)
    show_admin_ui = is_admin
    if platform_user:
        if is_admin:
            role_label = 'Admin'
        else:
            role_label = 'Student'
        site_name = f'Edunade Consulting | {role_label}'

    student_profiles = get_student_platform_users() if show_admin_ui else []

    personal_info_complete = show_admin_ui or bool(profile and profile.is_complete())
    user_profile_photo_url = ''
    if profile and profile.profile_photo:
        user_profile_photo_url = profile.profile_photo.url

    portfolio_design_unlocked = (
        is_admin
        or portfolio_design_is_unlocked_for_platform_user(platform_user)
        or portfolio_design_is_unlocked(profile)
    )
    strategic_application_unlocked = (
        is_admin
        or strategic_application_is_unlocked_for_platform_user(platform_user)
    )
    profile_narrative_unlocked = (
        is_admin
        or profile_narrative_is_unlocked_for_platform_user(platform_user)
    )
    interview_preparation_unlocked = (
        is_admin
        or interview_preparation_is_unlocked_for_platform_user(platform_user)
    )
    offers_unlocked = (
        is_admin
        or offers_is_unlocked_for_platform_user(platform_user)
    )

    return {
        'current_url_name': url_name,
        'current_theme': 'consulting',
        'site_name': site_name,
        'role_label': role_label,
        'user_logged_in': request.user.is_authenticated,
        'user_first_name': request.user.first_name if request.user.is_authenticated else '',
        'user_last_name': request.user.last_name if request.user.is_authenticated else '',
        'user_school_name': profile.school_name if profile else '',
        'user_curriculum': profile.curriculum if profile else '',
        'user_student_type': role_label,
        'user_occupation': '',
        'user_exam_session': profile.graduation_year if profile else '',
        'user_email': request.user.email if request.user.is_authenticated else '',
        'user_avatar': 'avatar0.png',
        'user_profile_photo_url': user_profile_photo_url,
        'user_type': platform_user.role if platform_user else 'none',
        'is_apex_user': False,
        'is_platform_admin': show_admin_ui,
        'is_impersonating': impersonating,
        'personal_info_complete': personal_info_complete,
        'portfolio_design_unlocked': portfolio_design_unlocked,
        'strategic_application_unlocked': strategic_application_unlocked,
        'profile_narrative_unlocked': profile_narrative_unlocked,
        'interview_preparation_unlocked': interview_preparation_unlocked,
        'offers_unlocked': offers_unlocked,
        'student_profiles': student_profiles,
        'admin_viewing_student_id': get_admin_viewing_student_id(request),
        'admin_viewing_student_name': (
            f'{viewing_student.first_name} {viewing_student.last_name}'.strip()
            if viewing_student else ''
        ),
        'phone_country_codes': PHONE_COUNTRY_CODES if show_admin_ui else [],
    }
