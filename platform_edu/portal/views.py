import os
from datetime import datetime

from django.contrib import messages
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
    COUNTRY_CHOICES,
    DIAGNOSTIC_STAGE_KEYS,
    GRADUATION_YEARS,
    IB_SUBJECT_CHOICES,
    MAX_UPLOAD_SIZE,
)
from .diagnostics_access import get_diagnostic_stage_items
from .models import AcademicProfile, Deadline, DiagnosticStage, PlatformUser
from .upload_utils import (
    ACADEMIC_UPLOAD_FIELDS,
    assign_file_field,
    can_delete_academic_upload,
    can_delete_diagnostic_upload,
    clear_file_field,
)
from .register_utils import (
    _register_form_context,
    _register_response,
    _validate_register_form,
    create_registered_user,
)
from .profile_access import (
    admin_must_select_student,
    claim_guest_profile_for_student,
    clear_admin_viewing_student,
    clear_deadline_filter_student,
    clear_profile_session_key,
    get_deadline_filter_student,
    get_platform_user,
    get_profile_for_request,
    get_student_platform_users,
    set_admin_viewing_student,
    set_deadline_filter_student,
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


def _parse_deadline_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed)
    return parsed


def _validate_deadline_form(request):
    name = request.POST.get('name', '').strip()
    due_at_raw = request.POST.get('due_at', '').strip()
    urgency = request.POST.get('urgency', '').strip()
    student_id = request.POST.get('student_id', '').strip()

    errors = []
    if not name:
        errors.append('Deadline name is required.')
    due_at = _parse_deadline_datetime(due_at_raw)
    if not due_at:
        errors.append('A valid date and time is required.')
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

    return errors, name, due_at, urgency, student


