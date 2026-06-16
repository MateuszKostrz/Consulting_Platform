from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import quote


LOGIN_EXEMPT_PREFIXES = (
    '/login/',
    '/register/',
    '/logout/',
    '/admin/',
    '/static/',
    '/media/',
)


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path
            if not any(path.startswith(prefix) for prefix in LOGIN_EXEMPT_PREFIXES):
                login_url = reverse('login')
                next_url = request.get_full_path()
                if next_url and next_url != login_url:
                    return redirect(f'{login_url}?next={quote(next_url, safe="")}')
                return redirect(login_url)
        return self.get_response(request)
