# analytics/middleware/visitor_cookie.py
import uuid
from django.utils import timezone
from website.models import User_Journey  # adjust path

COOKIE_NAME = "edunade_vid"
COOKIE_AGE = 60 * 60 * 24 * 365 * 2  # 2 years

class VisitorCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        ip = request.META.get("REMOTE_ADDR", "unknown")
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]

        # 1️⃣ Retrieve or set the visitor cookie
        visitor_id = request.COOKIES.get(COOKIE_NAME)
        if not visitor_id:
            visitor_id = str(uuid.uuid4())
            response.set_cookie(
                COOKIE_NAME,
                visitor_id,
                max_age=COOKIE_AGE,
                path="/",
                secure=True,     # ensure HTTPS
                httponly=False,  # if you need JS access
                samesite="Lax",
            )

        # 2️⃣ Save user journey record
        try:
            User_Journey.objects.create(
                email="anonymous@visitor.com",
                visitor_id=visitor_id,
                ip_address=ip,
                device=user_agent,
                country="unknown",
                journey_path={"path": request.path},
                session_start=timezone.now(),
                session_end=timezone.now(),
                date_created=timezone.now(),
            )
        except Exception as e:
            print("❌ Journey log failed:", e)

        return response
