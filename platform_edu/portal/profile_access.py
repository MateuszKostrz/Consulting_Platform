import uuid

from .models import AcademicProfile, PersonalProfile, PlatformUser

ADMIN_VIEWING_STUDENT_SESSION_KEY = 'admin_viewing_student_id'
DEADLINE_FILTER_STUDENT_SESSION_KEY = 'deadline_filter_student_id'
PROFILE_SESSION_KEY = 'profile_session_key'

PERSONAL_PROFILE_MERGE_FIELDS = (
    'address',
    'personal_email',
    'edunade_email',
    'phone_number',
    'nationality',
    'passport_number',
    'school_name',
    'curriculum',
    'graduation_year',
    'subjects',
)

ACADEMIC_PROFILE_MERGE_FIELDS = (
    'predicted_grades',
    'standardized_tests',
    'extracurricular_activities',
    'awards_competitions',
    'intended_course_interests',
    'country_preferences',
    'budget_expectations',
    'parent_input',
    'career_goals',
)


def ensure_profile_session_key(request):
    if PROFILE_SESSION_KEY not in request.session:
        request.session[PROFILE_SESSION_KEY] = uuid.uuid4().hex
        request.session.modified = True
    return request.session[PROFILE_SESSION_KEY]


def clear_profile_session_key(request):
    if PROFILE_SESSION_KEY in request.session:
        del request.session[PROFILE_SESSION_KEY]
        request.session.modified = True


def get_platform_user(request):
    if not request.user.is_authenticated:
        return None
    try:
        return request.user.platform_account
    except PlatformUser.DoesNotExist:
        return None


def get_admin_viewing_student_id(request):
    return request.session.get(ADMIN_VIEWING_STUDENT_SESSION_KEY)


def set_admin_viewing_student(request, student_platform_user):
    request.session[ADMIN_VIEWING_STUDENT_SESSION_KEY] = student_platform_user.id
    request.session.modified = True


def clear_admin_viewing_student(request):
    if ADMIN_VIEWING_STUDENT_SESSION_KEY in request.session:
        del request.session[ADMIN_VIEWING_STUDENT_SESSION_KEY]
        request.session.modified = True


def get_deadline_filter_student_id(request):
    return request.session.get(DEADLINE_FILTER_STUDENT_SESSION_KEY)


def set_deadline_filter_student(request, student_id):
    request.session[DEADLINE_FILTER_STUDENT_SESSION_KEY] = student_id
    request.session.modified = True


def clear_deadline_filter_student(request):
    if DEADLINE_FILTER_STUDENT_SESSION_KEY in request.session:
        del request.session[DEADLINE_FILTER_STUDENT_SESSION_KEY]
        request.session.modified = True


def get_deadline_filter_student(request):
    student_id = get_deadline_filter_student_id(request)
    if not student_id:
        return None
    try:
        return PlatformUser.objects.get(
            pk=student_id,
            role=PlatformUser.Role.STUDENT,
        )
    except PlatformUser.DoesNotExist:
        clear_deadline_filter_student(request)
        return None


def get_student_platform_users():
    return PlatformUser.objects.filter(
        role=PlatformUser.Role.STUDENT,
    ).order_by('last_name', 'first_name', 'email')


def get_admin_viewing_student(request):
    student_id = get_admin_viewing_student_id(request)
    if not student_id:
        return None
    try:
        return PlatformUser.objects.get(
            pk=student_id,
            role=PlatformUser.Role.STUDENT,
        )
    except PlatformUser.DoesNotExist:
        clear_admin_viewing_student(request)
        return None


def _sync_edunade_email(profile, student_platform_user):
    if not student_platform_user or not student_platform_user.email:
        return False
    if profile.edunade_email == student_platform_user.email:
        return False
    profile.edunade_email = student_platform_user.email
    profile.save(update_fields=['edunade_email', 'updated_at'])
    return True


