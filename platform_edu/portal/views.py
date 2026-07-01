import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib import messages
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
    GRADUATION_YEARS,
    IB_SUBJECT_CHOICES,
    INTERVIEW_FEEDBACK_EXTENSIONS,
    INTERVIEW_PREP_SESSION_SLOTS,
    MAX_UPLOAD_SIZE,
)
from .reference_contacts_utils import (
    MAX_REFERENCE_CONTACTS,
    reference_contacts_for_form,
    save_reference_contacts,
)
from .budget_utils import budget_exchange_rates_response, save_budget_fields
from .course_wishes_utils import ordered_countries_for_form, save_course_wishes
from .activity_entries_utils import (
    activity_entries_for_form,
    save_activity_entries,
)
from .subjects_utils import subjects_for_form, subjects_from_post
from .models import (
    AcademicProfile,
    Deadline,
    DiagnosticStage,
    InterviewPrepSession,
    Offer,
    PlatformUser,
    StudentTodo,
    UniversityChoice,
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
    admin_must_select_student,
    claim_guest_profile_for_student,
    clear_admin_viewing_student,
    clear_impersonator_user_id,
    clear_profile_session_key,
    ensure_interview_preparation,
    ensure_interview_prep_sessions,
    ensure_offers_access,
    ensure_portfolio_design,
    ensure_profile_narrative,
    ensure_strategic_application,
    get_admin_viewing_student,
    get_impersonator_user,
    get_interview_preparation_for_request,
    get_offers_access_for_request,
    get_platform_user,
    get_profile_for_request,
    get_portfolio_design_for_request,
    get_profile_narrative_for_request,
    get_strategic_application_for_request,
    get_student_platform_users,
    interview_preparation_is_unlocked_for_platform_user,
    is_impersonating,
    offers_is_unlocked_for_platform_user,
    portfolio_design_is_unlocked_for_platform_user,
    profile_narrative_is_unlocked_for_platform_user,
    set_admin_viewing_student,
    set_impersonator_user_id,
    strategic_application_is_unlocked_for_platform_user,
    sync_profile_edunade_email,
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
        'student_default_password': 'Edunade2020!',
    })


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

    sync_profile_edunade_email(profile)

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
        profile.personal_email = request.POST.get('personal_email', '').strip()
        if profile.platform_user_id:
            profile.edunade_email = profile.platform_user.email
        else:
            profile.edunade_email = request.POST.get('edunade_email', '').strip()
        profile.phone_number = request.POST.get('phone_number', '').strip()
        profile.nationality = request.POST.get('nationality', '').strip()
        profile.passport_number = request.POST.get('passport_number', '').strip()
        profile.school_name = request.POST.get('school_name', '').strip()
        profile.school_address = request.POST.get('school_address', '').strip()
        profile.curriculum = request.POST.get('curriculum', '').strip()
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

    selected_subjects, custom_subjects = subjects_for_form(profile.subjects)

    return render(request, 'personal_information.html', {
        'info': profile,
        'school_name': profile.school_name,
        'curriculum': profile.curriculum,
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

    reference_contacts, reference_contacts_visible = reference_contacts_for_form(academic)
    activity_entries = activity_entries_for_form(academic)

    return render(request, 'academic_profile.html', {
        'profile': profile,
        'academic': academic,
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
    if not (platform_user and platform_user.is_admin) and not profile.is_complete():
        messages.warning(
            request,
            'Please complete all fields in Personal Information before accessing Diagnostics.',
        )
        return redirect('personal-information')

    if request.method == 'POST':
        return _handle_diagnostic_upload(request, profile, platform_user)

    stage_items = get_diagnostic_stage_items(profile)
    homework_stage = next(
        (item['stage'] for item in stage_items if item['stage'].stage_key == 'homework'),
        None,
    )

    return render(request, 'diagnostics.html', {
        'stage_items': stage_items,
        'homework_complete': bool(homework_stage and homework_stage.has_student_submission),
    })


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

    if not is_admin and not portfolio_design_is_unlocked_for_platform_user(platform_user):
        messages.warning(
            request,
            'Portfolio Design is not available yet. Your consultant will unlock it when ready.',
        )
        return redirect('home')

    if request.method == 'POST':
        if not is_admin:
            messages.error(request, 'You do not have permission to change these settings.')
            return redirect('portfolio-design')

        portfolio.is_unlocked = request.POST.get('is_unlocked') == 'on'
        portfolio.google_doc_url = request.POST.get('google_doc_url', '').strip()
        portfolio.save()
        messages.success(request, 'Portfolio Design settings saved.')
        return redirect('portfolio-design')

    return render(request, 'portfolio_design.html', {
        'portfolio': portfolio,
    })


def _validate_university_choice_post(request):
    university_name = request.POST.get('university_name', '').strip()
    degree = request.POST.get('degree', '').strip()
    riskiness = request.POST.get('riskiness', '').strip()
    errors = []

    if not university_name:
        errors.append('University name is required.')
    if not degree:
        errors.append('Degree is required.')
    if riskiness not in UniversityChoice.Riskiness.values:
        errors.append('Please select a valid riskiness level.')

    return errors, {
        'university_name': university_name,
        'degree': degree,
        'riskiness': riskiness,
    }


def _get_university_choice_for_profile(profile, choice_id):
    return get_object_or_404(
        UniversityChoice,
        pk=choice_id,
        personal_profile=profile,
    )


def _handle_strategic_application_post(request, profile, strategic, is_admin):
    action = request.POST.get('action', '').strip()

    if action == 'admin_settings':
        if not is_admin:
            messages.error(request, 'You do not have permission to change these settings.')
            return redirect('strategic-application')
        strategic.is_unlocked = request.POST.get('is_unlocked') == 'on'
        strategic.save()
        messages.success(request, 'Strategic Application settings saved.')
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
                **cleaned,
            )
            messages.success(request, 'University choice added.')
            return redirect('strategic-application')

        choice = _get_university_choice_for_profile(
            profile,
            request.POST.get('choice_id', '').strip(),
        )
        choice.university_name = cleaned['university_name']
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

    if not is_admin and not strategic_application_is_unlocked_for_platform_user(platform_user):
        messages.warning(
            request,
            'Strategic Application is not available yet. Your consultant will unlock it when ready.',
        )
        return redirect('home')

    portfolio = get_portfolio_design_for_request(profile, platform_user, create=False)

    if request.method == 'POST':
        return _handle_strategic_application_post(request, profile, strategic, is_admin)

    university_choices = profile.university_choices.all()

    return render(request, 'strategic_application.html', {
        'strategic': strategic,
        'portfolio': portfolio,
        'university_choices': university_choices,
        'riskiness_choices': UniversityChoice.Riskiness.choices,
    })


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

    if not is_admin and not profile_narrative_is_unlocked_for_platform_user(platform_user):
        messages.warning(
            request,
            'Profile Narrative is not available yet. Your consultant will unlock it when ready.',
        )
        return redirect('home')

    if request.method == 'POST':
        if not is_admin:
            messages.error(request, 'You do not have permission to change these settings.')
            return redirect('profile-narrative')

        narrative.is_unlocked = request.POST.get('is_unlocked') == 'on'
        narrative.save()
        messages.success(request, 'Profile Narrative settings saved.')
        return redirect('profile-narrative')

    return render(request, 'profile_narrative.html', {
        'narrative': narrative,
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

    if action == 'admin_settings':
        if not is_admin:
            messages.error(request, 'You do not have permission to change these settings.')
            return redirect('interview-preparation')
        preparation.is_unlocked = request.POST.get('is_unlocked') == 'on'
        preparation.save()
        messages.success(request, 'Interview Preparation settings saved.')
        return redirect('interview-preparation')

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

    if not is_admin and not interview_preparation_is_unlocked_for_platform_user(platform_user):
        messages.warning(
            request,
            'Interview Preparation is not available yet. Your consultant will unlock it when ready.',
        )
        return redirect('home')

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

    if not is_admin and not interview_preparation_is_unlocked_for_platform_user(platform_user):
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


def _handle_offers_post(request, profile, offers_access, is_admin):
    action = request.POST.get('action', '').strip()

    if action == 'admin_settings':
        if not is_admin:
            messages.error(request, 'You do not have permission to change these settings.')
            return redirect('offers')
        offers_access.is_unlocked = request.POST.get('is_unlocked') == 'on'
        offers_access.save()
        messages.success(request, 'Offers settings saved.')
        return redirect('offers')

    if action in {'add_offer', 'edit_offer'}:
        errors, cleaned = _validate_offer_post(request)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('offers')

        if action == 'add_offer':
            Offer.objects.create(
                personal_profile=profile,
                **cleaned,
            )
            messages.success(request, 'Offer added.')
            return redirect('offers')

        offer = _get_offer_for_profile(
            profile,
            request.POST.get('offer_id', '').strip(),
        )
        offer.university_name = cleaned['university_name']
        offer.degree_name = cleaned['degree_name']
        offer.offer_requirements = cleaned['offer_requirements']
        offer.save()
        messages.success(request, 'Offer updated.')
        return redirect('offers')

    if action == 'delete_offer':
        offer = _get_offer_for_profile(
            profile,
            request.POST.get('offer_id', '').strip(),
        )
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

    offers_access = get_offers_access_for_request(profile, platform_user)
    if offers_access is None:
        offers_access = ensure_offers_access(profile)

    if not is_admin and not offers_is_unlocked_for_platform_user(platform_user):
        messages.warning(
            request,
            'Offers is not available yet. Your consultant will unlock it when ready.',
        )
        return redirect('home')

    if request.method == 'POST':
        return _handle_offers_post(request, profile, offers_access, is_admin)

    offer_entries = profile.offers.all()

    return render(request, 'offers.html', {
        'offers_access': offers_access,
        'offer_entries': offer_entries,
    })


def faq(request):
    return render(request, 'consulting_faq.html')


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
