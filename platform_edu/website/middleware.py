# website/middleware.py
from django.utils import timezone
from website.models import Premium_Members, Users, ApexUsers

class UpdatePremiumStatusMiddleware:
    """
    Checks if user's customer_id exists in Premium_Members table.
    If yes, they are premium. If no, they are not premium.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_email = request.session.get('email')
        is_apex_user = request.session.get('is_apex_user', False)

        if user_email:
            try:
                is_premium = False  # Default to False
                customer_id = None
                
                # Check ApexUsers first if this is an Apex user
                if is_apex_user:
                    apex_user = ApexUsers.objects.filter(email=user_email).first()
                    if apex_user and apex_user.customer_id:
                        customer_id = apex_user.customer_id
                else:
                    # Regular user - check Users table
                    custom_user = Users.objects.filter(email=user_email).first()
                    if custom_user and custom_user.customer_id:
                        customer_id = custom_user.customer_id

                # Check if customer_id exists in Premium_Members table
                if customer_id:
                    is_premium = Premium_Members.objects.filter(
                        customer_id=customer_id,
                        subscribed="Yes"
                    ).exists()

                # Update user_type in session (matches what login sets)
                if is_premium:
                    user_type = "premium"
                elif is_apex_user:
                    user_type = "apex_user"
                else:
                    user_type = "free"
                    
                if request.session.get("user_type") != user_type:
                    request.session["user_type"] = user_type
                    print(f"🔄 Updated user type for {user_email}: {user_type}")

            except Exception as e:
                # On error, keep current status to be safe
                print(f"⚠️ Premium status check failed for {user_email}: {e}")

        return self.get_response(request)
