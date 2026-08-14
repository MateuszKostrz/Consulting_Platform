import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .constants import GRADUATION_YEARS, INTERVIEW_PREP_SESSION_SLOTS
from .models import (
    AcademicProfile,
    ApplicationLogistics,
    PersonalProfile,
    PlatformUser,
    PortfolioDesign,
    ProfileNarrative,
    StrategicApplication,
    InterviewPreparation,
    InterviewPrepSession,
    Offer,
    Offers,
    Results,
)

ADMIN_VIEWING_STUDENT_SESSION_KEY = 'admin_viewing_student_id'
ADMIN_IMPERSONATOR_USER_ID_KEY = 'admin_impersonator_user_id'
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
    'school_address',
    'parent_first_name',
    'parent_last_name',
    'parent_email',
    'parent_phone',
    'parent2_first_name',
    'parent2_last_name',
    'parent2_email',
    'parent2_phone',
    'curriculum',
    'curriculum_other',
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
    'primary_course_preference',
    'secondary_course_preference',
    'excluded_countries_cities',
    'budget_expectations',
    'budget_currency',
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


def is_impersonating(request):
    return bool(request.session.get(ADMIN_IMPERSONATOR_USER_ID_KEY))


def get_impersonator_user_id(request):
    return request.session.get(ADMIN_IMPERSONATOR_USER_ID_KEY)


def set_impersonator_user_id(request, user_id):
    request.session[ADMIN_IMPERSONATOR_USER_ID_KEY] = user_id
    request.session.modified = True


def clear_impersonator_user_id(request):
    if ADMIN_IMPERSONATOR_USER_ID_KEY in request.session:
        del request.session[ADMIN_IMPERSONATOR_USER_ID_KEY]
        request.session.modified = True


def get_impersonator_user(request):
    from django.contrib.auth import get_user_model

    user_id = get_impersonator_user_id(request)
    if not user_id:
        return None
    User = get_user_model()
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        clear_impersonator_user_id(request)
        return None


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
    ).select_related('personal_profile').order_by('last_name', 'first_name', 'email')


def graduation_years_for_student_filter(student_profiles):
    """Graduation years that have at least one student, preserving standard order."""
    present = set()
    for student in student_profiles:
        profile = student.get_personal_profile()
        if profile and profile.graduation_year:
            present.add(profile.graduation_year.strip())
    ordered = [year for year in GRADUATION_YEARS if year in present]
    extras = sorted(present - set(GRADUATION_YEARS))
    return ordered + extras


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


def _sync_personal_email_from_login(profile, student_platform_user):
    """Backfill personal_email from the login email for legacy accounts."""
    if not student_platform_user or not student_platform_user.email:
        return False
    if profile.personal_email:
        return False
    profile.personal_email = student_platform_user.email
    profile.save(update_fields=['personal_email', 'updated_at'])
    return True


def sync_profile_personal_email(profile):
    if not profile or not profile.platform_user_id:
        return profile
    _sync_personal_email_from_login(profile, profile.platform_user)
    return profile


def admin_editing_student_profile(request):
    platform_user = get_platform_user(request)
    if not platform_user or not platform_user.is_admin or is_impersonating(request):
        return False
    return get_admin_viewing_student(request) is not None


def update_student_login_email(student_platform_user, new_email):
    """Update a student's login email via personal_email."""
    if not student_platform_user or not student_platform_user.is_student:
        raise ValidationError('Invalid student account.')

    new_email = new_email.strip().lower()
    if not new_email:
        raise ValidationError('Personal email is required.')
    try:
        validate_email(new_email)
    except ValidationError:
        raise ValidationError('Please enter a valid personal email address.') from None

    auth_user = student_platform_user.user
    if auth_user.email.lower() == new_email:
        profile = ensure_student_personal_profile(student_platform_user, create=False)
        if profile and profile.personal_email != new_email:
            profile.personal_email = new_email
            profile.save(update_fields=['personal_email', 'updated_at'])
        return False

    if User.objects.filter(email__iexact=new_email).exclude(pk=auth_user.pk).exists():
        raise ValidationError('An account with this email already exists.')
    if User.objects.filter(username__iexact=new_email).exclude(pk=auth_user.pk).exists():
        raise ValidationError('An account with this email already exists.')

    auth_user.email = new_email
    auth_user.username = new_email
    auth_user.save(update_fields=['email', 'username'])

    profile = ensure_student_personal_profile(student_platform_user, create=False)
    if profile:
        profile.personal_email = new_email
        profile.save(update_fields=['personal_email', 'updated_at'])
    return True


