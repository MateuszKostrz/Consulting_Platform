from .models import (
    ApplicationLogistics,
    InterviewPreparation,
    Offers,
    PersonalProfile,
    PlatformUser,
    PortfolioDesign,
    ProfileNarrative,
    Results,
    StrategicApplication,
    StudentSectionAccess,
)
from .profile_access import (
    application_logistics_is_unlocked_for_platform_user,
    ensure_application_logistics,
    ensure_interview_preparation,
    ensure_offers_access,
    ensure_portfolio_design,
    ensure_profile_narrative,
    ensure_results_access,
    ensure_strategic_application,
    ensure_student_personal_profile,
    interview_preparation_is_unlocked_for_platform_user,
    offers_is_unlocked_for_platform_user,
    portfolio_design_is_unlocked_for_platform_user,
    profile_narrative_is_unlocked_for_platform_user,
    results_is_unlocked_for_platform_user,
    strategic_application_is_unlocked_for_platform_user,
)

PLATFORM_SECTIONS = (
    {
        'key': 'personal_information',
        'label': 'Personal Information',
        'default_rule': 'Always available',
    },
    {
        'key': 'academic_profile',
        'label': 'Academic Profile',
        'default_rule': 'Always available',
    },
    {
        'key': 'diagnostics',
        'label': 'Diagnostics',
        'default_rule': 'Available after Personal Information is complete',
    },
    {
        'key': 'portfolio_design',
        'label': 'Portfolio Design',
        'default_rule': 'Unlocked by consultant',
    },
    {
        'key': 'strategic_application',
        'label': 'Strategic Application',
        'default_rule': 'Unlocked by consultant',
    },
    {
        'key': 'profile_narrative',
        'label': 'Profile Narrative',
        'default_rule': 'Unlocked by consultant',
    },
    {
        'key': 'application_logistics',
        'label': 'Application Logistics',
        'default_rule': 'Unlocked by consultant',
    },
    {
        'key': 'interview_preparation',
        'label': 'Interview Preparation',
        'default_rule': 'Unlocked by consultant',
    },
    {
        'key': 'offers',
        'label': 'Offers',
        'default_rule': 'Unlocked by consultant',
    },
    {
        'key': 'results',
        'label': 'Results',
        'default_rule': 'Unlocked by consultant',
    },
)

SECTION_ACCESS_FIELDS = (
    'personal_information',
    'academic_profile',
    'diagnostics',
    'portfolio_design',
    'strategic_application',
    'profile_narrative',
    'application_logistics',
    'interview_preparation',
    'offers',
    'results',
)

SIGNATURE_ADMIN_ROWS = (
    {
        'key': 'strategic_application_signature',
        'label': 'Strategic Application - Signature',
        'default_rule': 'Student signs on Strategic Application page',
    },
)

UNLOCK_MODEL_BY_SECTION = {
    'portfolio_design': (PortfolioDesign, ensure_portfolio_design),
    'strategic_application': (StrategicApplication, ensure_strategic_application),
    'profile_narrative': (ProfileNarrative, ensure_profile_narrative),
    'application_logistics': (ApplicationLogistics, ensure_application_logistics),
    'interview_preparation': (InterviewPreparation, ensure_interview_preparation),
    'offers': (Offers, ensure_offers_access),
    'results': (Results, ensure_results_access),
}


def get_or_create_section_access(student_platform_user):
    access, _ = StudentSectionAccess.objects.get_or_create(
        platform_user=student_platform_user,
    )
    return access


def _default_section_access(platform_user, profile, section_key):
    if section_key in {'personal_information', 'academic_profile'}:
        return True
    if section_key == 'diagnostics':
        return bool(profile and profile.is_complete())
    if section_key == 'portfolio_design':
        return portfolio_design_is_unlocked_for_platform_user(platform_user)
    if section_key == 'strategic_application':
        return strategic_application_is_unlocked_for_platform_user(platform_user)
    if section_key == 'profile_narrative':
        return profile_narrative_is_unlocked_for_platform_user(platform_user)
    if section_key == 'application_logistics':
        return application_logistics_is_unlocked_for_platform_user(platform_user)
    if section_key == 'interview_preparation':
        return interview_preparation_is_unlocked_for_platform_user(platform_user)
    if section_key == 'offers':
        return offers_is_unlocked_for_platform_user(platform_user)
    if section_key == 'results':
        return results_is_unlocked_for_platform_user(platform_user)
    return False