def sync_profile_edunade_email(profile):
    if not profile or not profile.platform_user_id:
        return profile
    _sync_edunade_email(profile, profile.platform_user)
    return profile


def ensure_student_personal_profile(student_platform_user, create=True):
    if not create:
        profile = PersonalProfile.objects.filter(
            platform_user=student_platform_user,
        ).first()
        if profile:
            _sync_edunade_email(profile, student_platform_user)
        return profile

    profile, _ = PersonalProfile.objects.get_or_create(
        platform_user=student_platform_user,
        defaults={
            'session_key': None,
            'edunade_email': student_platform_user.email,
        },
    )
    _sync_edunade_email(profile, student_platform_user)
    return profile


def _merge_text_fields(source, target, field_names):
    updated_fields = []
    for field_name in field_names:
        source_value = getattr(source, field_name, '')
        target_value = getattr(target, field_name, '')
        if source_value and not target_value:
            setattr(target, field_name, source_value)
            updated_fields.append(field_name)
    return updated_fields


def _merge_academic_profiles(source_personal_profile, target_personal_profile):
    try:
        source_academic = source_personal_profile.academic_profile
    except AcademicProfile.DoesNotExist:
        return

    target_academic, _ = AcademicProfile.objects.get_or_create(
        personal_profile=target_personal_profile,
    )
    updated_fields = _merge_text_fields(
        source_academic,
        target_academic,
        ACADEMIC_PROFILE_MERGE_FIELDS,
    )
    for upload_field in ('transcripts', 'cv_upload', 'personal_statement_upload'):
        if not getattr(target_academic, upload_field) and getattr(source_academic, upload_field):
            setattr(
                target_academic,
                upload_field,
                getattr(source_academic, upload_field),
            )
            updated_fields.append(upload_field)
    if updated_fields:
        target_academic.save(update_fields=updated_fields + ['updated_at'])


def _merge_personal_profiles(source_profile, target_profile, student_platform_user):
    updated_fields = _merge_text_fields(
        source_profile,
        target_profile,
        PERSONAL_PROFILE_MERGE_FIELDS,
    )
    if not target_profile.edunade_email and student_platform_user.email:
        target_profile.edunade_email = student_platform_user.email
        updated_fields.append('edunade_email')
    if updated_fields:
        target_profile.save(update_fields=updated_fields + ['updated_at'])
    _merge_academic_profiles(source_profile, target_profile)


def claim_guest_profile_for_student(request, student_platform_user):
    session_key = request.session.get(PROFILE_SESSION_KEY)
    if not session_key:
        return

    guest_profile = PersonalProfile.objects.filter(
        session_key=session_key,
        platform_user__isnull=True,
    ).first()
    clear_profile_session_key(request)
    if not guest_profile:
        return

    student_profile = ensure_student_personal_profile(student_platform_user)
    if guest_profile.pk == student_profile.pk:
        return

    _merge_personal_profiles(guest_profile, student_profile, student_platform_user)
    guest_profile.delete()


def get_profile_for_request(request, create=True):
    platform_user = get_platform_user(request)

    if platform_user and platform_user.is_admin:
        viewing_student = get_admin_viewing_student(request)
        if viewing_student:
            return ensure_student_personal_profile(viewing_student, create=create)
        return None

    if request.user.is_authenticated:
        if platform_user and platform_user.is_student:
            return ensure_student_personal_profile(platform_user, create=create)
        return None

    session_key = (
        ensure_profile_session_key(request)
        if create
        else request.session.get(PROFILE_SESSION_KEY)
    )
    if not session_key:
        return None

    if create:
        profile, _ = PersonalProfile.objects.get_or_create(session_key=session_key)
        return profile

    return PersonalProfile.objects.filter(session_key=session_key).first()


def admin_must_select_student(request):
    platform_user = get_platform_user(request)
    return bool(
        platform_user
        and platform_user.is_admin
        and not get_admin_viewing_student_id(request)
    )
