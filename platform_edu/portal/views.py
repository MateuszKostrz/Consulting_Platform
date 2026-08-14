import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlencode

from .constants import (
    ALLOWED_UPLOAD_EXTENSIONS,
    BUDGET_CHOICES,
    BUDGET_CURRENCY_CHOICES,
    COUNTRY_CHOICES,
    DEADLINE_TIMEZONE_CHOICES,
    DEADLINE_TIMEZONE_VALUES,
    DIAGNOSTIC_STAGE_KEYS,
    DIAGNOSTIC_CALL_BOOKING_URL,
    GRADUATION_YEARS,
    IB_SUBJECT_CHOICES,
    INTERVIEW_FEEDBACK_EXTENSIONS,
    INTERVIEW_PREP_SESSION_SLOTS,
    MAX_UPLOAD_SIZE,
    RESULT_DOCUMENT_TYPE_CHOICES,
    RESULT_DOCUMENT_TYPE_VALUES,
)
from .reference_contacts_utils import (
    MAX_REFERENCE_CONTACTS,
    reference_contacts_for_form,
    save_reference_contacts,
)
from .budget_utils import budget_exchange_rates_response, save_budget_fields
from .course_wishes_utils import ordered_countries_for_form, save_course_wishes
from .diagnostics_access import get_diagnostic_stage_items
from .activity_entries_utils import (
    activity_entries_for_form,
    save_activity_entries,
)
from .section_access_utils import (
    save_section_access_from_post,
    section_access_rows_for_student,
    student_can_access_section,
)
from .section_navigation import redirect_after_section_save
from .subjects_utils import curriculum_for_form, curriculum_from_post, subjects_for_form, subjects_from_post
from .models import (
    AcademicProfile,
    ApplicationLogisticsPortal,
    Deadline,
    DiagnosticStage,
    InterviewPrepSession,
    Offer,
    PlatformUser,
    ResultDocument,
    StudentTodo,
    UniversityChoice,
    PortfolioDesignElement,
)
from .upload_utils import (
    ACADEMIC_UPLOAD_FIELDS,
    assign_file_field,
    can_delete_academic_upload,
    can_delete_diagnostic_upload,
    clear_file_field,
    replace_profile_photo,
)
from .register_utils import (
    _register_form_context,
    _register_response,
    _validate_admin_student_form,
    _validate_register_form,
    create_registered_user,
)
from .profile_access import (
    admin_editing_student_profile,
    admin_must_select_student,
    claim_guest_profile_for_student,
    clear_admin_viewing_student,
    clear_deadline_filter_student,
    clear_impersonator_user_id,
    clear_profile_session_key,
    ensure_application_logistics,
    ensure_interview_preparation,
    ensure_interview_prep_sessions,
    ensure_portfolio_design,
    ensure_profile_narrative,
    ensure_strategic_application,
    get_admin_viewing_student,
    get_admin_viewing_student_id,
    get_impersonator_user,
    get_application_logistics_for_request,
    get_interview_preparation_for_request,
    get_platform_user,
    get_profile_for_request,
    get_portfolio_design_for_request,
    get_profile_narrative_for_request,
    get_strategic_application_for_request,
    get_student_platform_users,
    is_impersonating,
    set_admin_viewing_student,
    set_impersonator_user_id,
    sync_profile_personal_email,
    update_student_login_email,
)

_NATIONALITY_CHOICES = [
    'Afghanistan', 'Australia', 'Austria', 'Belgium', 'Brazil', 'Canada', 'China',
    'France', 'Germany', 'India', 'Ireland', 'Italy', 'Japan', 'Mexico', 'Netherlands',
    'New Zealand', 'Norway', 'Poland', 'Portugal', 'Singapore', 'South Africa',
    'South Korea', 'Spain', 'Sweden', 'Switzerland', 'United Arab Emirates',
    'United Kingdom', 'United States', 'Other',
]


def _get_or_create_profile(request):
    return get_profile_for_request(request, create=True)


def _get_or_create_academic(profile):
    academic, _ = AcademicProfile.objects.get_or_create(personal_profile=profile)
    return academic


_SECTION_LABELS = {
    'personal_information': 'Personal Information',
    'academic_profile': 'Academic Profile',
    'diagnostics': 'Diagnostics',
    'portfolio_design': 'Portfolio Design',
    'strategic_application': 'Strategic Application',
    'profile_narrative': 'Profile Narrative',
    'application_logistics': 'Application Logistics',
    'interview_preparation': 'Interview Preparation',
    'offers': 'Offers',
    'results': 'Results',
}


def _require_section_access(request, platform_user, profile, section_key):
    if student_can_access_section(request, platform_user, profile, section_key):
        return None
    label = _SECTION_LABELS.get(section_key, 'This section')
    messages.warning(request, f'{label} is not available for your account.')
    return redirect('home')


def _validate_upload(uploaded_file):
    if not uploaded_file:
        return None

    if uploaded_file.size > MAX_UPLOAD_SIZE:
        return 'File must be 10 MB or smaller.'

    extension = os.path.splitext(uploaded_file.name)[1].lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        return 'Only PDF, DOC, and DOCX files are allowed.'

    return None


def _assign_upload(instance, field_name, uploaded_file):
    return assign_file_field(instance, field_name, uploaded_file)


def _handle_academic_file_delete(request, profile, academic):
    platform_user = get_platform_user(request)
    field_name = request.POST.get('field_name', '').strip()

    if field_name not in ACADEMIC_UPLOAD_FIELDS:
        messages.error(request, 'Unknown file type.')
        return redirect('academic-profile')

    if not can_delete_academic_upload(platform_user):
        messages.error(request, 'You do not have permission to delete this file.')
        return redirect('academic-profile')

    if not getattr(academic, field_name):
        messages.info(request, 'No file to delete.')
        return redirect('academic-profile')

    clear_file_field(academic, field_name)
    academic.save()
    messages.success(request, f'{ACADEMIC_UPLOAD_FIELDS[field_name]} deleted. You can upload a new file.')
    return redirect('academic-profile')


def _handle_diagnostic_file_delete(request, profile, platform_user):
    stage_key = request.POST.get('stage_key', '').strip()
    field_name = request.POST.get('field_name', '').strip()

    if stage_key not in DIAGNOSTIC_STAGE_KEYS:
        messages.error(request, 'Unknown diagnostics stage.')
        return redirect('diagnostics')

    if field_name not in {'template_file', 'student_submission', 'admin_document'}:
        messages.error(request, 'Unknown file type.')
        return redirect('diagnostics')

    if not can_delete_diagnostic_upload(request, platform_user, field_name):
        messages.error(request, 'You do not have permission to delete this file.')
        return redirect('diagnostics')

    stage = get_object_or_404(
        DiagnosticStage,
        personal_profile=profile,
        stage_key=stage_key,
    )

    if not getattr(stage, field_name):
        messages.info(request, 'No file to delete.')
        return redirect('diagnostics')

    clear_file_field(stage, field_name)
    if field_name == 'student_submission':
        stage.student_submitted_at = None
    stage.save()
    messages.success(request, 'File deleted. You can upload a new one.')
    return redirect('diagnostics')


