import uuid
from django.utils import timezone
from functools import wraps
from .models import User_Journey
from datetime import timedelta

COOKIE_NAME = "edunade_vid"
COOKIE_AGE = 60 * 60 * 24 * 365 * 2  # 2 years


def get_device_info(user_agent):
    """
    Extract device information from user agent string
    """
    if not user_agent:
        return "Unknown"
    
    user_agent = user_agent.lower()
    
    # Mobile devices
    if any(mobile in user_agent for mobile in ['iphone', 'android', 'mobile', 'phone']):
        if 'iphone' in user_agent:
            return "iPhone"
        elif 'android' in user_agent:
            return "Android Phone"
        else:
            return "Mobile Device"
    
    # Tablets
    elif any(tablet in user_agent for tablet in ['ipad', 'tablet']):
        if 'ipad' in user_agent:
            return "iPad"
        else:
            return "Tablet"
    
    # Desktop/Laptop
    elif any(desktop in user_agent for desktop in ['windows', 'macintosh', 'linux', 'x11']):
        if 'windows' in user_agent:
            return "Windows PC"
        elif 'macintosh' in user_agent or 'mac os' in user_agent:
            return "Mac"
        elif 'linux' in user_agent or 'x11' in user_agent:
            return "Linux PC"
        else:
            return "Desktop"
    
    # Default fallback
    else:
        return "Unknown Device"


def track_user_journey(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # ✅ Step 1: Ensure visitor_id exists BEFORE DB writes
        visitor_id = request.COOKIES.get(COOKIE_NAME)
        if not visitor_id:
            visitor_id = str(uuid.uuid4())
            request.new_cookie = True
        else:
            request.new_cookie = False
        
        # ✅ Attach visitor_id to request for internal use
        request.visitor_id = visitor_id

        # ✅ Step 2: Track session journey
        if "journey_path" not in request.session:
            request.session["journey_path"] = []
            request.session["session_start"] = timezone.now().isoformat()

        request.session["journey_path"].append(request.path)
        request.session.modified = True

        # Execute the view
        response = view_func(request, *args, **kwargs)

        # ✅ Step 3: Save the journey log
        store_journey(request, visitor_id)

        # ✅ Step 4: Only now set cookie in browser
        if getattr(request, "new_cookie", False):
            response.set_cookie(
                COOKIE_NAME,
                visitor_id,
                max_age=COOKIE_AGE,
                path="/",
                secure=False,  # change to True on production HTTPS
                httponly=True,
                samesite="Lax",
            )

        return response

    return wrapper


def store_journey(request, visitor_id):
    current_time = timezone.now()
    two_minutes_ago = current_time - timedelta(minutes=2)

    user_email = request.session.get("email", "Anonymous")

    # IP extraction
    x_forw_for = request.META.get("HTTP_X_FORWARDED_FOR")
    ip_address = x_forw_for.split(",")[0] if x_forw_for else request.META.get("REMOTE_ADDR")

    # Device
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    device_info = get_device_info(user_agent)

    country = "Unknown"

    # ✅ Avoid duplicating entries if user refreshes within 2 min window
    recent_journey = User_Journey.objects.filter(
        email=user_email,
        ip_address=ip_address,
        session_end__gte=two_minutes_ago
    ).exists()

    if not recent_journey:
        User_Journey.objects.create(
            email=user_email,
            visitor_id=visitor_id,
            ip_address=ip_address,
            device=device_info,
            country=country,
            journey_path=request.session.get("journey_path", []),
            session_start=request.session.get("session_start", current_time),
            date_created=current_time,
            session_end=current_time,
        )
