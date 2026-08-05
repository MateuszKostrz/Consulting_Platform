from django.urls import resolve, reverse

from .constants import PHONE_COUNTRY_CODES
from .profile_access import (
    get_admin_viewing_student,
    get_admin_viewing_student_id,
    get_platform_user,
    get_profile_for_request,
    get_student_platform_users,
    graduation_years_for_student_filter,
    is_impersonating,
)
from .section_access_utils import student_has_section_access
from .section_navigation import next_section_url_name


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

    access_user = platform_user
    access_profile = profile
    if impersonating and platform_user and platform_user.is_student:
        access_user = platform_user
        access_profile = profile
    elif show_admin_ui and viewing_student:
        access_user = viewing_student
        access_profile = viewing_student.get_personal_profile()

    personal_info_complete = show_admin_ui or bool(profile and profile.is_complete())
    user_profile_photo_url = ''
    if profile and profile.profile_photo:
        user_profile_photo_url = profile.profile_photo.url

    def section_unlocked(section_key):
        if show_admin_ui and not impersonating:
            return True
        return student_has_section_access(access_user, access_profile, section_key)

    continue_section = next_section_url_name(url_name)

    return {
        'current_url_name': url_name,
        'section_continue_url_name': continue_section,
        'section_continue_url': reverse(continue_section),
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
        'personal_information_unlocked': section_unlocked('personal_information'),
        'academic_profile_unlocked': section_unlocked('academic_profile'),
        'diagnostics_unlocked': section_unlocked('diagnostics'),
        'portfolio_design_unlocked': section_unlocked('portfolio_design'),
        'strategic_application_unlocked': section_unlocked('strategic_application'),
        'profile_narrative_unlocked': section_unlocked('profile_narrative'),
        'application_logistics_unlocked': section_unlocked('application_logistics'),
        'interview_preparation_unlocked': section_unlocked('interview_preparation'),
        'offers_unlocked': section_unlocked('offers'),
        'results_unlocked': section_unlocked('results'),
        'student_profiles': student_profiles,
        'student_graduation_years': graduation_years_for_student_filter(student_profiles),
        'admin_viewing_student_id': get_admin_viewing_student_id(request),
        'admin_viewing_student_name': (
            f'{viewing_student.first_name} {viewing_student.last_name}'.strip()
            if viewing_student else ''
        ),
        'phone_country_codes': PHONE_COUNTRY_CODES if show_admin_ui else [],
    }