def _parse_deadline_datetime(value, tz_name):
    if not value:
        return None
    if tz_name not in DEADLINE_TIMEZONE_VALUES:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return None
    if timezone.is_aware(parsed):
        parsed = timezone.make_naive(parsed)
    return parsed.replace(tzinfo=tz)


def _validate_deadline_form(request):
    name = request.POST.get('name', '').strip()
    due_at_raw = request.POST.get('due_at', '').strip()
    urgency = request.POST.get('urgency', '').strip()
    student_id = request.POST.get('student_id', '').strip()
    tz_name = request.POST.get('timezone', '').strip()

    errors = []
    if not name:
        errors.append('Deadline name is required.')
    due_at = _parse_deadline_datetime(due_at_raw, tz_name)
    if not due_at:
        errors.append('A valid date, time, and timezone are required.')
    if urgency not in Deadline.Urgency.values:
        errors.append('Please choose a valid urgency level.')

    student = None
    if not student_id:
        errors.append('Please select a student.')
    else:
        student = PlatformUser.objects.filter(
            pk=student_id,
            role=PlatformUser.Role.STUDENT,
        ).first()
        if not student:
            errors.append('Selected student was not found.')

    return errors, name, due_at, urgency, student, tz_name


def _handle_add_deadline(request, platform_user):
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only consultants can add deadlines.')
        return redirect('home')

    errors, name, due_at, urgency, student, tz_name = _validate_deadline_form(request)
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('home')

    Deadline.objects.create(
        name=name,
        due_at=due_at,
        timezone=tz_name,
        urgency=urgency,
        student=student,
        created_by=platform_user,
    )
    messages.success(request, 'Deadline added successfully.')
    return redirect('home')


def _handle_edit_deadline(request, platform_user):
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only consultants can edit deadlines.')
        return redirect('home')

    deadline_id = request.POST.get('deadline_id', '').strip()
    if not deadline_id:
        messages.error(request, 'Deadline not found.')
        return redirect('home')

    deadline = Deadline.objects.filter(pk=deadline_id).first()
    if not deadline:
        messages.error(request, 'Deadline not found.')
        return redirect('home')

    errors, name, due_at, urgency, student, tz_name = _validate_deadline_form(request)
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('home')

    deadline.name = name
    deadline.due_at = due_at
    deadline.timezone = tz_name
    deadline.urgency = urgency
    deadline.student = student
    deadline.save()
    messages.success(request, 'Deadline updated successfully.')
    return redirect('home')


def _handle_delete_deadline(request, platform_user):
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only consultants can delete deadlines.')
        return redirect('home')

    deadline_id = request.POST.get('deadline_id', '').strip()
    deadline = Deadline.objects.filter(pk=deadline_id).first()
    if not deadline:
        messages.error(request, 'Deadline not found.')
        return redirect('home')

    deadline.delete()
    messages.success(request, 'Deadline deleted successfully.')
    return redirect('home')


def _get_deadlines_for_user(platform_user, request=None):
    queryset = Deadline.objects.select_related('student').order_by('due_at')
    if platform_user and platform_user.is_student:
        queryset = queryset.filter(student=platform_user)
    return queryset


def _normalize_todo_link(value):
    link = value.strip()
    if not link:
        return ''
    if not link.startswith(('http://', 'https://')):
        return f'https://{link}'
    return link


def _parse_todo_due_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _validate_todo_form(request):
    name = request.POST.get('name', '').strip()
    due_date_raw = request.POST.get('due_date', '').strip()
    link_raw = request.POST.get('link', '').strip()
    student_id = request.POST.get('student_id', '').strip()

    errors = []
    if not name:
        errors.append('Item name is required.')

    due_date = _parse_todo_due_date(due_date_raw)
    if not due_date:
        errors.append('A valid deadline date is required.')

    link = _normalize_todo_link(link_raw)
    if link_raw and not link:
        errors.append('Please enter a valid hyperlink.')

    student = None
    if not student_id:
        errors.append('Please select a student.')
    else:
        student = PlatformUser.objects.filter(
            pk=student_id,
            role=PlatformUser.Role.STUDENT,
        ).first()
        if not student:
            errors.append('Selected student was not found.')

    return errors, name, due_date, link, student


def _handle_add_todo(request, platform_user):
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only consultants can add to-do items.')
        return redirect('home')

    errors, name, due_date, link, student = _validate_todo_form(request)
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('home')

    StudentTodo.objects.create(
        name=name,
        due_date=due_date,
        link=link,
        student=student,
        created_by=platform_user,
    )
    messages.success(request, 'To-do item added successfully.')
    return redirect('home')


def _handle_edit_todo(request, platform_user):
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only consultants can edit to-do items.')
        return redirect('home')

    todo_id = request.POST.get('todo_id', '').strip()
    if not todo_id:
        messages.error(request, 'To-do item not found.')
        return redirect('home')

    todo = StudentTodo.objects.filter(pk=todo_id).first()
    if not todo:
        messages.error(request, 'To-do item not found.')
        return redirect('home')

    errors, name, due_date, link, student = _validate_todo_form(request)
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('home')

    todo.name = name
    todo.due_date = due_date
    todo.link = link
    todo.student = student
    todo.save()
    messages.success(request, 'To-do item updated successfully.')
    return redirect('home')


def _handle_delete_todo(request, platform_user):
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only consultants can delete to-do items.')
        return redirect('home')

    todo_id = request.POST.get('todo_id', '').strip()
    todo = StudentTodo.objects.filter(pk=todo_id).first()
    if not todo:
        messages.error(request, 'To-do item not found.')
        return redirect('home')

    todo.delete()
    messages.success(request, 'To-do item deleted successfully.')
    return redirect('home')


def _get_todos_for_user(platform_user, request=None):
    queryset = StudentTodo.objects.select_related('student').order_by('due_date', 'name')
    if platform_user and platform_user.is_student:
        queryset = queryset.filter(student=platform_user)
    return queryset


def home(request):
    platform_user = get_platform_user(request)

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        if action == 'add_deadline':
            return _handle_add_deadline(request, platform_user)
        if action == 'edit_deadline':
            return _handle_edit_deadline(request, platform_user)
        if action == 'delete_deadline':
            return _handle_delete_deadline(request, platform_user)
        if action == 'add_todo':
            return _handle_add_todo(request, platform_user)
        if action == 'edit_todo':
            return _handle_edit_todo(request, platform_user)
        if action == 'delete_todo':
            return _handle_delete_todo(request, platform_user)

    deadlines = _get_deadlines_for_user(platform_user, request)
    todos = _get_todos_for_user(platform_user, request)
    today = timezone.localdate()
    upcoming_end = today + timedelta(days=7)
    can_manage = bool(platform_user and platform_user.is_admin)
    credential_portals = _get_credential_portals_for_home(request, platform_user)
    return render(request, 'home.html', {
        'deadlines_all': deadlines,
        'deadlines_urgent': deadlines.filter(urgency=Deadline.Urgency.URGENT),
        'deadlines_standard': deadlines.filter(urgency=Deadline.Urgency.STANDARD),
        'deadlines_relaxed': deadlines.filter(urgency=Deadline.Urgency.RELAXED),
        'deadline_total_count': deadlines.count(),
        'deadline_urgent_count': deadlines.filter(urgency=Deadline.Urgency.URGENT).count(),
        'deadline_today_count': deadlines.filter(due_at__date=today).count(),
        'deadline_upcoming_count': deadlines.filter(
            due_at__date__gte=today,
            due_at__date__lte=upcoming_end,
        ).count(),
        'can_manage_deadlines': can_manage,
        'can_manage_todos': can_manage,
        'deadline_students': get_student_platform_users() if can_manage else [],
        'todo_students': get_student_platform_users() if can_manage else [],
        'deadline_timezone_choices': DEADLINE_TIMEZONE_CHOICES,
        'todos_all': todos,
        'todo_total_count': todos.count(),
        'students_list': get_student_platform_users() if can_manage else [],
        'credential_portals': credential_portals,
    })


