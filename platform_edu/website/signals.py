from django.dispatch import receiver
from allauth.socialaccount.signals import pre_social_login
from allauth.account.signals import user_signed_up, user_logged_in
from django.contrib.auth.models import User
from .models import Users, Premium_Members
import random
import string

@receiver(user_signed_up)
def create_custom_user_for_social_signup(sender, request, user, **kwargs):
    """
    Signal handler that creates a Users record when someone signs up via Google OAuth
    """
    # Check if this is a social account signup (Google)
    if hasattr(user, 'socialaccount_set') and user.socialaccount_set.exists():
        try:
            # Check if Users record already exists
            Users.objects.get(email=user.email)
            return  # User record already exists, nothing to do
        except Users.DoesNotExist:
            pass  # Continue to create new user record
        
        # Generate a unique customer ID
        customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        while Users.objects.filter(customer_id=customer_id).exists():
            customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        
        # Generate unique referral code
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while Users.objects.filter(referral_code=referral_code).exists():
            referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # Create custom Users model entry with default values
        custom_user = Users.objects.create(
            first_name=user.first_name or "Google",
            last_name=user.last_name or "User",
            email=user.email,
            password="N/A",  # Google OAuth users don't have local passwords
            curriculum="IB",  # Default value
            occupation="Student",  # Default value
            customer_id=customer_id,
            avatar='avatar1.png',
            school_name="Not specified",  # Default value
            exam_session="May2026",  # Default value
            verified=True,  # Google OAuth users are already verified
            referral_code=referral_code
        )
        
        print(f"Created Users record for Google signup: {user.email}")


@receiver(pre_social_login)
def populate_user_info_from_google(sender, request, sociallogin, **kwargs):
    """
    Signal handler that populates user info from Google profile data
    """
    if sociallogin.account.provider == 'google':
        # Get extra data from Google
        extra_data = sociallogin.account.extra_data
        user = sociallogin.user
        
        # If user doesn't have first/last name, try to get from Google
        if not user.first_name and extra_data.get('given_name'):
            user.first_name = extra_data.get('given_name')
        
        if not user.last_name and extra_data.get('family_name'):
            user.last_name = extra_data.get('family_name')
        
        # Save the user with updated info
        if user.pk:
            user.save()


@receiver(user_logged_in)
def setup_session_for_social_login(sender, request, user, **kwargs):
    """
    Signal handler that sets up session data when user logs in via Google OAuth
    """
    # Check if this is a social account login (Google)
    if hasattr(user, 'socialaccount_set') and user.socialaccount_set.exists():
        email = user.email.lower()
        
        try:
            # Try to fetch user data from Users model by email
            user_data = Users.objects.get(email=email)
            
            # Check if user is premium member
            try:
                Premium_Members.objects.get(customer_id=user_data.customer_id)
                user_type = "premium"
            except Premium_Members.DoesNotExist:
                user_type = "free"
            
            # Set up session data similar to normal login
            request.session['user_name'] = user_data.first_name
            request.session['last_name'] = user_data.last_name
            request.session['school_name'] = user_data.school_name
            request.session['curriculum'] = user_data.curriculum
            # Extract only the part before the first hyphen from occupation
            occupation = user_data.occupation.split('-')[0] if user_data.occupation else ''
            request.session['occupation'] = occupation
            request.session['email'] = user_data.email
            request.session['avatar'] = user_data.avatar
            request.session['user_type'] = user_type
            
        except Users.DoesNotExist:
            # Fallback session data for Google users without Users record
            request.session['user_name'] = user.first_name or "Google"
            request.session['last_name'] = user.last_name or "User"
            request.session['school_name'] = "Not specified"
            request.session['curriculum'] = "Not specified"
            request.session['occupation'] = "Not specified"
            request.session['email'] = email
            request.session['avatar'] = 'avatar1.png'
            request.session['user_type'] = 'free'
        
        # Set other required session data
        request.session['already_user'] = True
        request.session['updated_creds'] = False
        request.session['already_registered'] = True
        
        # Set persistent login (30 days default)
        request.session.set_expiry(None)
        
        print(f"Session set up for Google OAuth user: {email}")
