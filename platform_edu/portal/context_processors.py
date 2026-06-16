from django.urls import resolve

from .models import PlatformUser
from .profile_access import (
    get_admin_viewing_student,
    get_admin_viewing_student_id,
    get_platform_user,
    get_profile_for_request,
    get_student_platform_users,
)


def consulting_context(request):
    try:
        url_name = resolve(request.path_info).url_name or ''
    except Exception:
        url_name = ''

    platform_user = get_platform_user(request)
    profile = get_profile_for_request(request, create=False)
    viewing_student = get_admin_viewing_student(request)

    site_name = 'Edunade Consulting'
    role_label = ''
    if platform_user:
        role_label = 'Admin' if platform_user.is_admin else 'Student'
        site_name = f'Edunade Consulting | {role_label}'

    student_profiles = get_student_platform_users() if platform_user and platform_user.is_admin else []

    is_admin = bool(platform_user and platform_user.is_admin)

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
        'user_type': platform_user.role if platform_user else 'none',
        'is_apex_user': False,
        'is_platform_admin': is_admin,
        'personal_info_complete': is_admin or bool(profile and profile.is_complete()),
        'student_profiles': student_profiles,
        'admin_viewing_student_id': get_admin_viewing_student_id(request),
        'admin_viewing_student_name': (
            f'{viewing_student.first_name} {viewing_student.last_name}'.strip()
            if viewing_student else ''
        ),
    }