def ensure_student_personal_profile(student_platform_user, create=True):
    if not create:
        return PersonalProfile.objects.filter(
            platform_user=student_platform_user,
        ).first()

    profile, _ = PersonalProfile.objects.get_or_create(
        platform_user=student_platform_user,
        defaults={
            'session_key': None,
            'personal_email': student_platform_user.email,
        },
    )
    _sync_personal_email_from_login(profile, student_platform_user)
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
    if not target_profile.personal_email and student_platform_user.email:
        target_profile.personal_email = student_platform_user.email
        updated_fields.append('personal_email')
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


def ensure_portfolio_design(profile, create=True):
    if not profile:
        return None
    if not create:
        try:
            return profile.portfolio_design
        except PortfolioDesign.DoesNotExist:
            return None
    portfolio, _ = PortfolioDesign.objects.get_or_create(personal_profile=profile)
    return portfolio


def portfolio_design_is_unlocked(profile):
    portfolio = ensure_portfolio_design(profile, create=False)
    return bool(portfolio and portfolio.is_unlocked)


def portfolio_design_is_unlocked_for_platform_user(platform_user):
    if not platform_user or not platform_user.is_student:
        return False
    return PortfolioDesign.objects.filter(
        personal_profile__platform_user_id=platform_user.pk,
        is_unlocked=True,
    ).exists()


def get_portfolio_design_for_request(profile, platform_user, create=True):
    if platform_user and platform_user.is_student:
        design = PortfolioDesign.objects.filter(
            personal_profile__platform_user_id=platform_user.pk,
        ).first()
        if design:
            return design
    if not profile:
        return None
    return ensure_portfolio_design(profile, create=create)


def ensure_strategic_application(profile, create=True):
    if not profile:
        return None
    if not create:
        try:
            return profile.strategic_application
        except StrategicApplication.DoesNotExist:
            return None
    strategic, _ = StrategicApplication.objects.get_or_create(personal_profile=profile)
    return strategic


def strategic_application_is_unlocked_for_platform_user(platform_user):
    if not platform_user or not platform_user.is_student:
        return False
    return StrategicApplication.objects.filter(
        personal_profile__platform_user_id=platform_user.pk,
        is_unlocked=True,
    ).exists()


def get_strategic_application_for_request(profile, platform_user, create=True):
    if platform_user and platform_user.is_student:
        strategic = StrategicApplication.objects.filter(
            personal_profile__platform_user_id=platform_user.pk,
        ).first()
        if strategic:
            return strategic
    if not profile:
        return None
    return ensure_strategic_application(profile, create=create)


def ensure_profile_narrative(profile, create=True):
    if not profile:
        return None
    if not create:
        try:
            return profile.profile_narrative
        except ProfileNarrative.DoesNotExist:
            return None
    narrative, _ = ProfileNarrative.objects.get_or_create(personal_profile=profile)
    return narrative


def profile_narrative_is_unlocked_for_platform_user(platform_user):
    if not platform_user or not platform_user.is_student:
        return False
    return ProfileNarrative.objects.filter(
        personal_profile__platform_user_id=platform_user.pk,
        is_unlocked=True,
    ).exists()


def get_profile_narrative_for_request(profile, platform_user, create=True):
    if platform_user and platform_user.is_student:
        narrative = ProfileNarrative.objects.filter(
            personal_profile__platform_user_id=platform_user.pk,
        ).first()
        if narrative:
            return narrative
    if not profile:
        return None
    return ensure_profile_narrative(profile, create=create)