def _handle_add_deadline(request, platform_user):
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only consultants can add deadlines.')
        return redirect('home')

    errors, name, due_at, urgency, student = _validate_deadline_form(request)
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('home')

    Deadline.objects.create(
        name=name,
        due_at=due_at,
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

    errors, name, due_at, urgency, student = _validate_deadline_form(request)
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('home')

    deadline.name = name
    deadline.due_at = due_at
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


def _handle_filter_deadline_student(request, platform_user):
    if not platform_user or not platform_user.is_admin:
        messages.error(request, 'Only consultants can filter deadlines by student.')
        return redirect('home')

    student_id = request.POST.get('student_id', '').strip()
    if not student_id or student_id == 'all':
        clear_deadline_filter_student(request)
        messages.info(request, 'Showing deadlines for all students.')
        return redirect('home')

    student = PlatformUser.objects.filter(
        pk=student_id,
        role=PlatformUser.Role.STUDENT,
    ).first()
    if not student:
        messages.error(request, 'Selected student was not found.')
        return redirect('home')

    set_deadline_filter_student(request, student.id)
    name = f'{student.first_name} {student.last_name}'.strip() or student.email
    messages.info(request, f'Showing deadlines for {name}.')
    return redirect('home')


def _get_deadlines_for_user(platform_user, request=None):
    queryset = Deadline.objects.select_related('student').order_by('due_at')
    if platform_user and platform_user.is_student:
        queryset = queryset.filter(student=platform_user)
    elif platform_user and platform_user.is_admin and request is not None:
        filter_student = get_deadline_filter_student(request)
        if filter_student:
            queryset = queryset.filter(student=filter_student)
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
        if action == 'filter_deadline_student':
            return _handle_filter_deadline_student(request, platform_user)

    deadlines = _get_deadlines_for_user(platform_user, request)
    deadline_filter_student = (
        get_deadline_filter_student(request)
        if platform_user and platform_user.is_admin
        else None
    )
    return render(request, 'logistics_dashboard.html', {
        'deadlines_all': deadlines,
        'deadlines_urgent': deadlines.filter(urgency=Deadline.Urgency.URGENT),
        'deadlines_standard': deadlines.filter(urgency=Deadline.Urgency.STANDARD),
        'deadlines_relaxed': deadlines.filter(urgency=Deadline.Urgency.RELAXED),
        'deadline_total_count': deadlines.count(),
        'can_manage_deadlines': bool(platform_user and platform_user.is_admin),
        'deadline_students': get_student_platform_users() if platform_user and platform_user.is_admin else [],
        'deadline_filter_student': deadline_filter_student,
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
        profile.curriculum = request.POST.get('curriculum', '').strip()
        profile.graduation_year = request.POST.get('graduation_year', '').strip()
        profile.subjects = ', '.join(request.POST.getlist('subjects'))
        profile.save()
        messages.success(request, 'Personal information saved successfully.')

    selected_subjects = [s.strip() for s in profile.subjects.split(',') if s.strip()]

    return render(request, 'personal_information.html', {
        'info': profile,
        'school_name': profile.school_name,
        'curriculum': profile.curriculum,
        'selected_subjects': selected_subjects,
        'ib_subjects': IB_SUBJECT_CHOICES,
        'nationalities': _NATIONALITY_CHOICES,
        'graduation_years': GRADUATION_YEARS,
    })


def academic_profile(request):
    if admin_must_select_student(request):
        return _redirect_admin_without_student(request)

    profile = _get_or_create_profile(request)
    if profile is None:
        return _redirect_admin_without_student(request)

    academic = _get_or_create_academic(profile)
    platform_user = get_platform_user(request)

    if request.method == 'POST':
        if request.POST.get('action') == 'delete_file':
            return _handle_academic_file_delete(request, profile, academic)

        upload_labels = {
            'transcripts': 'Transcripts',
            'cv_upload': 'CV',
            'personal_statement_upload': 'Personal Statement',
        }
        upload_errors = []
        for field_name, label in upload_labels.items():
            error = _validate_upload(request.FILES.get(field_name))
            if error:
                upload_errors.append(f'{label}: {error}')
            elif request.FILES.get(field_name) and getattr(academic, field_name):
                upload_errors.append(
                    f'{label} already uploaded. Delete it first to upload a new file.'
                )

        if upload_errors:
            for error in upload_errors:
                messages.error(request, error)
        else:
            profile.school_name = request.POST.get('school_name', '').strip()
            profile.curriculum = request.POST.get('curriculum', '').strip()
            profile.graduation_year = request.POST.get('graduation_year', '').strip()
            profile.subjects = ', '.join(request.POST.getlist('subjects'))
            profile.save()

            academic.predicted_grades = request.POST.get('predicted_grades', '').strip()
            academic.standardized_tests = request.POST.get('standardized_tests', '').strip()
            academic.extracurricular_activities = request.POST.get(
                'extracurricular_activities', ''
            ).strip()
            academic.awards_competitions = request.POST.get('awards_competitions', '').strip()
            academic.intended_course_interests = request.POST.get(
                'intended_course_interests', ''
            ).strip()
            academic.country_preferences = ', '.join(request.POST.getlist('country_preferences'))
            academic.budget_expectations = request.POST.get('budget_expectations', '').strip()
            academic.parent_input = request.POST.get('parent_input', '').strip()
            academic.career_goals = request.POST.get('career_goals', '').strip()

            _assign_upload(academic, 'transcripts', request.FILES.get('transcripts'))
            _assign_upload(academic, 'cv_upload', request.FILES.get('cv_upload'))
            _assign_upload(
                academic,
                'personal_statement_upload',
                request.FILES.get('personal_statement_upload'),
            )
            academic.save()
            messages.success(request, 'Academic profile saved successfully.')

    selected_subjects = [s.strip() for s in profile.subjects.split(',') if s.strip()]
    selected_countries = [
        c.strip() for c in academic.country_preferences.split(',') if c.strip()
    ]

    return render(request, 'academic_profile.html', {
        'profile': profile,
        'academic': academic,
        'selected_subjects': selected_subjects,
        'selected_countries': selected_countries,
        'ib_subjects': IB_SUBJECT_CHOICES,
        'graduation_years': GRADUATION_YEARS,
        'country_choices': COUNTRY_CHOICES,
        'budget_choices': BUDGET_CHOICES,
        'can_delete_uploads': can_delete_academic_upload(platform_user),
    })


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


def logout_view(request):
    clear_admin_viewing_student(request)
    auth_logout(request)
    return redirect('login')
