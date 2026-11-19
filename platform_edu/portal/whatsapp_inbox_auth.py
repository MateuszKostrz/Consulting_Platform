from __future__ import annotations

import secrets
from functools import wraps

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

SESSION_KEY = 'donna_whatsapp_inbox_auth'


def _inbox_credentials_configured() -> bool:
    return bool(
        (getattr(settings, 'WHATSAPP_INBOX_EMAIL', '') or '').strip()
        and (getattr(settings, 'WHATSAPP_INBOX_PASSWORD', '') or '').strip()
    )


def is_whatsapp_inbox_authenticated(request: HttpRequest) -> bool:
    return bool(request.session.get(SESSION_KEY))


def verify_whatsapp_inbox_login(email: str, password: str) -> bool:
    if not _inbox_credentials_configured():
        return False
    expected_email = settings.WHATSAPP_INBOX_EMAIL.strip().lower()
    expected_password = settings.WHATSAPP_INBOX_PASSWORD
    return secrets.compare_digest(
        email.strip().lower(),
        expected_email,
    ) and secrets.compare_digest(password, expected_password)


def login_whatsapp_inbox(request: HttpRequest) -> None:
    request.session[SESSION_KEY] = True
    request.session.set_expiry(60 * 60 * 12)


def logout_whatsapp_inbox(request: HttpRequest) -> None:
    request.session.pop(SESSION_KEY, None)


def require_whatsapp_inbox(view_func):
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not is_whatsapp_inbox_authenticated(request):
            login_url = reverse('donna-whatsapp-login')
            next_path = request.get_full_path()
            if next_path and next_path != login_url:
                return redirect(f'{login_url}?next={next_path}')
            return redirect(login_url)
        return view_func(request, *args, **kwargs)

    return wrapper


def require_whatsapp_inbox_json(view_func):
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not is_whatsapp_inbox_authenticated(request):
            from django.http import JsonResponse

            return JsonResponse({'error': 'Forbidden'}, status=403)
        return view_func(request, *args, **kwargs)

    return wrapper