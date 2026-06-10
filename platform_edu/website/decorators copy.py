from django.utils import timezone
from functools import wraps
from .models import User_Journey
from datetime import timedelta
from .ip_checker import get_details

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
        # Initialize the journey path if it doesn't exist
        if 'journey_path' not in request.session:
            request.session['journey_path'] = []
            request.session['session_start'] = timezone.now().isoformat()  # Store as ISO string

        # Append the current path to the journey path
        request.session['journey_path'].append(request.path)
        request.session.modified = True

        # Immediately store the journey on each page visit
        store_journey(request)

        # Call the original view function
        response = view_func(request, *args, **kwargs)
        return response

    return wrapper

def store_journey(request):
    current_time = timezone.now()
    two_minutes_ago = current_time - timedelta(minutes=2)
    
    
    user_email = request.session.get('email')

    if user_email is None:
        user_email = "Anynomous"
    
    # Get IP address
    x_forw_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forw_for is not None:
        ip_address = x_forw_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    # Get device information from user agent
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    device_info = get_device_info(user_agent)
    
    # Get country information from IP address
    try:
        city = "Unknown"
        country = "Unknown"
    except Exception as e:
        country = "Unknown"
    
    if user_email:
        # Check if an entry exists for the same user within the last 2 minutes
        recent_journey = User_Journey.objects.filter(
            email=user_email,
            ip_address=ip_address,
            session_end__gte=two_minutes_ago
        ).exists()
        
        # If no recent entry found, store a new journey
        if not recent_journey:
            new_journey = User_Journey(
                email=user_email,
                ip_address=ip_address,
                device=device_info,
                country=country,
                journey_path=request.session.get('journey_path', []),
                session_start=request.session.get('session_start', current_time), 
                date_created=current_time,
                session_end=current_time
            )
            new_journey.save()