def ensure_application_logistics(profile, create=True):
    if not profile:
        return None
    if not create:
        try:
            return profile.application_logistics
        except ApplicationLogistics.DoesNotExist:
            return None
    logistics, _ = ApplicationLogistics.objects.get_or_create(personal_profile=profile)
    return logistics


def application_logistics_is_unlocked_for_platform_user(platform_user):
    if not platform_user or not platform_user.is_student:
        return False
    return ApplicationLogistics.objects.filter(
        personal_profile__platform_user_id=platform_user.pk,
        is_unlocked=True,
    ).exists()


def get_application_logistics_for_request(profile, platform_user, create=True):
    if platform_user and platform_user.is_student:
        logistics = ApplicationLogistics.objects.filter(
            personal_profile__platform_user_id=platform_user.pk,
        ).first()
        if logistics:
            return logistics
    if not profile:
        return None
    return ensure_application_logistics(profile, create=create)


def ensure_interview_preparation(profile, create=True):
    if not profile:
        return None
    if not create:
        try:
            return profile.interview_preparation
        except InterviewPreparation.DoesNotExist:
            return None
    preparation, _ = InterviewPreparation.objects.get_or_create(personal_profile=profile)
    return preparation


def ensure_interview_prep_sessions(profile):
    if not profile:
        return []
    for slot in INTERVIEW_PREP_SESSION_SLOTS:
        InterviewPrepSession.objects.get_or_create(
            personal_profile=profile,
            slot=slot,
        )
    return list(profile.interview_prep_sessions.order_by('slot'))


def interview_preparation_is_unlocked_for_platform_user(platform_user):
    if not platform_user or not platform_user.is_student:
        return False
    return InterviewPreparation.objects.filter(
        personal_profile__platform_user_id=platform_user.pk,
        is_unlocked=True,
    ).exists()


def get_interview_preparation_for_request(profile, platform_user, create=True):
    if platform_user and platform_user.is_student:
        preparation = InterviewPreparation.objects.filter(
            personal_profile__platform_user_id=platform_user.pk,
        ).first()
        if preparation:
            return preparation
    if not profile:
        return None
    return ensure_interview_preparation(profile, create=create)


def ensure_offers_access(profile, create=True):
    if not profile:
        return None
    if not create:
        try:
            return profile.offers_access
        except Offers.DoesNotExist:
            return None
    offers_access, _ = Offers.objects.get_or_create(personal_profile=profile)
    return offers_access


def offers_is_unlocked_for_platform_user(platform_user):
    if not platform_user or not platform_user.is_student:
        return False
    return Offers.objects.filter(
        personal_profile__platform_user_id=platform_user.pk,
        is_unlocked=True,
    ).exists()


def get_offers_access_for_request(profile, platform_user, create=True):
    if platform_user and platform_user.is_student:
        offers_access = Offers.objects.filter(
            personal_profile__platform_user_id=platform_user.pk,
        ).first()
        if offers_access:
            return offers_access
    if not profile:
        return None
    return ensure_offers_access(profile, create=create)


def ensure_results_access(profile, create=True):
    if not profile:
        return None
    if not create:
        try:
            return profile.results_access
        except Results.DoesNotExist:
            return None
    results_access, _ = Results.objects.get_or_create(personal_profile=profile)
    return results_access


def results_is_unlocked_for_platform_user(platform_user):
    if not platform_user or not platform_user.is_student:
        return False
    return Results.objects.filter(
        personal_profile__platform_user_id=platform_user.pk,
        is_unlocked=True,
    ).exists()


def get_results_access_for_request(profile, platform_user, create=True):
    if platform_user and platform_user.is_student:
        results_access = Results.objects.filter(
            personal_profile__platform_user_id=platform_user.pk,
        ).first()
        if results_access:
            return results_access
    if not profile:
        return None
    return ensure_results_access(profile, create=create)