def _get_credential_portals_for_home(request, platform_user):
    if not platform_user or not platform_user.is_student:
        return []
    profile = get_profile_for_request(request, create=False)
    if not profile:
        return []
    if not student_can_access_section(request, platform_user, profile, 'application_logistics'):
        return []
    return list(profile.application_logistics_portals.order_by('sort_order', 'id'))


def _redirect_admin_without_student(request):
    next_path = request.get_full_path()
    params = urlencode({'pick_student': '1', 'next': next_path})
    return redirect(f'{reverse("home")}?{params}')


def personal_information(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None:
        return _redirect_admin_without_student(request)

    platform_user = get_platform_user(request)
    blocked = _require_section_access(
        request, platform_user, profile, 'personal_information',
    )
    if blocked:
        return blocked

    sync_profile_personal_email(profile)

    if request.method == 'POST':
        if request.POST.get('action') == 'delete_profile_photo':
            if profile.profile_photo:
                clear_file_field(profile, 'profile_photo')
                profile.save(update_fields=['profile_photo', 'updated_at'])
                messages.success(request, 'Profile photo deleted.')
            else:
                messages.info(request, 'No profile photo to delete.')
            return redirect('personal-information')

        profile.address = request.POST.get('address', '').strip()
        admin_editing_student = admin_editing_student_profile(request)
        viewing_student = get_admin_viewing_student(request)

        if admin_editing_student and viewing_student and profile.platform_user_id == viewing_student.id:
            new_personal_email = request.POST.get('personal_email', '').strip()
            try:
                update_student_login_email(viewing_student, new_personal_email)
                profile.refresh_from_db()
            except ValidationError as exc:
                messages.error(request, '; '.join(exc.messages) if exc.messages else str(exc))
                return redirect('personal-information')
            profile.personal_email = new_personal_email
            profile.edunade_email = request.POST.get('edunade_email', '').strip()
        elif not profile.platform_user_id:
            profile.personal_email = request.POST.get('personal_email', '').strip()
            profile.edunade_email = request.POST.get('edunade_email', '').strip()
        profile.phone_number = request.POST.get('phone_number', '').strip()
        profile.nationality = request.POST.get('nationality', '').strip()
        profile.passport_number = request.POST.get('passport_number', '').strip()
        profile.school_name = request.POST.get('school_name', '').strip()
        profile.school_address = request.POST.get('school_address', '').strip()
        profile.parent_first_name = request.POST.get('parent_first_name', '').strip()
        profile.parent_last_name = request.POST.get('parent_last_name', '').strip()
        profile.parent_email = request.POST.get('parent_email', '').strip()
        profile.parent_phone = request.POST.get('parent_phone', '').strip()
        profile.parent2_first_name = request.POST.get('parent2_first_name', '').strip()
        profile.parent2_last_name = request.POST.get('parent2_last_name', '').strip()
        profile.parent2_email = request.POST.get('parent2_email', '').strip()
        profile.parent2_phone = request.POST.get('parent2_phone', '').strip()
        profile.curriculum, profile.curriculum_other = curriculum_from_post(request)
        profile.graduation_year = request.POST.get('graduation_year', '').strip()
        profile.subjects = subjects_from_post(request)

        uploaded_photo = request.FILES.get('profile_photo')
        if uploaded_photo:
            photo_error = replace_profile_photo(profile, uploaded_photo)
            if photo_error:
                messages.error(request, photo_error)
                return redirect('personal-information')

        profile.save()
        profile.refresh_from_db()
        messages.success(request, 'Personal information saved successfully.')
        return redirect_after_section_save(request, 'personal-information')

    selected_subjects, custom_subjects = subjects_for_form(profile.subjects)
    curriculum_select, curriculum_other = curriculum_for_form(
        profile.curriculum,
        profile.curriculum_other,
    )

    return render(request, 'personal_information.html', {
        'info': profile,
        'admin_editing_student_profile': admin_editing_student_profile(request),
        'school_name': profile.school_name,
        'curriculum': curriculum_select,
        'curriculum_other': curriculum_other,
        'selected_subjects': selected_subjects,
        'custom_subjects': custom_subjects,
        'ib_subjects': IB_SUBJECT_CHOICES,
        'nationalities': _NATIONALITY_CHOICES,
        'graduation_years': GRADUATION_YEARS,
        'profile_photo_url': profile.profile_photo.url if profile.profile_photo else '',
        'profile_photo_download_url': reverse('download-profile-photo') if profile.profile_photo else '',
        'profile_photo_upload_url': reverse('upload-profile-photo'),
    })


def academic_profile(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None:
        return _redirect_admin_without_student(request)

    platform_user = get_platform_user(request)
    blocked = _require_section_access(
        request, platform_user, profile, 'academic_profile',
    )
    if blocked:
        return blocked

    academic = _get_or_create_academic(profile)

    if request.method == 'POST':
        academic.predicted_grades = request.POST.get('predicted_grades', '').strip()
        academic.intended_course_interests = request.POST.get(
            'intended_course_interests', ''
        ).strip()
        save_course_wishes(academic, request)
        save_budget_fields(academic, request)
        academic.parent_input = request.POST.get('parent_input', '').strip()
        academic.save()
        save_reference_contacts(academic, request)
        save_activity_entries(academic, request)
        messages.success(request, 'Academic profile saved successfully.')
        return redirect_after_section_save(request, 'academic-profile')

    reference_contacts, reference_contacts_visible = reference_contacts_for_form(academic, profile)
    activity_entries = activity_entries_for_form(academic)

    return render(request, 'academic_profile.html', {
        'profile': profile,
        'academic': academic,
        'school_name': profile.school_name,
        'school_address': profile.school_address,
        'country_choices': COUNTRY_CHOICES,
        'ordered_countries': ordered_countries_for_form(academic),
        'budget_choices': BUDGET_CHOICES,
        'budget_currency_choices': BUDGET_CURRENCY_CHOICES,
        'reference_contacts': reference_contacts,
        'reference_contacts_visible': reference_contacts_visible,
        'reference_contacts_max': MAX_REFERENCE_CONTACTS,
        'activity_entries': activity_entries,
    })


def budget_exchange_rates(request):
    return budget_exchange_rates_response()


def _handle_diagnostic_upload(request, profile, platform_user):
    if request.POST.get('action') == 'delete_file':
        return _handle_diagnostic_file_delete(request, profile, platform_user)

    stage_key = request.POST.get('stage_key', '').strip()
    upload_field = request.POST.get('upload_field', '').strip()
    uploaded_file = request.FILES.get('upload_file')

    if stage_key not in DIAGNOSTIC_STAGE_KEYS:
        messages.error(request, 'Unknown diagnostics stage.')
        return redirect('diagnostics')

    if upload_field not in {'template_file', 'student_submission', 'admin_document'}:
        messages.error(request, 'Unknown upload type.')
        return redirect('diagnostics')

    is_admin = bool(platform_user and platform_user.is_admin)
    if upload_field == 'template_file' and not is_admin:
        messages.error(request, 'Only consultants can upload template documents.')
        return redirect('diagnostics')

    if upload_field == 'admin_document' and not is_admin:
        messages.error(request, 'Only consultants can upload consultant documents.')
        return redirect('diagnostics')

    if upload_field == 'student_submission' and not request.user.is_authenticated:
        messages.error(request, 'Please log in to upload your submission.')
        return redirect('diagnostics')

    if not uploaded_file:
        messages.error(request, 'Please choose a file to upload.')
        return redirect('diagnostics')

    upload_error = _validate_upload(uploaded_file)
    if upload_error:
        messages.error(request, upload_error)
        return redirect('diagnostics')

    stage = get_object_or_404(
        DiagnosticStage,
        personal_profile=profile,
        stage_key=stage_key,
    )
    if getattr(stage, upload_field):
        messages.error(request, 'A file is already uploaded. Delete it first to upload a new one.')
        return redirect('diagnostics')

    _assign_upload(stage, upload_field, uploaded_file)
    if upload_field == 'student_submission':
        stage.student_submitted_at = timezone.now()
    stage.save()
    messages.success(request, 'File uploaded successfully.')
    return redirect('diagnostics')


def diagnostics(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None:
        return _redirect_admin_without_student(request)

    platform_user = get_platform_user(request)
    blocked = _require_section_access(request, platform_user, profile, 'diagnostics')
    if blocked:
        return blocked

    if request.method == 'POST':
        return _handle_diagnostic_upload(request, profile, platform_user)

    stage_items = get_diagnostic_stage_items(profile)

    return render(request, 'diagnostics.html', {
        'stage_items': stage_items,
        'diagnostic_booking_url': DIAGNOSTIC_CALL_BOOKING_URL,
    })


def _validate_portfolio_element_post(request):
    title = request.POST.get('title', '').strip()
    country = request.POST.get('country', '').strip()
    detail = request.POST.get('detail', '').strip()
    comment = request.POST.get('comment', '').strip()
    errors = []

    if not title:
        errors.append('University name is required.')
    if not country:
        errors.append('Country is required.')
    if not detail:
        errors.append('Program name is required.')

    return errors, {
        'row_type': PortfolioDesignElement.RowType.UNIVERSITY,
        'title': title,
        'country': country,
        'detail': detail,
        'comment': comment,
    }


def _next_portfolio_element_sort_order(profile):
    last = profile.portfolio_design_elements.order_by('-sort_order').first()
    return (last.sort_order + 1) if last else 1


def _get_portfolio_element_for_profile(profile, element_id):
    return get_object_or_404(
        PortfolioDesignElement,
        pk=element_id,
        personal_profile=profile,
    )


def _portfolio_element_json_response(request, *, success=True, error=None, status=200):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        payload = {'success': success}
        if error:
            payload['error'] = error
        return JsonResponse(payload, status=status)
    if error:
        messages.error(request, error)
    return redirect('portfolio-design')


def _handle_portfolio_design_post(request, profile):
    action = request.POST.get('action', '').strip()

    if action == 'reorder_elements':
        ordered_ids = request.POST.getlist('element_ids')
        seen = set()
        for index, element_id in enumerate(ordered_ids, start=1):
            if not element_id or element_id in seen:
                continue
            seen.add(element_id)
            element = PortfolioDesignElement.objects.filter(
                pk=element_id,
                personal_profile=profile,
            ).first()
            if element:
                element.sort_order = index
                element.save(update_fields=['sort_order', 'updated_at'])
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.success(request, 'Portfolio rows reordered.')
        return redirect('portfolio-design')

    if action == 'update_status':
        element = _get_portfolio_element_for_profile(
            profile,
            request.POST.get('element_id', '').strip(),
        )
        status_color = request.POST.get('status_color', '').strip()
        if status_color not in PortfolioDesignElement.StatusColor.values:
            return _portfolio_element_json_response(
                request,
                success=False,
                error='Invalid status color.',
                status=400,
            )
        element.status_color = status_color
        element.save(update_fields=['status_color', 'updated_at'])
        return _portfolio_element_json_response(request)

    if action == 'update_comment':
        element = _get_portfolio_element_for_profile(
            profile,
            request.POST.get('element_id', '').strip(),
        )
        element.comment = request.POST.get('comment', '').strip()
        element.save(update_fields=['comment', 'updated_at'])
        return _portfolio_element_json_response(request)

    if action in {'add_element', 'edit_element'}:
        errors, cleaned = _validate_portfolio_element_post(request)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('portfolio-design')

        if action == 'add_element':
            PortfolioDesignElement.objects.create(
                personal_profile=profile,
                sort_order=_next_portfolio_element_sort_order(profile),
                **cleaned,
            )
            messages.success(request, 'Portfolio row added.')
            return redirect('portfolio-design')

        element = _get_portfolio_element_for_profile(
            profile,
            request.POST.get('element_id', '').strip(),
        )
        element.row_type = cleaned['row_type']
        element.title = cleaned['title']
        element.country = cleaned['country']
        element.detail = cleaned['detail']
        element.comment = cleaned.get('comment', element.comment)
        element.save()
        messages.success(request, 'Portfolio row updated.')
        return redirect('portfolio-design')

    if action == 'delete_element':
        element = _get_portfolio_element_for_profile(
            profile,
            request.POST.get('element_id', '').strip(),
        )
        element.delete()
        messages.success(request, 'Portfolio row deleted.')
        return redirect('portfolio-design')

    messages.error(request, 'Unknown action.')
    return redirect('portfolio-design')


def portfolio_design(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None:
        return _redirect_admin_without_student(request)

    platform_user = get_platform_user(request)
    is_admin = bool(platform_user and platform_user.is_admin)

    portfolio = get_portfolio_design_for_request(profile, platform_user)

    if portfolio is None:
        portfolio = ensure_portfolio_design(profile)

    blocked = _require_section_access(
        request, platform_user, profile, 'portfolio_design',
    )
    if blocked:
        return blocked

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        if action:
            return _handle_portfolio_design_post(request, profile)

        if not is_admin:
            messages.error(request, 'You do not have permission to change these settings.')
            return redirect('portfolio-design')

        portfolio.google_doc_url = request.POST.get('google_doc_url', '').strip()
        portfolio.save()
        messages.success(request, 'Portfolio Design document link saved.')
        return redirect_after_section_save(request, 'portfolio-design')

    portfolio_elements = profile.portfolio_design_elements.order_by('sort_order', 'id')

    return render(request, 'portfolio_design.html', {
        'portfolio': portfolio,
        'portfolio_elements': portfolio_elements,
    })


def _validate_university_choice_post(request):
    university_name = request.POST.get('university_name', '').strip()
    country = request.POST.get('country', '').strip()
    degree = request.POST.get('degree', '').strip()
    riskiness = request.POST.get('riskiness', '').strip()
    errors = []

    if not university_name:
        errors.append('University name is required.')
    if not country:
        errors.append('Country is required.')
    if not degree:
        errors.append('Degree is required.')
    if riskiness not in UniversityChoice.Riskiness.values:
        errors.append('Please select a valid riskiness level.')

    return errors, {
        'university_name': university_name,
        'country': country,
        'degree': degree,
        'riskiness': riskiness,
    }


def _next_university_choice_sort_order(profile):
    last = profile.university_choices.order_by('-sort_order').first()
    return (last.sort_order + 1) if last else 1


def _get_university_choice_for_profile(profile, choice_id):
    return get_object_or_404(
        UniversityChoice,
        pk=choice_id,
        personal_profile=profile,
    )


def _choices_are_locked(strategic, is_admin):
    return bool(strategic.choices_approved_at) and not is_admin


def _blocked_choice_mutation_response(request):
    message = (
        'This list has been signed and approved. '
        'If you want to edit this table, please send an email to contact@edunade.com.'
    )
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': message}, status=403)
    messages.warning(request, message)
    return redirect('strategic-application')


def _handle_strategic_application_post(request, profile, strategic, is_admin):
    action = request.POST.get('action', '').strip()

    if action == 'approve_choices':
        if is_admin:
            messages.error(request, 'Only students can sign and approve their university list.')
            return redirect('strategic-application')
        if strategic.choices_approved_at:
            messages.info(request, 'Your university list is already approved.')
            return redirect('strategic-application')
        if not profile.university_choices.exists():
            messages.error(request, 'Add at least one university choice before approving.')
            return redirect('strategic-application')
        strategic.choices_approved_at = timezone.now()
        strategic.save(update_fields=['choices_approved_at', 'updated_at'])
        messages.success(request, 'Your university list has been signed and approved.')
        return redirect('strategic-application')

    if _choices_are_locked(strategic, is_admin) and action in {
        'reorder_choices',
        'add_choice',
        'edit_choice',
        'delete_choice',
    }:
        return _blocked_choice_mutation_response(request)

    if action == 'reorder_choices':
        ordered_ids = request.POST.getlist('choice_ids')
        seen = set()
        for index, choice_id in enumerate(ordered_ids, start=1):
            if not choice_id or choice_id in seen:
                continue
            seen.add(choice_id)
            choice = UniversityChoice.objects.filter(
                pk=choice_id,
                personal_profile=profile,
            ).first()
            if choice:
                choice.sort_order = index
                choice.save(update_fields=['sort_order', 'updated_at'])
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.success(request, 'University choices reordered.')
        return redirect('strategic-application')

    if action in {'add_choice', 'edit_choice'}:
        errors, cleaned = _validate_university_choice_post(request)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('strategic-application')

        if action == 'add_choice':
            UniversityChoice.objects.create(
                personal_profile=profile,
                sort_order=_next_university_choice_sort_order(profile),
                **cleaned,
            )
            messages.success(request, 'University choice added.')
            return redirect('strategic-application')

        choice = _get_university_choice_for_profile(
            profile,
            request.POST.get('choice_id', '').strip(),
        )
        choice.university_name = cleaned['university_name']
        choice.country = cleaned['country']
        choice.degree = cleaned['degree']
        choice.riskiness = cleaned['riskiness']
        choice.save()
        messages.success(request, 'University choice updated.')
        return redirect('strategic-application')

    if action == 'delete_choice':
        choice = _get_university_choice_for_profile(
            profile,
            request.POST.get('choice_id', '').strip(),
        )
        choice.delete()
        messages.success(request, 'University choice deleted.')
        return redirect('strategic-application')

    messages.error(request, 'Unknown action.')
    return redirect('strategic-application')


def strategic_application(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None:
        return _redirect_admin_without_student(request)

    platform_user = get_platform_user(request)
    is_admin = bool(platform_user and platform_user.is_admin)

    strategic = get_strategic_application_for_request(profile, platform_user)
    if strategic is None:
        strategic = ensure_strategic_application(profile)

    blocked = _require_section_access(
        request, platform_user, profile, 'strategic_application',
    )
    if blocked:
        return blocked

    portfolio = get_portfolio_design_for_request(profile, platform_user, create=False)

    if request.method == 'POST':
        return _handle_strategic_application_post(request, profile, strategic, is_admin)

    university_choices = profile.university_choices.order_by('sort_order', 'id')
    choices_locked = _choices_are_locked(strategic, is_admin)

    return render(request, 'strategic_application.html', {
        'strategic': strategic,
        'portfolio': portfolio,
        'university_choices': university_choices,
        'riskiness_choices': UniversityChoice.Riskiness.choices,
        'choices_locked': choices_locked,
        'show_approve_button': not strategic.choices_approved_at,
    })


def _profile_narrative_sections(narrative):
    return (
        {
            'key': 'personal_statement',
            'title': 'Personal Statement',
            'field_name': 'personal_statement_google_doc_url',
            'url': narrative.personal_statement_google_doc_url,
        },
        {
            'key': 'cv',
            'title': 'CV',
            'field_name': 'cv_google_doc_url',
            'url': narrative.cv_google_doc_url,
        },
        {
            'key': 'application_essays',
            'title': 'Application Essays',
            'field_name': 'application_essays_google_doc_url',
            'url': narrative.application_essays_google_doc_url,
        },
    )


def profile_narrative(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None:
        return _redirect_admin_without_student(request)

    platform_user = get_platform_user(request)
    is_admin = bool(platform_user and platform_user.is_admin)

    narrative = get_profile_narrative_for_request(profile, platform_user)
    if narrative is None:
        narrative = ensure_profile_narrative(profile)

    blocked = _require_section_access(
        request, platform_user, profile, 'profile_narrative',
    )
    if blocked:
        return blocked

    if request.method == 'POST':
        if not is_admin:
            messages.error(request, 'You do not have permission to change these settings.')
            return redirect('profile-narrative')

        narrative.personal_statement_google_doc_url = request.POST.get(
            'personal_statement_google_doc_url', '',
        ).strip()
        narrative.cv_google_doc_url = request.POST.get('cv_google_doc_url', '').strip()
        narrative.application_essays_google_doc_url = request.POST.get(
            'application_essays_google_doc_url', '',
        ).strip()
        narrative.save()
        messages.success(request, 'Profile Narrative document links saved.')
        return redirect_after_section_save(request, 'profile-narrative')

    return render(request, 'profile_narrative.html', {
        'narrative': narrative,
        'narrative_sections': _profile_narrative_sections(narrative),
    })


def _validate_application_logistics_portal_post(request):
    errors = []
    portal_name = request.POST.get('portal_name', '').strip()
    portal_link = request.POST.get('portal_link', '').strip()
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()
    comments = request.POST.get('comments', '').strip()

    if not portal_name:
        errors.append('Portal name is required.')

    if portal_link and not portal_link.startswith(('http://', 'https://')):
        errors.append('Portal link must start with http:// or https://.')

    return errors, {
        'portal_name': portal_name,
        'portal_link': portal_link,
        'username': username,
        'password': password,
        'comments': comments,
    }


def _next_application_logistics_portal_sort_order(profile):
    last = profile.application_logistics_portals.order_by('-sort_order').first()
    if last is None:
        return 1
    return last.sort_order + 1


def _get_application_logistics_portal_for_profile(profile, portal_id):
    if not portal_id:
        return None
    return ApplicationLogisticsPortal.objects.filter(
        pk=portal_id,
        personal_profile=profile,
    ).first()


def _handle_application_logistics_post(request, profile):
    action = request.POST.get('action', '').strip()

    if action == 'reorder_portals':
        ordered_ids = request.POST.getlist('portal_ids')
        seen = set()
        for index, portal_id in enumerate(ordered_ids, start=1):
            if not portal_id or portal_id in seen:
                continue
            seen.add(portal_id)
            portal = ApplicationLogisticsPortal.objects.filter(
                pk=portal_id,
                personal_profile=profile,
            ).first()
            if portal:
                portal.sort_order = index
                portal.save(update_fields=['sort_order', 'updated_at'])
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.success(request, 'Portals reordered.')
        return redirect('application-logistics')

    if action in {'add_portal', 'edit_portal'}:
        errors, cleaned = _validate_application_logistics_portal_post(request)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('application-logistics')

        if action == 'add_portal':
            ApplicationLogisticsPortal.objects.create(
                personal_profile=profile,
                sort_order=_next_application_logistics_portal_sort_order(profile),
                **cleaned,
            )
            messages.success(request, 'Portal added.')
            return redirect('application-logistics')

        portal = _get_application_logistics_portal_for_profile(
            profile,
            request.POST.get('portal_id', '').strip(),
        )
        if portal is None:
            messages.error(request, 'Portal not found.')
            return redirect('application-logistics')

        portal.portal_name = cleaned['portal_name']
        portal.portal_link = cleaned['portal_link']
        portal.username = cleaned['username']
        portal.password = cleaned['password']
        portal.comments = cleaned['comments']
        portal.save()
        messages.success(request, 'Portal updated.')
        return redirect('application-logistics')

    if action == 'delete_portal':
        portal = _get_application_logistics_portal_for_profile(
            profile,
            request.POST.get('portal_id', '').strip(),
        )
        if portal is None:
            messages.error(request, 'Portal not found.')
            return redirect('application-logistics')
        portal.delete()
        messages.success(request, 'Portal deleted.')
        return redirect('application-logistics')

    messages.error(request, 'Unknown action.')
    return redirect('application-logistics')


def application_logistics(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None:
        return _redirect_admin_without_student(request)

    platform_user = get_platform_user(request)

    logistics = get_application_logistics_for_request(profile, platform_user)
    if logistics is None:
        logistics = ensure_application_logistics(profile)

    blocked = _require_section_access(
        request, platform_user, profile, 'application_logistics',
    )
    if blocked:
        return blocked

    if request.method == 'POST':
        return _handle_application_logistics_post(request, profile)

    portals = profile.application_logistics_portals.order_by('sort_order', 'id')

    return render(request, 'application_logistics.html', {
        'logistics': logistics,
        'portals': portals,
        'can_manage_portals': True,
    })


def _validate_interview_feedback_upload(uploaded_file):
    if not uploaded_file:
        return None
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        return 'Feedback file must be 10 MB or smaller.'
    extension = os.path.splitext(uploaded_file.name)[1].lower()
    if extension not in INTERVIEW_FEEDBACK_EXTENSIONS:
        return 'Only PDF and DOCX files are allowed for feedback.'
    return None


def _get_interview_prep_session(profile, slot_value):
    try:
        slot = int(slot_value)
    except (TypeError, ValueError):
        return None
    if slot not in INTERVIEW_PREP_SESSION_SLOTS:
        return None
    ensure_interview_prep_sessions(profile)
    return get_object_or_404(InterviewPrepSession, personal_profile=profile, slot=slot)


def _get_interview_session_items(profile, is_admin):
    sessions = ensure_interview_prep_sessions(profile)
    if is_admin:
        return sessions
    return [session for session in sessions if session.has_meeting_link]


def _handle_interview_preparation_post(request, profile, preparation, is_admin):
    action = request.POST.get('action', '').strip()

    if not is_admin:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('interview-preparation')

    session = _get_interview_prep_session(profile, request.POST.get('slot', ''))
    if session is None:
        messages.error(request, 'Unknown interview prep session.')
        return redirect('interview-preparation')

    if action == 'save_meeting_link':
        session.meeting_link = request.POST.get('meeting_link', '').strip()
        session.save()
        messages.success(request, f'Session {session.slot} meeting link saved.')
        return redirect('interview-preparation')

    if action == 'upload_feedback':
        upload_error = _validate_interview_feedback_upload(request.FILES.get('feedback_file'))
        if upload_error:
            messages.error(request, upload_error)
            return redirect('interview-preparation')
        if not request.FILES.get('feedback_file'):
            messages.error(request, 'Please choose a feedback file to upload.')
            return redirect('interview-preparation')
        if session.feedback_file:
            messages.error(
                request,
                f'Session {session.slot} already has feedback. Delete it first to upload a new file.',
            )
            return redirect('interview-preparation')
        session.feedback_file.save(
            request.FILES['feedback_file'].name,
            request.FILES['feedback_file'],
            save=True,
        )
        messages.success(request, f'Session {session.slot} feedback uploaded.')
        return redirect('interview-preparation')

    if action == 'delete_feedback':
        if not session.feedback_file:
            messages.info(request, 'No feedback file to delete.')
            return redirect('interview-preparation')
        clear_file_field(session, 'feedback_file')
        session.save()
        messages.success(request, f'Session {session.slot} feedback deleted.')
        return redirect('interview-preparation')

    messages.error(request, 'Unknown action.')
    return redirect('interview-preparation')


def interview_preparation(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None:
        return _redirect_admin_without_student(request)

    platform_user = get_platform_user(request)
    is_admin = bool(platform_user and platform_user.is_admin)

    preparation = get_interview_preparation_for_request(profile, platform_user)
    if preparation is None:
        preparation = ensure_interview_preparation(profile)

    blocked = _require_section_access(
        request, platform_user, profile, 'interview_preparation',
    )
    if blocked:
        return blocked

    if request.method == 'POST':
        return _handle_interview_preparation_post(request, profile, preparation, is_admin)

    session_items = _get_interview_session_items(profile, is_admin)

    return render(request, 'interview_preparation.html', {
        'preparation': preparation,
        'session_items': session_items,
    })


def _get_interview_feedback_session_for_request(request, session_id):
    if admin_must_select_student(request):
        return None

    profile = get_profile_for_request(request, create=False)
    if profile is None:
        return None

    platform_user = get_platform_user(request)
    is_admin = bool(platform_user and platform_user.is_admin)

    if not student_can_access_section(
        request, platform_user, profile, 'interview_preparation',
    ):
        return None

    try:
        session = InterviewPrepSession.objects.get(pk=session_id, personal_profile=profile)
    except InterviewPrepSession.DoesNotExist:
        return None

    if not is_admin and not session.has_meeting_link:
        return None

    return session


def preview_interview_feedback(request, session_id):
    session = _get_interview_feedback_session_for_request(request, session_id)
    if session is None or not session.feedback_file or not session.feedback_is_pdf:
        raise Http404

    filename = os.path.basename(session.feedback_file.name)
    response = FileResponse(
        session.feedback_file.open('rb'),
        content_type='application/pdf',
        as_attachment=False,
    )
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def _validate_offer_post(request):
    university_name = request.POST.get('university_name', '').strip()
    degree_name = request.POST.get('degree_name', '').strip()
    offer_requirements = request.POST.get('offer_requirements', '').strip()
    errors = []

    if not university_name:
        errors.append('University name is required.')
    if not degree_name:
        errors.append('Degree name is required.')
    if not offer_requirements:
        errors.append('Offer requirements are required.')

    return errors, {
        'university_name': university_name,
        'degree_name': degree_name,
        'offer_requirements': offer_requirements,
    }


def _get_offer_for_profile(profile, offer_id):
    return get_object_or_404(
        Offer,
        pk=offer_id,
        personal_profile=profile,
    )


def _save_offer_attachment(offer, uploaded_file):
    upload_error = _validate_upload(uploaded_file)
    if upload_error:
        return upload_error
    clear_file_field(offer, 'attachment_file')
    offer.attachment_file.save(uploaded_file.name, uploaded_file, save=False)
    offer.save(update_fields=['attachment_file', 'updated_at'])
    return None


def _handle_offers_post(request, profile, is_admin):
    action = request.POST.get('action', '').strip()

    if action in {'add_offer', 'edit_offer', 'delete_offer', 'delete_offer_attachment', 'upload_offer_attachment'}:
        if not is_admin:
            messages.error(request, 'You do not have permission to perform this action.')
            return redirect('offers')

    if action in {'add_offer', 'edit_offer'}:
        errors, cleaned = _validate_offer_post(request)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('offers')

        uploaded_file = request.FILES.get('attachment_file')
        if uploaded_file:
            upload_error = _validate_upload(uploaded_file)
            if upload_error:
                messages.error(request, upload_error)
                return redirect('offers')

        if action == 'add_offer':
            offer = Offer.objects.create(
                personal_profile=profile,
                **cleaned,
            )
            if uploaded_file:
                offer.attachment_file.save(uploaded_file.name, uploaded_file, save=True)
            messages.success(request, 'Offer added.')
            return redirect('offers')

        offer = _get_offer_for_profile(
            profile,
            request.POST.get('offer_id', '').strip(),
        )
        offer.university_name = cleaned['university_name']
        offer.degree_name = cleaned['degree_name']
        offer.offer_requirements = cleaned['offer_requirements']
        if uploaded_file:
            clear_file_field(offer, 'attachment_file')
            offer.attachment_file.save(uploaded_file.name, uploaded_file, save=False)
        offer.save()
        messages.success(request, 'Offer updated.')
        return redirect('offers')

    if action == 'upload_offer_attachment':
        offer = _get_offer_for_profile(
            profile,
            request.POST.get('offer_id', '').strip(),
        )
        uploaded_file = request.FILES.get('attachment_file')
        if not uploaded_file:
            messages.error(request, 'Please choose a file to upload.')
            return redirect('offers')
        if offer.attachment_file:
            messages.error(request, 'Delete the current document before uploading a new one.')
            return redirect('offers')
        upload_error = _save_offer_attachment(offer, uploaded_file)
        if upload_error:
            messages.error(request, upload_error)
            return redirect('offers')
        messages.success(request, 'Offer document uploaded.')
        return redirect('offers')

    if action == 'delete_offer_attachment':
        offer = _get_offer_for_profile(
            profile,
            request.POST.get('offer_id', '').strip(),
        )
        if not offer.attachment_file:
            messages.error(request, 'This offer has no document to delete.')
            return redirect('offers')
        clear_file_field(offer, 'attachment_file')
        offer.save(update_fields=['attachment_file', 'updated_at'])
        messages.success(request, 'Offer document deleted.')
        return redirect('offers')

    if action == 'delete_offer':
        offer = _get_offer_for_profile(
            profile,
            request.POST.get('offer_id', '').strip(),
        )
        clear_file_field(offer, 'attachment_file')
        offer.delete()
        messages.success(request, 'Offer deleted.')
        return redirect('offers')

    messages.error(request, 'Unknown action.')
    return redirect('offers')


def offers(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None:
        return _redirect_admin_without_student(request)

    platform_user = get_platform_user(request)
    is_admin = bool(platform_user and platform_user.is_admin)

    blocked = _require_section_access(request, platform_user, profile, 'offers')
    if blocked:
        return blocked

    if request.method == 'POST':
        return _handle_offers_post(request, profile, is_admin)

    offer_entries = profile.offers.all()

    return render(request, 'offers.html', {
        'offer_entries': offer_entries,
    })


def _validate_result_document_post(request):
    document_type = request.POST.get('document_type', '').strip()
    uploaded_file = request.FILES.get('document_file')
    errors = []

    if document_type not in RESULT_DOCUMENT_TYPE_VALUES:
        errors.append('Please select a document type.')
    if not uploaded_file:
        errors.append('Please choose a file to upload.')

    return errors, document_type, uploaded_file


def _get_result_document_for_profile(profile, document_id):
    return get_object_or_404(
        ResultDocument,
        pk=document_id,
        personal_profile=profile,
    )


def _handle_results_post(request, profile, is_admin):
    action = request.POST.get('action', '').strip()

    if action in {'add_document', 'delete_document'} and not is_admin:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('results')

    if action == 'add_document':
        errors, document_type, uploaded_file = _validate_result_document_post(request)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('results')

        upload_error = _validate_upload(uploaded_file)
        if upload_error:
            messages.error(request, upload_error)
            return redirect('results')

        document = ResultDocument(
            personal_profile=profile,
            document_type=document_type,
        )
        document.document_file.save(uploaded_file.name, uploaded_file, save=True)
        messages.success(request, 'Document added.')
        return redirect('results')

    if action == 'delete_document':
        document = _get_result_document_for_profile(
            profile,
            request.POST.get('document_id', '').strip(),
        )
        clear_file_field(document, 'document_file')
        document.delete()
        messages.success(request, 'Document deleted.')
        return redirect('results')

    messages.error(request, 'Unknown action.')
    return redirect('results')


def results(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None:
        return _redirect_admin_without_student(request)

    platform_user = get_platform_user(request)
    is_admin = bool(platform_user and platform_user.is_admin)

    blocked = _require_section_access(request, platform_user, profile, 'results')
    if blocked:
        return blocked

    if request.method == 'POST':
        return _handle_results_post(request, profile, is_admin)

    document_entries = profile.result_documents.all()

    return render(request, 'results.html', {
        'document_entries': document_entries,
        'result_document_type_choices': RESULT_DOCUMENT_TYPE_CHOICES,
    })


def faq(request):
    return render(request, 'consulting_faq.html')


@login_required
def admin_student_access(request):
    platform_user = get_platform_user(request)
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only admins can manage student access.')
        return redirect('home')

    students = get_student_platform_users()
    selected_student_id = request.GET.get('student') or request.POST.get('student_id')
    if not selected_student_id and students:
        selected_student_id = str(students[0].id)

    selected_student = None
    section_rows = []
    if selected_student_id:
        selected_student = get_object_or_404(
            PlatformUser,
            pk=selected_student_id,
            role=PlatformUser.Role.STUDENT,
        )
        if request.method == 'POST':
            signature_reset = save_section_access_from_post(selected_student, request)
            student_name = (
                f'{selected_student.first_name} {selected_student.last_name}'
            )
            if signature_reset:
                messages.success(
                    request,
                    f'Strategic Application signature reset for {student_name}. '
                    'The student can edit and sign again.',
                )
            else:
                messages.success(
                    request,
                    f'Access settings saved for {student_name}.',
                )
            return redirect(f'{reverse("admin-student-access")}?student={selected_student.id}')
        section_rows = section_access_rows_for_student(selected_student)

    return render(request, 'admin_student_access.html', {
        'students': students,
        'selected_student': selected_student,
        'section_rows': section_rows,
    })


@ensure_csrf_cookie
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    next_url = request.GET.get('next', '').strip()

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('passwd', '')
        next_url = request.POST.get('next', next_url).strip()

        user = authenticate(request, username=email, password=password)
        if user is None:
            try:
                matched = User.objects.get(email__iexact=email)
                user = authenticate(request, username=matched.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None and hasattr(user, 'platform_account'):
            auth_login(request, user)
            platform_user = user.platform_account
            if platform_user.is_student:
                claim_guest_profile_for_student(request, platform_user)
                clear_admin_viewing_student(request)
            else:
                clear_profile_session_key(request)
            if request.POST.get('remember-me') == 'on':
                request.session.set_expiry(None)
            else:
                request.session.set_expiry(0)
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
            ):
                return redirect(next_url)
            return redirect('home')

        messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html', {'next': next_url})


@ensure_csrf_cookie
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        errors, form_data, cleaned = _validate_register_form(request)
        if errors:
            ajax_response = _register_response(request, success=False, errors=errors)
            if ajax_response:
                return ajax_response
            return render(
                request,
                'register.html',
                {**_register_form_context(form_data), 'errors': errors},
            )

        user, platform_user = create_registered_user(**cleaned)
        auth_login(request, user)
        if platform_user.is_student:
            claim_guest_profile_for_student(request, platform_user)
            clear_admin_viewing_student(request)
        else:
            clear_profile_session_key(request)
        request.session.set_expiry(0)

        redirect_url = reverse('home')
        ajax_response = _register_response(
            request,
            success=True,
            redirect_url=redirect_url,
        )
        if ajax_response:
            return ajax_response
        messages.success(request, 'Welcome! Your account has been created.')
        return redirect('home')

    return render(request, 'register.html', _register_form_context())


@login_required
def upload_profile_photo(request):
    if admin_must_select_student(request):
        return JsonResponse(
            {'success': False, 'errors': ['Select a student profile first.']},
            status=400,
        )

    profile = _get_or_create_profile(request)
    if profile is None:
        return JsonResponse(
            {'success': False, 'errors': ['Profile not found.']},
            status=404,
        )

    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'errors': ['Invalid request.']},
            status=405,
        )

    uploaded_photo = request.FILES.get('profile_photo')
    if not uploaded_photo:
        return JsonResponse(
            {'success': False, 'errors': ['No photo provided.']},
            status=400,
        )

    photo_error = replace_profile_photo(profile, uploaded_photo)
    if photo_error:
        return JsonResponse({'success': False, 'errors': [photo_error]})

    profile.save()
    profile.refresh_from_db()
    return JsonResponse({
        'success': True,
        'photo_url': profile.profile_photo.url,
        'download_url': reverse('download-profile-photo'),
    })


@login_required
def download_profile_photo(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None or not profile.profile_photo:
        raise Http404

    filename = os.path.basename(profile.profile_photo.name)
    return FileResponse(
        profile.profile_photo.open('rb'),
        as_attachment=True,
        filename=filename,
    )


@login_required
def admin_create_student(request):
    platform_user = get_platform_user(request)
    if not platform_user or not platform_user.is_admin:
        return JsonResponse(
            {'success': False, 'errors': ['Only admins can create students.']},
            status=403,
        )

    if request.method != 'POST':
        return redirect('home')

    errors, cleaned = _validate_admin_student_form(request)
    if errors:
        return JsonResponse({'success': False, 'errors': errors})

    _, student = create_registered_user(**cleaned)
    set_admin_viewing_student(request, student)
    name = f'{student.first_name} {student.last_name}'.strip() or student.email
    messages.success(request, f'Student {name} created successfully.')
    return JsonResponse({
        'success': True,
        'redirect_url': reverse('personal-information'),
    })


@login_required
def admin_delete_student(request, student_id):
    platform_user = get_platform_user(request)
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only admins can delete students.')
        return redirect('home')

    if request.method != 'POST':
        return redirect('home')

    student = get_object_or_404(PlatformUser, pk=student_id, role=PlatformUser.Role.STUDENT)
    name = f'{student.first_name} {student.last_name}'.strip() or student.email

    if get_admin_viewing_student_id(request) == student.id:
        clear_admin_viewing_student(request)
        clear_deadline_filter_student(request)

    auth_user = student.user
    auth_user.delete()

    messages.success(request, f'Student {name} deleted.')
    return redirect('home')


@login_required
def select_student_profile(request, student_id):
    platform_user = get_platform_user(request)
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only admins can switch student profiles.')
        return redirect('home')

    student = get_object_or_404(PlatformUser, pk=student_id, role=PlatformUser.Role.STUDENT)
    set_admin_viewing_student(request, student)
    next_url = request.GET.get('next', '').strip()
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
    ):
        return redirect(next_url)
    return redirect('personal-information')


@login_required
def clear_student_selection(request):
    platform_user = get_platform_user(request)
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only admins can clear student selection.')
        return redirect('home')

    clear_admin_viewing_student(request)
    clear_deadline_filter_student(request)
    messages.info(request, 'Student selection cleared.')
    return redirect('home')


@login_required
def preview_student_profile(request, student_id):
    if is_impersonating(request):
        messages.error(request, 'You are already viewing the platform as a student.')
        return redirect('home')

    platform_user = get_platform_user(request)
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only admins can preview student profiles.')
        return redirect('home')

    student = get_object_or_404(PlatformUser, pk=student_id, role=PlatformUser.Role.STUDENT)
    set_impersonator_user_id(request, request.user.pk)
    clear_admin_viewing_student(request)
    auth_login(request, student.user)
    return redirect('home')


@login_required
def exit_student_preview(request):
    if not is_impersonating(request):
        return redirect('home')

    admin_user = get_impersonator_user(request)
    clear_impersonator_user_id(request)
    clear_admin_viewing_student(request)
    if admin_user:
        auth_login(request, admin_user)
        messages.info(request, 'Returned to your admin account.')
    else:
        auth_logout(request)
        messages.info(request, 'Admin session expired. Please log in again.')
        return redirect('login')
    return redirect('home')


def logout_view(request):
    clear_impersonator_user_id(request)
    clear_admin_viewing_student(request)
    auth_logout(request)
    return redirect('login')