def get_section_override(student_platform_user, section_key):
    if not student_platform_user or not student_platform_user.is_student:
        return None
    try:
        access = student_platform_user.section_access
    except StudentSectionAccess.DoesNotExist:
        return None
    return getattr(access, section_key, None)


def student_has_section_access(platform_user, profile, section_key):
    if not platform_user or not platform_user.is_student:
        return True

    override = get_section_override(platform_user, section_key)
    if override is True:
        return True
    if override is False:
        return False
    return _default_section_access(platform_user, profile, section_key)


def student_can_access_section(request, platform_user, profile, section_key):
    from .profile_access import is_impersonating

    if platform_user and platform_user.is_admin and not is_impersonating(request):
        return True
    return student_has_section_access(platform_user, profile, section_key)


def _sync_unlock_model(profile, section_key, enabled):
    config = UNLOCK_MODEL_BY_SECTION.get(section_key)
    if not config or not profile:
        return
    _, ensure_fn = config
    instance = ensure_fn(profile, create=True)
    if instance and instance.is_unlocked != enabled:
        instance.is_unlocked = enabled
        instance.save(update_fields=['is_unlocked', 'updated_at'])


def _parse_access_value(raw_value):
    value = (raw_value or 'default').strip().lower()
    if value == 'enabled':
        return True
    if value == 'disabled':
        return False
    return None


def save_section_access_from_post(student_platform_user, request):
    access = get_or_create_section_access(student_platform_user)
    profile = ensure_student_personal_profile(student_platform_user, create=True)

    updated_fields = []
    for field_name in SECTION_ACCESS_FIELDS:
        parsed = _parse_access_value(request.POST.get(f'access_{field_name}'))
        if getattr(access, field_name) != parsed:
            setattr(access, field_name, parsed)
            updated_fields.append(field_name)
        if field_name in UNLOCK_MODEL_BY_SECTION and parsed is not None:
            _sync_unlock_model(profile, field_name, parsed)

    if updated_fields:
        access.save(update_fields=updated_fields + ['updated_at'])

    return _save_signature_admin_from_post(profile, request)


def _save_signature_admin_from_post(profile, request):
    if not profile:
        return False

    reset_value = (request.POST.get('access_strategic_application_signature') or '').strip().lower()
    if reset_value != 'reset':
        return False

    strategic = ensure_strategic_application(profile, create=False)
    if not strategic or not strategic.choices_approved_at:
        return False

    strategic.choices_approved_at = None
    strategic.save(update_fields=['choices_approved_at', 'updated_at'])
    return True


def _strategic_application_signature_row(profile):
    config = SIGNATURE_ADMIN_ROWS[0]
    strategic = ensure_strategic_application(profile, create=False)
    signed_at = strategic.choices_approved_at if strategic else None
    return {
        'key': config['key'],
        'label': config['label'],
        'default_rule': config['default_rule'],
        'row_type': 'signature',
        'is_signed': bool(signed_at),
        'signed_at': signed_at,
    }


def _access_mode_label(value):
    if value is True:
        return 'enabled'
    if value is False:
        return 'disabled'
    return 'default'


def section_access_rows_for_student(student_platform_user):
    profile = ensure_student_personal_profile(student_platform_user, create=False)
    access = get_or_create_section_access(student_platform_user)
    rows = []
    for section in PLATFORM_SECTIONS:
        key = section['key']
        override = getattr(access, key)
        rows.append({
            'key': key,
            'label': section['label'],
            'default_rule': section['default_rule'],
            'row_type': 'access',
            'mode': _access_mode_label(override),
            'effective_access': student_has_section_access(
                student_platform_user,
                profile,
                key,
            ),
        })
        if key == 'strategic_application':
            rows.append(_strategic_application_signature_row(profile))
    return rows
