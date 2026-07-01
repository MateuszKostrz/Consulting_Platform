import json
import re
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse

from .constants import PHONE_COUNTRY_CODES
from .models import PlatformUser
from .profile_access import ensure_student_personal_profile
from .upload_utils import replace_profile_photo, validate_profile_photo

VALID_PHONE_COUNTRY_CODES = {code for code, _ in PHONE_COUNTRY_CODES}


def _register_form_context(form_data=None):
    form_data = form_data or {}
    return {
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
        'recaptcha_enabled': settings.RECAPTCHA_ENABLED,
        'phone_country_codes': PHONE_COUNTRY_CODES,
        **form_data,
    }


def _build_phone_number(country_code, local_number):
    digits = re.sub(r'\D', '', local_number)
    if not country_code or not digits:
        return ''
    return f'{country_code} {digits}'


def _register_response(request, *, success, errors=None, redirect_url=''):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'errors': errors or [],
            'redirect_url': redirect_url,
        })
    return None


def _verify_recaptcha(token, remote_ip=None):
    if not settings.RECAPTCHA_ENABLED:
        return True, None

    if not token:
        return False, 'reCAPTCHA verification failed. Please try again.'

    payload = urllib.parse.urlencode({
        'secret': settings.RECAPTCHA_SECRET_KEY,
        'response': token,
        'remoteip': remote_ip or '',
    }).encode()
    request = urllib.request.Request(
        settings.RECAPTCHA_VERIFY_URL,
        data=payload,
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode())
    except Exception:
        return False, 'reCAPTCHA verification failed. Please try again.'

    if not result.get('success'):
        return False, 'reCAPTCHA verification failed. Please try again.'
    return True, None


def _validate_register_form(request):
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip().lower()
    user_type = request.POST.get('user_type', '').strip()
    application_type = request.POST.get('application_type', '').strip()
    password = request.POST.get('password', '')
    confirm_password = request.POST.get('confirm_password', '')
    privacy_policy = request.POST.get('privacy_policy')
    data_processing = request.POST.get('data_processing')
    recaptcha_token = request.POST.get('recaptcha_token', '').strip()
    phone_country_code = request.POST.get('phone_country_code', '').strip()
    phone_local = request.POST.get('phone_local', '').strip()
    parent_email = request.POST.get('parent_email', '').strip().lower()

    form_data = {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'user_type': user_type,
        'application_type': application_type,
        'phone_country_code': phone_country_code,
        'phone_local': phone_local,
        'parent_email': parent_email,
        'privacy_policy_checked': bool(privacy_policy),
        'data_processing_checked': bool(data_processing),
    }

    errors = []
    if not first_name:
        errors.append('First name is required.')
    if not last_name:
        errors.append('Last name is required.')
    if not email:
        errors.append('Email is required.')
    elif User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
        errors.append('An account with this email already exists.')
    if user_type not in {PlatformUser.Role.STUDENT, PlatformUser.Role.PARENT}:
        errors.append('Please select a valid account type.')
    if application_type not in PlatformUser.ApplicationType.values:
        errors.append('Please select a valid application type.')
    phone_number = ''
    if user_type == PlatformUser.Role.STUDENT:
        if phone_country_code not in VALID_PHONE_COUNTRY_CODES:
            errors.append('Please select a valid country code.')
        phone_digits = re.sub(r'\D', '', phone_local)
        if len(phone_digits) < 6:
            errors.append('Please enter a valid phone number.')
        elif len(phone_digits) > 15:
            errors.append('Phone number is too long.')
        else:
            phone_number = _build_phone_number(phone_country_code, phone_local)
    if parent_email:
        try:
            validate_email(parent_email)
        except ValidationError:
            errors.append('Please enter a valid parent email address.')
    if len(password) < 8:
        errors.append('Password must be at least 8 characters long.')
    if password != confirm_password:
        errors.append('Passwords do not match.')
    if not privacy_policy:
        errors.append('You must agree to the Privacy Policy.')
    if not data_processing:
        errors.append('You must agree to the Data Processing Terms.')

    recaptcha_ok, recaptcha_error = _verify_recaptcha(
        recaptcha_token,
        request.META.get('REMOTE_ADDR'),
    )
    if not recaptcha_ok:
        errors.append(recaptcha_error)

    return errors, form_data, {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'user_type': user_type,
        'application_type': application_type,
        'password': password,
        'phone_number': phone_number,
        'parent_email': parent_email,
    }


def _validate_admin_student_form(request):
    """Validate admin-created student accounts (no recaptcha / policy checkboxes)."""
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip().lower()
    application_type = request.POST.get('application_type', '').strip()
    password = request.POST.get('password', '')
    confirm_password = request.POST.get('confirm_password', '')
    parent_email = request.POST.get('parent_email', '').strip().lower()
    school_name = request.POST.get('school_name', '').strip()
    profile_photo = request.FILES.get('profile_photo')

    errors = []
    if not first_name:
        errors.append('First name is required.')
    if not last_name:
        errors.append('Last name is required.')
    if not email:
        errors.append('Email is required.')
    elif User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
        errors.append('An account with this email already exists.')
    if application_type not in PlatformUser.ApplicationType.values:
        errors.append('Please select a valid application type.')
    if parent_email:
        try:
            validate_email(parent_email)
        except ValidationError:
            errors.append('Please enter a valid parent email address.')
    if len(password) < 8:
        errors.append('Password must be at least 8 characters long.')
    if password != confirm_password:
        errors.append('Passwords do not match.')
    photo_error = validate_profile_photo(profile_photo)
    if photo_error:
        errors.append(photo_error)

    return errors, {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'user_type': PlatformUser.Role.STUDENT,
        'application_type': application_type,
        'password': password,
        'parent_email': parent_email,
        'school_name': school_name,
        'profile_photo': profile_photo,
    }


def create_registered_user(
    *,
    first_name,
    last_name,
    email,
    user_type,
    application_type,
    password,
    phone_number='',
    parent_email='',
    school_name='',
    school_address='',
    profile_photo=None,
):
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    platform_user = PlatformUser.objects.create(
        user=user,
        first_name=first_name,
        last_name=last_name,
        email=email,
        role=user_type,
        application_type=application_type,
    )
    if platform_user.is_student:
        profile = ensure_student_personal_profile(platform_user)
        if phone_number:
            profile.phone_number = phone_number
        if parent_email:
            profile.parent_email = parent_email
        if school_name:
            profile.school_name = school_name
        if school_address:
            profile.school_address = school_address
        if profile_photo:
            replace_profile_photo(profile, profile_photo)
        profile.save()
    return user, platform_user
