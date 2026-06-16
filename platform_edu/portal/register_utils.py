import json
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse

from .models import PlatformUser
from .profile_access import ensure_student_personal_profile


def _register_form_context(form_data=None):
    form_data = form_data or {}
    return {
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
        'recaptcha_enabled': settings.RECAPTCHA_ENABLED,
        **form_data,
    }


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

    form_data = {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'user_type': user_type,
        'application_type': application_type,
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
    }


def create_registered_user(*, first_name, last_name, email, user_type, application_type, password):
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
        ensure_student_personal_profile(platform_user)
    return user, platform_user
