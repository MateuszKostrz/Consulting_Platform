from django.shortcuts import render, redirect
from django.core.mail import send_mail, BadHeaderError
from django.core.mail import EmailMessage
from platform_edu import settings
from datetime import datetime, timedelta
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound
import random
from django.utils.timezone import now
from django.utils import timezone
import inspect
from django.views.generic import ListView, DetailView, CreateView
from django.views import View
from ckeditor.widgets import CKEditorWidget
from django.shortcuts import render
import re
import requests
from rest_framework import generics
from .models import Math_AI_SL_Questionbank, Math_AI_HL_Questionbank, Math_AA_SL_Questionbank, Past_Paper_Videos, Past_Paper_Videos_AI_HL, Past_Paper_Videos_AA_SL, Past_Paper_Videos_AA_HL, Uni_Database, Users, User_Journey, Premium_Members, Fillout_Survey, Math_AA_HL_Questionbank, Math_AA_HL_Questionbank_Backup, Biology_SL_Questionbank, Biology_HL_Questionbank, Webinars_Live, Physics_SL_Questionbank, Physics_HL_Questionbank, Comp_Sci_SL_Questionbank, Comp_Sci_HL_Questionbank, Past_Paper_Videos_Physics_SL, Past_Paper_Videos_Physics_HL, TutorSession, StudentManagement, UserQuestionProgress, NewsAnnouncement, Past_Paper_Videos_Comp_Sci_SL, Past_Paper_Videos_Chemistry_SL, Past_Paper_Videos_Chemistry_HL, Chemistry_SL_Questionbank, Chemistry_HL_Questionbank, History_SL_Questionbank, History_HL_Questionbank, ApexUsers
from .models import RevisionChapter, RevisionTopic, RevisionSkill, StudentSkillMastery, RevisionAttempt, QuestionSkillTag, ClassTranscriptAnalysis, LearningPathProgress
from .models import RevisionSubQuestion, RevisionMCQOption
from . import revision_engine as re_service
from django.contrib.auth.models import User as DjangoUser
from .serializers import Math_AI_SL_QuestionsSerializer, Math_AI_HL_QuestionsSerializer, Math_AA_SL_QuestionsSerializer, Math_AA_HL_QuestionsSerializer, Math_AA_HL_Backup_QuestionsSerializer, Biology_SL_QuestionbankSerializer, Biology_HL_QuestionbankSerializer, Physics_SL_QuestionbankSerializer, Physics_HL_QuestionbankSerializer, Comp_Sci_SL_QuestionbankSerializer, Comp_Sci_HL_QuestionbankSerializer, Chemistry_SL_QuestionbankSerializer, Chemistry_HL_QuestionbankSerializer, History_SL_QuestionbankSerializer, History_HL_QuestionbankSerializer
from django.db.models import IntegerField, Count
from django.db.models.functions import Cast
from django.db.models import Q
from django.db.models import Case, When, Value
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from .decorators import track_user_journey
import string
import secrets
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import io
import uuid
import zipfile
import shutil
from pathlib import Path
from .discipline_data import discipline_data
from .paper_latex_html import parse_tex_bundle, write_manifest, read_manifest
import stripe
from django.views.decorators.http import require_POST, require_http_methods
import logging
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.conf import settings
from rest_framework.response import Response
import json
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)


def verify_recaptcha(token, remote_ip=None):
    """
    Verify Google reCAPTCHA v3 token
    Returns tuple: (is_valid, score, error_message)
    """
    try:
        data = {
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': token,
        }
        if remote_ip:
            data['remoteip'] = remote_ip
        
        logger.info(f"Verifying reCAPTCHA token for IP: {remote_ip}")
        response = requests.post(settings.RECAPTCHA_VERIFY_URL, data=data, timeout=5)
        result = response.json()
        
        logger.info(f"reCAPTCHA response: {result}")
        
        if result.get('success'):
            score = result.get('score', 0)
            logger.info(f"reCAPTCHA score: {score}")
            # reCAPTCHA v3 returns a score between 0 (bot) and 1 (human)
            # We'll accept scores >= 0.5
            if score >= 0.6:
                return (True, score, None)
            else:
                return (False, score, f"reCAPTCHA score too low: {score}. Please try again.")
        else:
            error_codes = result.get('error-codes', [])
            logger.error(f"reCAPTCHA verification failed with errors: {error_codes}")
            return (False, 0, f"reCAPTCHA verification failed: {', '.join(error_codes)}")
    except requests.exceptions.Timeout:
        logger.error("reCAPTCHA verification timeout")
        return (False, 0, "Verification timeout. Please try again.")
    except Exception as e:
        logger.error(f"reCAPTCHA verification error: {str(e)}")
        return (False, 0, "Verification error. Please try again.")



@require_POST
@csrf_exempt
def webhook(request):
    # Get the raw payload and signature header
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    
    # TODO: Move this to environment variables for security
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET



    try:
        # Attempt to construct the event using Stripe's Webhook helper
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Handle event of type 'checkout.session.completed'
    if event.type == 'checkout.session.completed':
        session = event.data.object
        client_reference_id = session.client_reference_id
        
        # Default to monthly
        subscription_days = 50
        clean_customer_id = client_reference_id
        
        # Parse subscription type and customer ID
        if client_reference_id and '-' in client_reference_id:
            subscription_type, clean_customer_id = client_reference_id.split('-', 1)
            if subscription_type == 'yearly':
                subscription_days = 365

            elif subscription_type == 'monthly':
                subscription_days = 30
            
            elif subscription_type == 'trial':
                # Trial subscriptions: 3-day trial + 30 days for the first month
                # Set to 33 days initially (3 days trial + 30 days subscription)
                subscription_days = 33
        else:
            # Default if no type specified
            subscription_type = 'monthly'

        # Calculate subscription end date
        subscription_end_date = datetime.now() + timedelta(days=subscription_days)
        stripe_customer_id = str(session.customer) if session.customer else None


        send_mail(
            subject='Subscription Payment Successful',
            message=f'{clean_customer_id} has successfully paid for a {subscription_type} subscription.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['contact@edunade.com'],
            fail_silently=False,
        )

        # Save to database
        try:
            # Try to find the user to get their name and email
            user_first_name = "None"
            user_last_name = "None"
            user_email = "None"
            
            try:
                user = Users.objects.get(customer_id=clean_customer_id)
                user_first_name = user.first_name
                user_last_name = user.last_name
                user_email = user.email
            except Users.DoesNotExist:
                pass  # Keep default "None" values
            
            existing_member = Premium_Members.objects.filter(customer_id=clean_customer_id).first()
            
            if existing_member:
                # Update existing record
                existing_member.stripe_customer_id = stripe_customer_id or existing_member.stripe_customer_id
                existing_member.subscribed = "Yes"
                existing_member.subscription_end_date = subscription_end_date
                existing_member.first_name = user_first_name
                existing_member.last_name = user_last_name
                existing_member.email = user_email
                existing_member.subscription_type = 'free_trial' if subscription_type == 'trial' else subscription_type
                existing_member.save()
            else:
                # Create new premium member
                Premium_Members.objects.create(
                    customer_id=clean_customer_id or "unknown",
                    stripe_customer_id=stripe_customer_id or "unknown",
                    first_name=user_first_name,
                    last_name=user_last_name,
                    email=user_email,
                    subscribed="Yes",
                    subscription_end_date=subscription_end_date,
                    subscription_type='free_trial' if subscription_type == 'trial' else subscription_type
                )
        except:
            pass
            
    elif event.type == 'customer.subscription.deleted':
        # Handle subscription cancellation
        subscription = event.data.object
        customer_id = subscription.customer
        
        try:
            premium_member = Premium_Members.objects.filter(stripe_customer_id=customer_id).first()
            if premium_member:
                # Only update if status is "Cancelled" to avoid conflicts with manual deletions
                if premium_member.subscribed == "Cancelled":
                    premium_member.subscribed = "No"
                    premium_member.subscription_end_date = None
                    premium_member.save()
        except Exception as e:
            logger.error(f"Error handling subscription deletion webhook: {str(e)}")

    return JsonResponse({'success': True})



@track_user_journey
def login(request):
    # Check if this is an Apex or TopIBTutors subdomain login (both use ApexUsers table)
    host = request.get_host().lower()
    theme = request.GET.get('theme', '')
    is_apex = 'apex' in host or 'topibtutors' in host or theme == 'apex' or theme == 'topibtutors' or request.POST.get('is_apex') == 'true'
    
    # Determine current subdomain for source_domain check
    if 'topibtutors' in host or theme == 'topibtutors':
        current_subdomain = 'topibtutors'
    else:
        current_subdomain = 'apex'
    
    if request.method == 'POST':
        email = request.POST['email'].strip().lower()  # Remove spaces and convert to lowercase
        password = request.POST['passwd']
        remember_me = request.POST.get('remember-me')
        user = authenticate(username=email, password=password)

        if user is not None:
            # For Apex subdomain, check if user exists in ApexUsers table
            if is_apex:
                try:
                    apex_user = ApexUsers.objects.get(email=email)
                    
                    # Check if user's source_domain matches current subdomain
                    if apex_user.source_domain != current_subdomain:
                        domain_names = {'apex': 'Apex Tuition Australia', 'topibtutors': 'Top IB Tutors'}
                        correct_domain = domain_names.get(apex_user.source_domain, apex_user.source_domain)
                        errors = [f"This account is registered with {correct_domain}. Please log in from the correct website."]
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({'success': False, 'errors': errors})
                        return render(request, 'login.html', {'errors': errors})
                    
                    # Check if Apex user is premium member
                    try:
                        Premium_Members.objects.get(customer_id=apex_user.customer_id, subscribed="Yes")
                        user_type = "premium"
                    except Premium_Members.DoesNotExist:
                        user_type = "apex_user"

                    # Set session data for Apex user
                    request.session['user_name'] = apex_user.first_name
                    request.session['last_name'] = apex_user.last_name
                    request.session['email'] = apex_user.email
                    request.session['avatar'] = apex_user.avatar
                    request.session['school_name'] = apex_user.school_name
                    request.session['curriculum'] = apex_user.curriculum
                    request.session['occupation'] = apex_user.occupation
                    request.session['exam_session'] = apex_user.exam_session
                    request.session['user_type'] = user_type
                    request.session['is_apex_user'] = True
                    request.session['source_domain'] = apex_user.source_domain
                    request.session['already_user'] = True
                    request.session['already_registered'] = True

                    if remember_me:
                        request.session.set_expiry(60 * 24 * 60 * 60)
                    else:
                        request.session.set_expiry(None)

                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': True, 'redirect_url': '/home/'})
                    return redirect('home')
                    
                except ApexUsers.DoesNotExist:
                    domain_names = {'apex': 'Apex Tuition Australia', 'topibtutors': 'Top IB Tutors'}
                    current_domain_name = domain_names.get(current_subdomain, current_subdomain)
                    errors = [f"This account is not registered with {current_domain_name}. Please register first."]
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'errors': errors})
                    return render(request, 'login.html', {'errors': errors})
            
            # Regular (non-Apex) login flow
            # Try to fetch user data from Users model by email
            try:
                user_data = Users.objects.get(email=email)
                
                # Check if user's email is verified
                if not user_data.verified:
                    # Store email in session for verification page
                    request.session['verification_email'] = email
                    request.session['user_first_name'] = user_data.first_name
                    
                    # Generate new verification code if needed
                    if not user_data.verification_code or not user_data.verification_code_created:
                        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                        user_data.verification_code = verification_code
                        user_data.verification_code_created = timezone.now()
                        user_data.save()
                        
                        # Send verification email
                        try:
                            subject = 'Verify Your Email - Edunade Academy'
                            context = {
                                'user_name': user_data.first_name,
                                'verification_code': verification_code,
                                'platform_name': 'Edunade Academy',
                            }
                            email_html_message = render_to_string('email/verification_code_email.html', context)
                            
                            from_email = 'Contact | Edunade Academy <{}>'.format(settings.DEFAULT_FROM_EMAIL)
                            
                            verification_email = EmailMultiAlternatives(
                                subject=subject,
                                body=f"Your verification code is: {verification_code}",
                                from_email=from_email,
                                to=[email]
                            )
                            verification_email.attach_alternative(email_html_message, "text/html")
                            verification_email.send()
                        except Exception as e:
                            print(f"Failed to send verification email to {email}: {str(e)}")
                    
                    # Redirect to verification page
                    errors = ["Please verify your email address before logging in. A verification code has been sent to your email."]
                    if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'errors': errors, 'redirect_url': '/verify-email/'})
                    return redirect('verify-email')

                
                # Check if user is premium member by looking up customer_id in Premium_Members table
                try:
                    Premium_Members.objects.get(customer_id=user_data.customer_id)
                    user_type = "premium"
                except Premium_Members.DoesNotExist:
                    user_type = "free"
                
                # Store data from Users model
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
                # This shouldn't happen with the new signal handler, but keep as fallback
                # Try to create Users record for existing Django auth user (Google OAuth users)
                try:
                    # Generate a unique customer ID
                    customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                    while Users.objects.filter(customer_id=customer_id).exists():
                        customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                    
                    # Create custom Users model entry
                    user_data = Users.objects.create(
                        first_name=user.first_name or "Google",
                        last_name=user.last_name or "User",
                        email=email,
                        password="N/A",  # Google OAuth users don't have local passwords
                        curriculum="Not specified",
                        occupation="Not specified",
                        customer_id=customer_id,
                        avatar='avatar1.png',
                        school_name="Not specified",
                        exam_session="Not specified",
                        verified=True  # OAuth users are verified
                    )
                    
                    # Now use the newly created user_data
                    request.session['user_name'] = user_data.first_name
                    request.session['last_name'] = user_data.last_name
                    request.session['school_name'] = user_data.school_name
                    request.session['curriculum'] = user_data.curriculum
                    request.session['occupation'] = user_data.occupation
                    request.session['email'] = user_data.email
                    request.session['avatar'] = user_data.avatar
                    request.session['user_type'] = 'free'
                    
                except Exception as e:
                    print(f"Failed to create Users record for {email}: {str(e)}")
                    # Final fallback to Django auth user data
                    request.session['user_name'] = user.first_name
                    request.session['last_name'] = str(user.last_name)
                    request.session['school_name'] = ''
                    request.session['curriculum'] = ''
                    request.session['occupation'] = ''
                    request.session['student_type'] = ''
                    request.session['email'] = str(user.email)
                    request.session['avatar'] = 'avatar1.png'
                    request.session['user_type'] = 'free'  # Default to free if no Users record

            # Set other session data
            request.session['already_user'] = True
            request.session['updated_creds'] = False
            request.session['already_registered'] = True

            # Handle Remember Me functionality
            if remember_me:
                # Extended session for 60 days when "Remember Me" is checked
                request.session.set_expiry(60 * 24 * 60 * 60)
            else:
                # Default session duration (30 days as set in settings.py)
                # No need to set expiry to 0 anymore since we want persistent login
                request.session.set_expiry(None)  # Use default from settings

            # Handle AJAX requests
            if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect_url': '/home/'})

            return redirect('home')
        else:
            # Authentication failed
            errors = ["Invalid email or password."]
            
            # Handle AJAX requests
            if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': errors})
            
            # For regular form submission, render with errors
            return render(request, 'login.html', {'errors': errors})

    return render(request, 'login.html')

@track_user_journey
def register(request):
    # Check if this is an Apex or TopIBTutors subdomain registration
    host = request.get_host().lower()
    theme = request.GET.get('theme', '')
    is_apex = 'apex' in host or theme == 'apex' or request.POST.get('is_apex') == 'true'
    is_topibtutors = 'topibtutors' in host or theme == 'topibtutors'
    
    if is_apex or is_topibtutors:
        return register_apex(request)
    
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        curriculum = request.POST.get('curriculum', '')
        occupation = request.POST.get('occupation', '') 
        exam_session = request.POST.get('exam_session', '')
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        school_name = request.POST.get('school_name', '')
        terms_accepted = request.POST.get('terms', '') == 'on'
        recaptcha_token = request.POST.get('recaptcha_token', '')
        
        # Validation
        errors = []
        
        # Verify reCAPTCHA (skip for localhost in development OR if disabled via settings)
        skip_recaptcha = (settings.DEBUG and request.get_host() in ['localhost:8000', '127.0.0.1:8000', 'localhost', '127.0.0.1']) or not settings.RECAPTCHA_ENABLED
        
        if not skip_recaptcha and recaptcha_token:
            remote_ip = request.META.get('REMOTE_ADDR')
            is_valid, score, error_msg = verify_recaptcha(recaptcha_token, remote_ip)
            if not is_valid:
                logger.warning(f"reCAPTCHA failed for {email}: {error_msg} (score: {score})")
                errors.append("Bot verification failed. Please try again or contact support.")
        elif not skip_recaptcha and not recaptcha_token:
            errors.append("reCAPTCHA verification is required.")
        
        if skip_recaptcha:
            logger.info(f"reCAPTCHA verification skipped - DEBUG: {settings.DEBUG}, Host: {request.get_host()}, Enabled: {settings.RECAPTCHA_ENABLED}")
        
        # Required field validation
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email:
            errors.append("Email is required.")
        if not curriculum:
            errors.append("Curriculum is required.")
        if not occupation:
            errors.append("Occupation is required.")
        if not exam_session:
            errors.append("Exam session is required.")
        if not password:
            errors.append("Password is required.")
        if not confirm_password:
            errors.append("Password confirmation is required.")
        
        # Check if passwords match
        if password and confirm_password and password != confirm_password:
            errors.append("Passwords do not match.")

        # Check both terms checkboxes
        privacy_policy_accepted = request.POST.get('privacy_policy', '') == 'on'
        data_processing_accepted = request.POST.get('data_processing', '') == 'on'
        
        if not privacy_policy_accepted:
            errors.append("You must agree to the privacy policy & terms.")
        if not data_processing_accepted:
            errors.append("You must agree to the data processing terms.")
        
        # Password validation
        if password:
            if len(password) < 8:
                errors.append("Password must be at least 8 characters long.")
            if not any(c.isupper() for c in password):
                errors.append("Password must contain at least one uppercase letter.")
            if not any(c.isdigit() or not c.isalnum() for c in password):
                errors.append("Password must contain at least one number or symbol.")
        
        # Check if user already exists in Django User model
        if email and User.objects.filter(email=email).exists():
            errors.append("A user with this email address already exists.")
        
        if errors:
            # Return form with errors
            context = {
                'errors': errors,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'curriculum': curriculum,
                'occupation': occupation,
                'exam_session': exam_session,
                'school_name': school_name,
                'privacy_policy_checked': privacy_policy_accepted,
                'data_processing_checked': data_processing_accepted,
                'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
            }
            
            # Handle AJAX requests
            if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': errors})
            
            return render(request, 'register.html', context)
        
        else:

            user = User.objects.create_user(username=email, email=email, first_name = first_name, last_name = last_name)
            user.set_password(password)
            user.save()
    
            # Generate a unique customer ID
            customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            while Users.objects.filter(customer_id=customer_id).exists():
                customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                
            # Generate a 6-digit verification code
            verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # Generate unique referral code
            referral_code = None
            while True:
                referral_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
                if not Users.objects.filter(referral_code=referral_code).exists():
                    break
            
            # Create custom Users model entry
            custom_user = Users.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password="N/A",
                curriculum=curriculum,
                occupation=occupation,
                customer_id=customer_id,
                avatar='avatar1.png',
                school_name=school_name,
                exam_session=exam_session,
                verified=False,
                verification_code=verification_code,
                verification_code_created=timezone.now(),
                referral_code=referral_code
            )
            
            # Send verification email
            try:
                subject = 'Verify Your Email - Edunade Academy'
                context = {
                    'user_name': first_name,
                    'verification_code': verification_code,
                    'platform_name': 'Edunade Academy',
                }
                email_html_message = render_to_string('email/verification_code_email.html', context)
                
                from_email = 'Contact | Edunade Academy <{}>'.format(settings.DEFAULT_FROM_EMAIL)
                
                verification_email = EmailMultiAlternatives(
                    subject=subject,
                    body=f"Your verification code is: {verification_code}",
                    from_email=from_email,
                    to=[email]
                )
                verification_email.attach_alternative(email_html_message, "text/html")
                verification_email.send()
                
                print(f"Verification email sent successfully to {email}")
            except Exception as e:
                print(f"Failed to send verification email to {email}: {str(e)}")
                # Don't fail registration if email fails
            
            # Store email in session for verification page
            request.session['verification_email'] = email
            request.session['user_first_name'] = first_name
            
            # Return success response for AJAX handling
            if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect_url': '/verify-email/'})
            
            # Redirect to verification page for regular form submission
            return redirect('verify-email')
                
    
    return render(request, 'register.html', {'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY})


def register_apex(request):
    """
    Registration for Apex Tutoring Australia subdomain.
    Saves users to ApexUsers table instead of regular Users table.
    No email verification required.
    """
    if request.method == 'POST':
        # Get form data - same fields as regular registration
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        curriculum = request.POST.get('curriculum', '')
        occupation = request.POST.get('occupation', '') 
        exam_session = request.POST.get('exam_session', '')
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        school_name = request.POST.get('school_name', '')
        recaptcha_token = request.POST.get('recaptcha_token', '')
        
        # Validation
        errors = []
        
        # Verify reCAPTCHA (skip for localhost in development OR if disabled via settings)
        skip_recaptcha = (settings.DEBUG and request.get_host() in ['localhost:8000', '127.0.0.1:8000', 'localhost', '127.0.0.1']) or not settings.RECAPTCHA_ENABLED
        
        if not skip_recaptcha and recaptcha_token:
            remote_ip = request.META.get('REMOTE_ADDR')
            is_valid, score, error_msg = verify_recaptcha(recaptcha_token, remote_ip)
            if not is_valid:
                logger.warning(f"reCAPTCHA failed for {email}: {error_msg} (score: {score})")
                errors.append("Bot verification failed. Please try again or contact support.")
        elif not skip_recaptcha and not recaptcha_token:
            errors.append("reCAPTCHA verification is required.")
        
        if skip_recaptcha:
            logger.info(f"reCAPTCHA verification skipped for Apex - DEBUG: {settings.DEBUG}, Host: {request.get_host()}, Enabled: {settings.RECAPTCHA_ENABLED}")
        
        # Required field validation
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email:
            errors.append("Email is required.")
        if not curriculum:
            errors.append("Curriculum is required.")
        if not occupation:
            errors.append("Occupation is required.")
        if not exam_session:
            errors.append("Exam session is required.")
        if not password:
            errors.append("Password is required.")
        if not confirm_password:
            errors.append("Password confirmation is required.")
        
        # Check if passwords match
        if password and confirm_password and password != confirm_password:
            errors.append("Passwords do not match.")
        
        # Check both terms checkboxes
        privacy_policy_accepted = request.POST.get('privacy_policy', '') == 'on'
        data_processing_accepted = request.POST.get('data_processing', '') == 'on'
        
        if not privacy_policy_accepted:
            errors.append("You must agree to the privacy policy & terms.")
        if not data_processing_accepted:
            errors.append("You must agree to the data processing terms.")
        
        # Password validation
        if password:
            if len(password) < 8:
                errors.append("Password must be at least 8 characters long.")
            if not any(c.isupper() for c in password):
                errors.append("Password must contain at least one uppercase letter.")
            if not any(c.isdigit() or not c.isalnum() for c in password):
                errors.append("Password must contain at least one number or symbol.")
        
        # Check if user already exists in ApexUsers or Django User
        if email:
            if ApexUsers.objects.filter(email=email).exists():
                errors.append("A user with this email address already exists.")
            elif User.objects.filter(username=email).exists():
                errors.append("A user with this email address already exists.")
        
        if errors:
            context = {
                'errors': errors,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'curriculum': curriculum,
                'occupation': occupation,
                'exam_session': exam_session,
                'school_name': school_name,
                'privacy_policy_checked': privacy_policy_accepted,
                'data_processing_checked': data_processing_accepted,
                'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
            }
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': errors})
            
            return render(request, 'register_apex.html', context)
        
        else:
            # Create Django User for authentication
            user = User.objects.create_user(username=email, email=email, first_name=first_name, last_name=last_name)
            user.set_password(password)
            user.save()
            
            # Generate a unique customer ID
            customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            while ApexUsers.objects.filter(customer_id=customer_id).exists():
                customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

            # Determine source domain from theme
            theme = request.GET.get('theme', '')
            if not theme:
                theme = getattr(request, 'theme', 'apex')
            source_domain = 'topibtutors' if theme == 'topibtutors' else 'apex'

            # Create ApexUsers entry (no verification required)
            apex_user = ApexUsers.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password="N/A",
                curriculum=curriculum,
                occupation=occupation,
                exam_session=exam_session,
                customer_id=customer_id,
                school_name=school_name,
                avatar='avatar1.png',
                verified=True,
                source_domain=source_domain,
            )
            
            # Log the user in directly
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            auth_login(request, user)
            
            # Set session data
            request.session['user_name'] = apex_user.first_name
            request.session['last_name'] = apex_user.last_name
            request.session['email'] = apex_user.email
            request.session['avatar'] = apex_user.avatar
            request.session['school_name'] = apex_user.school_name
            request.session['curriculum'] = apex_user.curriculum
            request.session['occupation'] = apex_user.occupation
            request.session['exam_session'] = apex_user.exam_session
            request.session['user_type'] = 'apex_user'
            request.session['is_apex_user'] = True
            request.session['source_domain'] = source_domain
            request.session['already_user'] = True
            request.session['already_registered'] = True
            request.session.set_expiry(None)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect_url': '/home/'})
            
            return redirect('home')

    return render(request, 'register_apex.html', {'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY})


def register_qr_code(request):
    """
    QR Code registration - creates user with automatic 1 month premium access
    No email verification required - direct login after registration
    """
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        curriculum = request.POST.get('curriculum', '')
        occupation = request.POST.get('occupation', '') 
        exam_session = request.POST.get('exam_session', '')
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        school_name = request.POST.get('school_name', '')
        
        # Validation
        errors = []
        
        # Required field validation
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email:
            errors.append("Email is required.")
        if not curriculum:
            errors.append("Curriculum is required.")
        if not occupation:
            errors.append("Occupation is required.")
        if not exam_session:
            errors.append("Exam session is required.")
        if not password:
            errors.append("Password is required.")
        if not confirm_password:
            errors.append("Password confirmation is required.")
        
        # Check if passwords match
        if password and confirm_password and password != confirm_password:
            errors.append("Passwords do not match.")

        # Check both terms checkboxes
        privacy_policy_accepted = request.POST.get('privacy_policy', '') == 'on'
        data_processing_accepted = request.POST.get('data_processing', '') == 'on'
        
        if not privacy_policy_accepted:
            errors.append("You must agree to the privacy policy & terms.")
        if not data_processing_accepted:
            errors.append("You must agree to the data processing terms.")
        
        # Password validation
        if password:
            if len(password) < 8:
                errors.append("Password must be at least 8 characters long.")
            if not any(c.isupper() for c in password):
                errors.append("Password must contain at least one uppercase letter.")
            if not any(c.isdigit() or not c.isalnum() for c in password):
                errors.append("Password must contain at least one number or symbol.")
        
        # Check if user already exists in Django User model
        if email and User.objects.filter(email=email).exists():
            errors.append("A user with this email address already exists.")
        
        if errors:
            # Return form with errors
            context = {
                'errors': errors,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'curriculum': curriculum,
                'occupation': occupation,
                'exam_session': exam_session,
                'school_name': school_name,
                'privacy_policy_checked': privacy_policy_accepted,
                'data_processing_checked': data_processing_accepted,
            }
            
            # Handle AJAX requests
            if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': errors})
            
            return render(request, 'register_qr_code.html', context)
        
        else:
            # Create Django User with password
      
            django_user = User.objects.create_user(username=email, email=email, first_name=first_name, last_name=last_name, password=password)
            django_user.is_active = True
            django_user.save()
       
    
            # Generate a unique customer ID
            customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            while Users.objects.filter(customer_id=customer_id).exists():
                customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            
            # Generate unique referral code
            referral_code = None
            while True:
                referral_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
                if not Users.objects.filter(referral_code=referral_code).exists():
                    break
            
            # Create custom Users model entry (verified = True, no verification code needed)
            custom_user = Users.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password="N/A",
                curriculum=curriculum,
                occupation=occupation,
                customer_id=customer_id,
                avatar='avatar1.png',
                school_name=school_name,
                exam_session=exam_session,
                verified=True,  # No verification needed for QR code registration
                referral_code=referral_code
            )
            
            # Create Premium_Members entry with 1 month free access
            from datetime import timedelta
            subscription_end_date = timezone.now() + timedelta(days=30)
            
        
            premium_member = Premium_Members.objects.create(
                email=email,
                customer_id=customer_id,
                first_name=first_name,
                last_name=last_name,
                subscribed="Yes",
                stripe_customer_id="FREE",
                subscription_end_date=subscription_end_date
            )

            authenticated_user = authenticate(username=email, password=password)

            if authenticated_user:
                print(f"[QR Register] User is_active: {authenticated_user.is_active}")
                print(f"[QR Register] User is_authenticated: {authenticated_user.is_authenticated}")
            
            if authenticated_user is not None:
                auth_login(request, authenticated_user)

                # Set session variables (match the login view format)
                request.session['user_name'] = first_name
                request.session['last_name'] = last_name
                request.session['school_name'] = school_name
                request.session['curriculum'] = curriculum
                request.session['occupation'] = occupation.split('-')[0] if occupation else ''
                request.session['email'] = email
                request.session['avatar'] = 'avatar1.png'
                request.session['user_type'] = 'premium'
                request.session['customer_id'] = customer_id
                request.session['already_user'] = True
                request.session['updated_creds'] = False
                request.session['already_registered'] = True
                request.session['exam_session'] = exam_session
                request.session.set_expiry(None)  # Use default from settings
                request.session.modified = True
                request.session.save()
   
                
                # Return success response for AJAX handling
                if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'redirect_url': '/home/'})
                
                # Redirect to home page for regular form submission
                return redirect('home')
            else:
                print(f"[QR Register] Authentication failed for {email}")
                errors.append("Account created but login failed. Please try logging in manually.")
                context = {
                    'errors': errors,
                }
                if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': errors})
                return render(request, 'register_qr_code.html', context)
    
    return render(request, 'register_qr_code.html')


def verify_email(request):
    # Get email from session
    email = request.session.get('verification_email')
    user_first_name = request.session.get('user_first_name', '')
    is_apex_user = request.session.get('is_apex_user', False)
    
    if not email:
        messages.error(request, 'No verification session found. Please register again.')
        return redirect('register')
    
    if request.method == 'POST':
        submitted_code = request.POST.get('verification_code', '').strip()
        
        try:
            # Handle Apex users separately
            if is_apex_user:
                apex_user = ApexUsers.objects.filter(email=email).order_by('-id').first()
                
                if not apex_user:
                    raise ApexUsers.DoesNotExist
                
                if apex_user.verification_code == submitted_code:
                    if apex_user.verification_code_created:
                        time_diff = timezone.now() - apex_user.verification_code_created
                        if time_diff.total_seconds() > 1800:
                            context = {
                                'error': 'Verification code has expired. Please request a new code.',
                                'email': email,
                                'user_first_name': user_first_name
                            }
                            return render(request, 'verify_email.html', context)
                    
                    apex_user.verified = True
                    apex_user.status = 'active'
                    apex_user.verification_code = None
                    apex_user.verification_code_created = None
                    apex_user.save()
                    
                    user = User.objects.get(email=email)
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    auth_login(request, user)
                    
                    request.session['user_name'] = apex_user.first_name
                    request.session['last_name'] = apex_user.last_name
                    request.session['email'] = apex_user.email
                    request.session['avatar'] = apex_user.avatar
                    request.session['user_type'] = 'apex_tutor'
                    request.session['apex_role'] = apex_user.role
                    request.session['apex_status'] = apex_user.status
                    request.session['is_apex_user'] = True
                    request.session['already_user'] = True
                    request.session['already_registered'] = True
                    request.session.set_expiry(None)
                    
                    if 'verification_email' in request.session:
                        del request.session['verification_email']
                    if 'user_first_name' in request.session:
                        del request.session['user_first_name']
                    
                    messages.success(request, 'Email verified successfully! Welcome to Apex Tutoring Australia.')
                    return redirect('home')
                else:
                    context = {
                        'error': 'Invalid verification code. Please try again.',
                        'email': email,
                        'user_first_name': user_first_name
                    }
                    return render(request, 'verify_email.html', context)
            
            # Regular user verification
            custom_user = Users.objects.filter(email=email).order_by('-id').first()
            
            if not custom_user:
                raise Users.DoesNotExist
            
            # Check if code matches
            if custom_user.verification_code == submitted_code:
                # Check if code is not expired (valid for 30 minutes)
                if custom_user.verification_code_created:
                    time_diff = timezone.now() - custom_user.verification_code_created
                    if time_diff.total_seconds() > 1800:  # 30 minutes
                        context = {
                            'error': 'Verification code has expired. Please request a new code.',
                            'email': email,
                            'user_first_name': user_first_name
                        }
                        return render(request, 'verify_email.html', context)
                
                # Mark user as verified
                custom_user.verified = True
                custom_user.verification_code = None  # Clear the code
                custom_user.verification_code_created = None
                custom_user.save()
                
                # Get Django user and log them in
                user = User.objects.get(email=email)
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                auth_login(request, user)
                
                # Set session data
                request.session['user_name'] = custom_user.first_name
                request.session['last_name'] = custom_user.last_name
                request.session['school_name'] = custom_user.school_name
                request.session['curriculum'] = custom_user.curriculum
                request.session['occupation'] = custom_user.occupation
                request.session['email'] = custom_user.email
                request.session['avatar'] = custom_user.avatar
                request.session['user_type'] = 'free'
                request.session['already_user'] = True
                request.session['updated_creds'] = False
                request.session['already_registered'] = True
                request.session['exam_session'] = custom_user.exam_session
                request.session.set_expiry(None)  # Use default from settings
                
                # Clear verification session data
                if 'verification_email' in request.session:
                    del request.session['verification_email']
                if 'user_first_name' in request.session:
                    del request.session['user_first_name']
                
                messages.success(request, 'Email verified successfully! Welcome to Edunade Academy.')
                return redirect('home')
            else:
                context = {
                    'error': 'Invalid verification code. Please try again.',
                    'email': email,
                    'user_first_name': user_first_name
                }
                return render(request, 'verify_email.html', context)
                
        except (Users.DoesNotExist, ApexUsers.DoesNotExist):
            messages.error(request, 'User not found. Please register again.')
            return redirect('register')
        except User.DoesNotExist:
            messages.error(request, 'User authentication failed. Please contact support.')
            return redirect('register')
    
    context = {
        'email': email,
        'user_first_name': user_first_name
    }
    return render(request, 'verify_email.html', context)


def resend_verification_code(request):
    """Resend verification code to user's email"""
    email = request.session.get('verification_email')
    
    if not email:
        return JsonResponse({'success': False, 'error': 'No verification session found.'})
    
    try:
        # Get the most recent custom user with this email (in case of duplicates)
        custom_user = Users.objects.filter(email=email).order_by('-id').first()
        
        if not custom_user:
            raise Users.DoesNotExist
        
        # Generate new verification code
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Update user with new code
        custom_user.verification_code = verification_code
        custom_user.verification_code_created = timezone.now()
        custom_user.save()
        
        # Send verification email
        try:
            subject = 'Verify Your Email - Edunade Academy'
            context = {
                'user_name': custom_user.first_name,
                'verification_code': verification_code,
                'platform_name': 'Edunade Academy',
            }
            email_html_message = render_to_string('email/verification_code_email.html', context)
            
            from_email = 'Contact | Edunade Academy <{}>'.format(settings.DEFAULT_FROM_EMAIL)
            
            verification_email = EmailMultiAlternatives(
                subject=subject,
                body=f"Your verification code is: {verification_code}",
                from_email=from_email,
                to=[email]
            )
            verification_email.attach_alternative(email_html_message, "text/html")
            verification_email.send()
            
            return JsonResponse({'success': True, 'message': 'Verification code sent successfully!'})
        except Exception as e:
            print(f"Failed to resend verification email to {email}: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Failed to send email. Please try again.'})
            
    except Users.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found.'})

def logout_view(request):
    request.session.flush()
    return redirect('landing')

def forgot_password(request):
    print("made it here")
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        try:
            user = User.objects.get(email__iexact=email)
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build password reset URL
            reset_url = request.build_absolute_uri(
                reverse('reset-password', kwargs={'uidb64': uid, 'token': token})
            )
            
            # Send email using existing template
            subject = 'Password Reset Requested'
            context = {
                'email': user.email,
                'reset_url': reset_url,
                'user': user,
            }
            email_html_message = render_to_string('email/password_reset_email.html', context)
            
            try:
                send_mail(
                    subject=subject,
                    message='',
                    from_email=None,  # Use DEFAULT_FROM_EMAIL from settings
                    recipient_list=[user.email],
                    html_message=email_html_message,
                    fail_silently=False,
                )
                messages.success(request, 'Password reset link has been sent to your email.')
            except Exception as e:
                messages.error(request, 'There was an error sending the password reset email. Please try again later.')
                
        except User.DoesNotExist:
            # Don't reveal whether a user exists
            messages.info(request, 'If an account exists with this email, you will receive password reset instructions.')
        
        return render(request, 'forgot_password.html')
    
    return render(request, 'forgot_password.html')

def reset_password(request, uidb64, token):
    try:
        # Decode the user ID
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        
        # Check if the token is valid
        if default_token_generator.check_token(user, token):
            if request.method == 'POST':
                new_password1 = request.POST.get('new_password1')
                new_password2 = request.POST.get('new_password2')
                
                if new_password1 and new_password2 and new_password1 == new_password2:
                    # Validate password
                    if len(new_password1) < 8:
                        messages.error(request, 'Password must be at least 8 characters long.')
                        return render(request, 'reset_password.html', {
                            'validlink': True,
                            'uidb64': uidb64,
                            'token': token,
                        })
                    elif not any(c.isupper() for c in new_password1):
                        messages.error(request, 'Password must contain at least one uppercase letter.')
                        return render(request, 'reset_password.html', {
                            'validlink': True,
                            'uidb64': uidb64,
                            'token': token,
                        })
                    elif not any(c.isdigit() or not c.isalnum() for c in new_password1):
                        messages.error(request, 'Password must contain at least one number or symbol.')
                        return render(request, 'reset_password.html', {
                            'validlink': True,
                            'uidb64': uidb64,
                            'token': token,
                        })
                    else:
                        # Set new password
                        user.set_password(new_password1)
                        user.save()
                        
                        # Success message and redirect to login instead of auto-login
                        messages.success(request, 'Your password has been reset successfully! Please log in with your new password.')
                        return redirect('login')
                else:
                    messages.error(request, 'Passwords do not match.')
                    return render(request, 'reset_password.html', {
                        'validlink': True,
                        'uidb64': uidb64,
                        'token': token,
                    })
            
            # GET request - show the form
            return render(request, 'reset_password.html', {
                'validlink': True,
                'uidb64': uidb64,
                'token': token,
            })
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        pass
    
    # If anything goes wrong, invalidate the link
    return render(request, 'reset_password.html', {'validlink': False})

def calendar(request):
    return render(request, 'app-calendar.html')

def timeline(request):
    return render(request, 'timeline-fullscreen.html')

def academy_dashboard(request):
    return render(request, 'ENG/app-academy-dashboard.html')    

def settings_account(request):
    return render(request, 'settings-account.html')

def landing(request):
    # Check if this domain should show home page at root (e.g., example.edunade.com)
    if getattr(request, 'show_home_as_landing', False):
        # Redirect to home view logic for example.edunade.com
        return home(request)
    
    # Allow users to access landing page regardless of login status
    # The template will handle showing "Open!" vs "Login" button
    return render(request, 'landing.html')

def success(request):
    # Check if user should be upgraded to premium after successful payment
    current_email = request.session.get('email', '')
    user_was_upgraded = False
    
    if current_email and request.session.get('already_registered', False):
        try:
            # Get user data to find their customer_id
            user_data = Users.objects.get(email=current_email)
            
            # Check if user is now a premium member
            try:
                premium_member = Premium_Members.objects.get(
                    customer_id=user_data.customer_id,
                    subscribed="Yes"
                )
                
                # If they are premium but session shows free, upgrade them
                current_user_type = request.session.get('user_type', 'free')
                if current_user_type != 'premium':
                    request.session['user_type'] = 'premium'
                    user_was_upgraded = True
                    logger.info(f"User {current_email} upgraded to premium in success page")
                    
            except Premium_Members.DoesNotExist:
                # User is not premium, keep current status
                pass
                
        except Users.DoesNotExist:
            # User not found, can't check premium status
            pass
    
    # Pass upgrade status to template for potential success message
    context = {
        'user_was_upgraded': user_was_upgraded
    }
    
    return render(request, 'success.html', context)

def success_trial(request):
    # Check if user should be upgraded to premium after successful trial payment
    current_email = request.session.get('email', '')
    user_was_upgraded = False
    
    if current_email and request.session.get('already_registered', False):
        try:
            # Get user data to find their customer_id
            user_data = Users.objects.get(email=current_email)
            
            # Check if user is now a premium member
            try:
                premium_member = Premium_Members.objects.get(
                    customer_id=user_data.customer_id,
                    subscribed="Yes"
                )
                
                # If they are premium but session shows free, upgrade them
                current_user_type = request.session.get('user_type', 'free')
                if current_user_type != 'premium':
                    request.session['user_type'] = 'premium'
                    user_was_upgraded = True
                    logger.info(f"User {current_email} upgraded to premium (trial) in success-trial page")
                    
            except Premium_Members.DoesNotExist:
                # User is not premium, keep current status
                pass
                
        except Users.DoesNotExist:
            # User not found, can't check premium status
            pass
    
    # Pass upgrade status to template for potential success message
    context = {
        'user_was_upgraded': user_was_upgraded
    }
    
    return render(request, 'success-trial.html', context)

@track_user_journey
def home(request):
    # logger.info(f"Home page accessed - User: {request.session.get('email', 'Anonymous')}")

    if request.GET.get('start_without_registering'):
        request.session['already_user'] = False
        request.session['updated_creds'] = False
        request.session['already_registered'] = False
        request.session['user_type'] = 'free'
        request.session['user_name'] = 'Guest'
        request.session['last_name'] = 'User'
        request.session['avatar'] = 'avatar1.png'
    
    # Fallback check: If user is logged in but session shows non-premium, check if they should be premium
    current_email = request.session.get('email', '')
    current_user_type = request.session.get('user_type', 'free')
    is_apex_user = request.session.get('is_apex_user', False)
    
    if (current_email and 
        request.session.get('already_registered', False) and 
        current_user_type in ['free', 'apex_user']):
        
        try:
            # Check for Apex users first
            if is_apex_user:
                apex_user = ApexUsers.objects.get(email=current_email)
                try:
                    Premium_Members.objects.get(
                        customer_id=apex_user.customer_id,
                        subscribed="Yes"
                    )
                    request.session['user_type'] = 'premium'
                    logger.info(f"Apex user {current_email} upgraded to premium in home page (fallback)")
                except Premium_Members.DoesNotExist:
                    pass
            else:
                # Regular user - get from Users table
                user_data = Users.objects.get(email=current_email)
                try:
                    Premium_Members.objects.get(
                        customer_id=user_data.customer_id,
                        subscribed="Yes"
                    )
                    request.session['user_type'] = 'premium'
                    logger.info(f"User {current_email} upgraded to premium in home page (fallback)")
                except Premium_Members.DoesNotExist:
                    pass
                
        except (Users.DoesNotExist, ApexUsers.DoesNotExist):
            # User not found, can't check premium status
            pass
    
    # Get active news announcements
    news_announcements = NewsAnnouncement.objects.filter(is_active=True).order_by('order', '-created_date')
    
    # Count questions for each subject
    math_ai_sl_count = Math_AI_SL_Questionbank.objects.count()
    math_ai_hl_count = Math_AI_HL_Questionbank.objects.count()
    math_aa_sl_count = Math_AA_SL_Questionbank.objects.count()
    math_aa_hl_count = Math_AA_HL_Questionbank.objects.count()
    comp_sci_sl_count = Comp_Sci_SL_Questionbank.objects.count()
    comp_sci_hl_count = Comp_Sci_HL_Questionbank.objects.count()
    biology_sl_count = Biology_SL_Questionbank.objects.count()
    biology_hl_count = Biology_HL_Questionbank.objects.count()
    
    # Get user's referral code and check premium status
    user_referral_code = None
    is_premium_user = False
    current_email = request.session.get('email', '')
    is_apex_user = request.session.get('is_apex_user', False)
    
    if current_email:
        if is_apex_user:
            # Apex users don't have referral codes, but check premium status
            try:
                apex_user = ApexUsers.objects.get(email=current_email)
                try:
                    Premium_Members.objects.get(customer_id=apex_user.customer_id, subscribed="Yes")
                    is_premium_user = True
                except Premium_Members.DoesNotExist:
                    is_premium_user = False
            except ApexUsers.DoesNotExist:
                pass
        else:
            try:
                user = Users.objects.get(email=current_email)
                user_referral_code = user.referral_code
                
                # Check if user is premium
                try:
                    Premium_Members.objects.get(customer_id=user.customer_id, subscribed="Yes")
                    is_premium_user = True
                except Premium_Members.DoesNotExist:
                    is_premium_user = False
            except Users.DoesNotExist:
                pass
    
    context = {
        'news_announcements': news_announcements,
        'math_ai_sl_count': math_ai_sl_count,
        'math_ai_hl_count': math_ai_hl_count,
        'math_aa_sl_count': math_aa_sl_count,
        'math_aa_hl_count': math_aa_hl_count,
        'comp_sci_sl_count': comp_sci_sl_count,
        'comp_sci_hl_count': comp_sci_hl_count,
        'biology_sl_count': biology_sl_count,
        'biology_hl_count': biology_hl_count,
        'user_referral_code': user_referral_code,
        'is_premium_user': is_premium_user,
    }
    
    return render(request, 'home.html', context)

def account(request):
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('firstName', '')
        last_name = request.POST.get('lastName', '')
        email = request.POST.get('email', '') or request.session.get('email', '')
        school_name = request.POST.get('organization', '')
        curriculum = request.POST.get('curriculum', '')
        exam_session = request.POST.get('exam_session', '')
        occupation = request.POST.get('occupation', '')
        avatar = request.POST.get('avatar', request.session.get('avatar', 'avatar1.png'))

        # Update user in the database
        current_email = request.session.get('email', '')
        is_apex_user = request.session.get('is_apex_user', False)
        current_occupation = request.session.get('occupation', '')
        
        try:
            if is_apex_user:
                # Update ApexUsers table
                user = ApexUsers.objects.get(email=current_email)
                user.first_name = first_name
                user.last_name = last_name
                if email and email != current_email:
                    user.email = email
                user.school_name = school_name
                user.curriculum = curriculum
                user.exam_session = exam_session
                # Don't allow AdminExternal users to change their occupation
                if current_occupation != 'AdminExternal':
                    user.occupation = occupation
                user.avatar = avatar
                user.save()
            else:
                # Update Users table
                user = Users.objects.get(email=current_email)
                user.first_name = first_name
                user.last_name = last_name
                if email and email != current_email:
                    user.email = email
                user.school_name = school_name
                user.curriculum = curriculum
                user.exam_session = exam_session
                user.occupation = occupation
                user.avatar = avatar
                user.save()
            
            # Update session data
            request.session['user_name'] = first_name
            request.session['last_name'] = last_name
            request.session['school_name'] = school_name
            request.session['curriculum'] = curriculum
            request.session['exam_session'] = exam_session
            # Keep AdminExternal occupation unchanged
            if current_occupation != 'AdminExternal':
                request.session['occupation'] = occupation
            request.session['avatar'] = avatar
            if email and email != current_email:
                request.session['email'] = email
            
        except (Users.DoesNotExist, ApexUsers.DoesNotExist):
            pass
        except Exception as e:
            pass
    
    # Get user's referral code usage status and premium status
    user_referral_code_used = None
    is_premium_user = False
    current_email = request.session.get('email', '')
    is_apex_user = request.session.get('is_apex_user', False)
    
    if current_email:
        try:
            if is_apex_user:
                # Apex users don't have referral codes
                apex_user = ApexUsers.objects.get(email=current_email)
                # Check if user is premium
                try:
                    Premium_Members.objects.get(customer_id=apex_user.customer_id, subscribed="Yes")
                    is_premium_user = True
                except Premium_Members.DoesNotExist:
                    is_premium_user = False
            else:
                user = Users.objects.get(email=current_email)
                user_referral_code_used = user.referral_code_used
                # Check if user is premium
                try:
                    Premium_Members.objects.get(customer_id=user.customer_id, subscribed="Yes")
                    is_premium_user = True
                except Premium_Members.DoesNotExist:
                    is_premium_user = False
        except (Users.DoesNotExist, ApexUsers.DoesNotExist):
            pass
            
    return render(request, 'account.html', {
        'user_referral_code_used': user_referral_code_used,
        'is_premium_user': is_premium_user
    })


@require_http_methods(["POST"])
def activate_referral_code(request):
    """View to activate a referral code and grant premium access"""
    if request.method == 'POST':
        referral_code = request.POST.get('referral_code', '').strip().upper()
        current_email = request.session.get('email', '')
        
        if not current_email:
            return JsonResponse({'success': False, 'error': 'You must be logged in to activate a referral code.'})
        
        if not referral_code:
            return JsonResponse({'success': False, 'error': 'Please enter a referral code.'})
        
        try:
            # Get current user
            current_user = Users.objects.get(email=current_email)
            
            # Check if user is already premium (must check FIRST before other validations)
            try:
                existing_premium = Premium_Members.objects.get(customer_id=current_user.customer_id, subscribed="Yes")
                return JsonResponse({'success': False, 'error': 'You are already a premium member and cannot use a referral code.'})
            except Premium_Members.DoesNotExist:
                pass
            
            # Check if user has already used a referral code
            if current_user.referral_code_used:
                return JsonResponse({'success': False, 'error': 'You have already activated a referral code.'})
            
            # Check if user is trying to use their own code
            if current_user.referral_code == referral_code:
                return JsonResponse({'success': False, 'error': 'You cannot use your own referral code.'})
            
            # Find the user who owns this referral code
            try:
                referrer = Users.objects.get(referral_code=referral_code)
            except Users.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Invalid referral code.'})
            
            # Calculate subscription end date (1 month from now)
            from datetime import timedelta
            subscription_end = timezone.now() + timedelta(days=30)
            
            # Add the current user (friend) to Premium_Members
            Premium_Members.objects.create(
                email=current_user.email,
                customer_id=current_user.customer_id,
                first_name=current_user.first_name,
                last_name=current_user.last_name,
                subscribed="Yes",
                stripe_customer_id="FREE",
                subscription_end_date=subscription_end
            )
            
            # Check if referrer is already premium
            try:
                referrer_premium = Premium_Members.objects.get(customer_id=referrer.customer_id, subscribed="Yes")
                # Referrer is already premium - extend their subscription by 1 month
                referrer_premium.subscription_end_date = referrer_premium.subscription_end_date + timedelta(days=30)
                referrer_premium.save()
            except Premium_Members.DoesNotExist:
                # Referrer is not premium - give them 1 month free
                Premium_Members.objects.create(
                    email=referrer.email,
                    customer_id=referrer.customer_id,
                    first_name=referrer.first_name,
                    last_name=referrer.last_name,
                    subscribed="Yes",
                    stripe_customer_id="FREE",
                    subscription_end_date=subscription_end
                )
            
            # Mark that this user used a referral code
            current_user.referral_code_used = referral_code
            current_user.save()
            
            # Update session to reflect premium status
            request.session['user_type'] = 'premium'
            
            return JsonResponse({
                'success': True,
                'message': 'Congratulations! You and your friend have both been granted 1 month of premium access.'
            })
            
        except Users.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


@require_POST
def send_referral_email(request):
    """View to send referral email to a friend"""
    friend_email = request.POST.get('friend_email', '').strip().lower()
    current_email = request.session.get('email', '')
    
    if not current_email:
        return JsonResponse({'success': False, 'error': 'You must be logged in to send referral emails.'})
    
    if not friend_email:
        return JsonResponse({'success': False, 'error': 'Please enter an email address.'})
    
    # Validate email format
    import re
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, friend_email):
        return JsonResponse({'success': False, 'error': 'Please enter a valid email address.'})
    
    try:
        # Get current user
        current_user = Users.objects.get(email=current_email)
        
        if not current_user.referral_code:
            return JsonResponse({'success': False, 'error': 'You do not have a referral code yet. Please refresh the page.'})
        
        # Check if trying to send to self
        if friend_email == current_email:
            return JsonResponse({'success': False, 'error': 'You cannot send a referral to yourself.'})
        
        # Send referral email
        try:
            subject = f"{current_user.first_name} invited you to join Edunade Academy!"
            context = {
                'sender_name': current_user.first_name,
                'referral_code': current_user.referral_code,
            }
            email_html_message = render_to_string('email/referral_invitation_email.html', context)
            
            from_email = 'Edunade Academy <{}>'.format(settings.DEFAULT_FROM_EMAIL)
            
            referral_email = EmailMultiAlternatives(
                subject=subject,
                body=f"Hi! {current_user.first_name} invited you to join Edunade Academy. Use referral code: {current_user.referral_code}",
                from_email=from_email,
                to=[friend_email]
            )
            referral_email.attach_alternative(email_html_message, "text/html")
            referral_email.send()
            
            return JsonResponse({
                'success': True,
                'message': 'Referral invitation sent successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Failed to send email: {str(e)}'})
            
    except Users.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})


def security(request):
    # Get recent login data for the current user
    current_email = request.session.get('email', '')
    recent_logins = []
    
    if current_email:
        # Get the last 5 User_Journey entries for this email, ordered by most recent first
        recent_logins = User_Journey.objects.filter(
            email=current_email
        ).order_by('-date_created')[:5]
    
    if request.method == 'POST':
        # Get form data
        current_password = request.POST.get('currentPassword', '')
        new_password = request.POST.get('newPassword', '')
        confirm_password = request.POST.get('confirmPassword', '')
        
        # Get current user's email from session
        if not current_email:
            # If no email in session, redirect to login
            return redirect('login')
        
        # Authenticate user with current password
        user = authenticate(username=current_email, password=current_password)
        
        if user is not None:
            # Current password is correct
            if new_password == confirm_password:
                password_errors = []
                
                if len(new_password) < 8:
                    password_errors.append("Password must be at least 8 characters long")
                
                if not any(c.isupper() for c in new_password):
                    password_errors.append("Password must contain at least one uppercase letter")
                
                if not any(c.isdigit() or not c.isalnum() for c in new_password):
                    password_errors.append("Password must contain at least one number or symbol")
                
                if password_errors:
                    # Password doesn't meet requirements
                    context = {
                        'error_message': '. '.join(password_errors) + '.',
                        'recent_logins': recent_logins,
                        'user_email': current_email
                    }
                    return render(request, 'security.html', context)
                else:
                    # Password meets all requirements
                    user.set_password(new_password)
                    user.save()
                    
                    # Re-authenticate the user with the new password to keep them logged in
                    updated_user = authenticate(username=current_email, password=new_password)
                    if updated_user is not None:
                        auth_login(request, updated_user)
                    
                    # Success message
                    context = {
                        'success_message': 'Password changed successfully! You are now logged in with your new password.',
                        'recent_logins': recent_logins,
                        'user_email': current_email
                    }
                    return render(request, 'security.html', context)
            else:
                # New passwords don't match
                context = {
                    'error_message': 'New password and confirmation do not match.',
                    'recent_logins': recent_logins,
                    'user_email': current_email
                }
                return render(request, 'security.html', context)
        else:
            # Current password is incorrect
            context = {
                'error_message': 'Current password is incorrect.',
                'recent_logins': recent_logins,
                'user_email': current_email
            }
            return render(request, 'security.html', context)
    
    # For GET requests, just show the page with recent logins
    context = {
        'recent_logins': recent_logins,
        'user_email': current_email
    }
    return render(request, 'security.html', context)


@require_POST
@csrf_exempt
def cancel_subscription(request):
    try:
        # Get the current user's stripe customer ID
        current_email = request.session.get('email', '')
        if not current_email:
            return JsonResponse({'error': 'User not logged in'}, status=401)
            
        try:
            user_data = Users.objects.get(email=current_email)
            premium_member = Premium_Members.objects.get(customer_id=user_data.customer_id)
            stripe_customer_id = premium_member.stripe_customer_id
        except (Users.DoesNotExist, Premium_Members.DoesNotExist):
            return JsonResponse({'error': 'User not found'}, status=404)

        # Initialize Stripe with your secret key
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Get customer's subscriptions
        subscriptions = stripe.Subscription.list(customer=stripe_customer_id)
        
        if not subscriptions.data:
            return JsonResponse({'error': 'No active subscription found'}, status=404)
            
        # Cancel the subscription at period end
        subscription = subscriptions.data[0]  # Get the first active subscription
        stripe.Subscription.modify(
            subscription.id,
            cancel_at_period_end=True
        )
        
        # Update the local database to reflect the cancellation
        premium_member.subscribed = "Cancelled"
        
        # For free trial users, adjust subscription_end_date to trial end (3 days from start)
        if premium_member.subscription_type == 'free_trial':
            from django.utils import timezone
            trial_end = premium_member.registration_date + timedelta(days=3)
            # Only adjust if they're still within the trial period
            if timezone.now() < trial_end:
                premium_member.subscription_end_date = trial_end
        
        premium_member.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Subscription will be cancelled at the end of the billing period',
            'end_date': premium_member.subscription_end_date.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@track_user_journey
def subscription(request):
    context = {}
    
    # Get user_type from context processor to determine plan display
    user_type = request.session.get('user_type', 'free') if request.session.get('already_registered', False) else 'none'
    
    # Get customer_id for Stripe links
    customer_id = None
    current_email = request.session.get('email', '')
    if current_email:
        try:
            user_data = Users.objects.get(email=current_email)
            customer_id = user_data.customer_id
        except Users.DoesNotExist:
            pass
    
    # Add customer_id to context
    context['customer_id'] = customer_id
    
    # Default subscription type (for determining pricing display)
    subscription_type = 'yearly'  # Default to yearly
    
    # If user is premium, fetch subscription details
    if user_type == 'premium':
        try:
            user_data = Users.objects.get(email=current_email)
            premium_member = Premium_Members.objects.get(customer_id=user_data.customer_id)
            
            # Check if this is a FREE premium membership (admin-granted)
            is_free_premium = premium_member.stripe_customer_id == "FREE"
            context['is_free_premium'] = is_free_premium
            
            # Get subscription type from database if available
            if premium_member.subscription_type and premium_member.subscription_type != 'none':
                subscription_type = premium_member.subscription_type
            else:
                # Fallback: determine subscription type based on duration
                if premium_member.registration_date and premium_member.subscription_end_date:
                    subscription_duration = (premium_member.subscription_end_date - premium_member.registration_date).days
                    # If subscription is around 30 days, it's monthly; if around 365 days, it's yearly
                    if subscription_duration <= 40:  # Allow some buffer for monthly (30 +/- 10 days)
                        subscription_type = 'monthly'
                    else:
                        subscription_type = 'yearly'
                else:
                    subscription_type = 'yearly'  # Default assumption
            
            # Get subscription dates and status
            subscription_start = premium_member.registration_date
            subscription_end = premium_member.subscription_end_date
            context['subscribed'] = premium_member.subscribed  # Can be "Yes", "No", or "Cancelled"

            if subscription_end:
                # Calculate days remaining
                from django.utils import timezone
                today = timezone.now()
                
                # Special handling for free trial
                if subscription_type == 'free_trial':
                    # Trial is 3 days, then converts to subscription
                    trial_end = subscription_start + timedelta(days=3)
                    
                    if today < trial_end:
                        # Still in trial period
                        trial_days_remaining = (trial_end - today).days
                        trial_days_elapsed = (today - subscription_start).days
                        
                        context.update({
                            'subscription_end_date': trial_end.strftime("%b %d, %Y"),
                            'days_remaining': trial_days_remaining,
                            'total_days': 3,
                            'days_elapsed': trial_days_elapsed + 1,
                            'progress_percentage': min((trial_days_elapsed / 3) * 100, 100),
                            'subscription_type': subscription_type,
                            'is_trial_active': True,
                        })
                    else:
                        # Trial ended, now showing full subscription
                        total_days = (subscription_end - subscription_start).days
                        days_remaining = (subscription_end - today).days
                        days_elapsed = total_days - days_remaining
                        
                        context.update({
                            'subscription_end_date': subscription_end.strftime("%b %d, %Y"),
                            'days_remaining': days_remaining,
                            'total_days': total_days + 1,
                            'days_elapsed': days_elapsed + 1,
                            'progress_percentage': min((days_elapsed / total_days) * 100, 100),
                            'subscription_type': 'yearly',  # After trial, it becomes yearly
                            'is_trial_active': False,
                        })
                else:
                    # Regular subscription (monthly/yearly)
                    if subscription_end > today:
                        total_days = (subscription_end - subscription_start).days
                        days_remaining = (subscription_end - today).days
               
                        days_elapsed = total_days - days_remaining
            
                        # Only fix the specific case where days_elapsed is -1
                        if days_elapsed == -1:
                            days_elapsed = 0
                        
                        # Adjust for user-friendly display: show 1-30 instead of 0-29
                        days_elapsed_display = days_elapsed + 1
                        total_days_display = total_days + 1
                        
                        progress_percentage = (days_elapsed / total_days) * 100 if total_days > 0 else 0
                    else:
                        # Subscription has expired
                        days_remaining = 0
                        total_days = (subscription_end - subscription_start).days
                        days_elapsed = total_days
                        
                        # Adjust for user-friendly display
                        days_elapsed_display = days_elapsed + 1
                        total_days_display = total_days + 1
                        
                        progress_percentage = 100
                    
                    # Format the subscription end date for display
                    formatted_end_date = subscription_end.strftime("%b %d, %Y")
                    
                    context.update({
                        'subscription_end_date': formatted_end_date,
                        'days_remaining': days_remaining,
                        'total_days': total_days_display,
                        'days_elapsed': days_elapsed_display,
                        'progress_percentage': min(progress_percentage, 100),  # Cap at 100%
                        'subscription_type': subscription_type,
                    })
            
        except (Users.DoesNotExist, Premium_Members.DoesNotExist):
            # If premium member data not found, use default values
            pass
    
    # Add subscription_type to context for all users (free users won't see pricing anyway)
    context['subscription_type'] = subscription_type
    
    return render(request, 'subscription.html', context)

@track_user_journey
def pricing(request):
    context = {}
    
    # Get user's subscription status if they are premium
    current_email = request.session.get('email', '')
    if current_email:
        try:
            user_data = Users.objects.get(email=current_email)
            premium_member = Premium_Members.objects.get(customer_id=user_data.customer_id)
            context['subscribed'] = premium_member.subscribed
            
            # Check if this is a FREE premium membership (admin-granted)
            is_free_premium = premium_member.stripe_customer_id == "FREE"
            context['is_free_premium'] = is_free_premium
        except (Users.DoesNotExist, Premium_Members.DoesNotExist):
            pass
    
    # Get user_type from context processor to determine current plan
    user_type = request.session.get('user_type', 'free') if request.session.get('already_registered', False) else 'none'
    
    # Get customer_id for Stripe links
    customer_id = None
    current_email = request.session.get('email', '')
    if current_email:
        try:
            user_data = Users.objects.get(email=current_email)
            customer_id = user_data.customer_id
        except Users.DoesNotExist:
            pass
    
    # Add variables to context
    context['user_type'] = user_type
    context['customer_id'] = customer_id
    
    return render(request, 'pricing.html', context)

@track_user_journey
def pricing2(request):
    """Test page for trial subscription feature"""
    context = {}
    
    # Get user's subscription status if they are premium
    current_email = request.session.get('email', '')
    if current_email:
        try:
            user_data = Users.objects.get(email=current_email)
            premium_member = Premium_Members.objects.get(customer_id=user_data.customer_id)
            context['subscribed'] = premium_member.subscribed
            
            # Check if this is a FREE premium membership (admin-granted)
            is_free_premium = premium_member.stripe_customer_id == "FREE"
            context['is_free_premium'] = is_free_premium
        except (Users.DoesNotExist, Premium_Members.DoesNotExist):
            pass
    
    # Get user_type from context processor to determine current plan
    user_type = request.session.get('user_type', 'free') if request.session.get('already_registered', False) else 'none'
    
    # Get customer_id for Stripe links
    customer_id = None
    current_email = request.session.get('email', '')
    if current_email:
        try:
            user_data = Users.objects.get(email=current_email)
            customer_id = user_data.customer_id
        except Users.DoesNotExist:
            pass
    
    # Add variables to context
    context['user_type'] = user_type
    context['customer_id'] = customer_id
    
    return render(request, 'pricing2.html', context)

def faq(request):
    return render(request, 'faq.html')

def data_processing_terms(request):
    return render(request, 'data_processing_terms.html')

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

@track_user_journey
def contact(request):
    success_message = None
    error_message = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not message:
            error_message = 'Please fill in all required fields.'
        else:
            # Email to Edunade team
            subject = f'Contact Form Submission from {name}'
            body = f'Name: {name}\nEmail: {email}\nPhone: {phone}\nMessage:\n{message}'
            try:
                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    ['contact@edunade.com'],
                    fail_silently=False,
                )
                # Confirmation email to user
                confirmation_subject = 'Thank you for contacting Edunade Academy'
                confirmation_body = f"""
                Dear {name},

                Thank you for reaching out to Edunade Academy! We have received your message and will get back to you within 24 hours.

                Best regards,\nMatt | Edunade Academy
                """
                send_mail(
                    confirmation_subject,
                    confirmation_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                success_message = 'Thank you for contacting us! We have received your message and will get back to you soon.'
            except BadHeaderError:
                error_message = 'Invalid header found. Please try again.'
            except Exception as e:
                error_message = f'An error occurred while sending your message: {str(e)}'

    context = {
        'success_message': success_message,
        'error_message': error_message,
    }
    return render(request, 'contact.html', context)


@track_user_journey
def tutoring(request):
    return render(request, 'tutoring.html')

@track_user_journey
def tutoring2(request):
    return render(request, 'tutoring2.html')


def _meta_pixel_context():
    from django.conf import settings
    return {'meta_pixel_id': getattr(settings, 'META_PIXEL_ID', 'YOUR_PIXEL_ID')}


def tutoring_landing(request):
    from .forms import TutoringLandingForm
    from .models import TutoringLead

    form = TutoringLandingForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        TutoringLead.objects.create(
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data.get('last_name', ''),
            email=form.cleaned_data['email'],
            phone=form.cleaned_data.get('phone', ''),
            ib_year=form.cleaned_data.get('ib_year', ''),
            subject=form.cleaned_data.get('subject', ''),
            message=form.cleaned_data.get('message', ''),
            utm_source=request.POST.get('utm_source', ''),
            utm_medium=request.POST.get('utm_medium', ''),
            utm_campaign=request.POST.get('utm_campaign', ''),
        )
        request.session['tutoring_lead_first_name'] = form.cleaned_data['first_name']
        return redirect('tutoring-landing-thank-you')

    context = {'form': form, **_meta_pixel_context()}
    return render(request, 'tutoring_landing.html', context)


def tutoring_landing_thank_you(request):
    first_name = request.session.pop('tutoring_lead_first_name', '')
    context = {'first_name': first_name, **_meta_pixel_context()}
    return render(request, 'tutoring_landing_thank_you.html', context)


def vimeo_test(request):
    return render(request, 'vimeo_test.html')

@track_user_journey
def questionbank(request):
    return render(request, 'questionbank.html')

@track_user_journey
def past_papers(request):
    return render(request, 'past_papers.html')

def questionpreview(request):
    return render(request, 'questionpreview.html')

def gpt(request):
    return render(request, 'gpt.html')

# def tour(request):
#     return render(request, 'tour.html')


def current_url_name(request):
    return {
        "current_url": request.resolver_match.url_name if request.resolver_match else ""
    }

@track_user_journey
def uni_database(request):
    # Get all universities from the database
    queryset = Uni_Database.objects.all()
    
    # Apply filters if provided in GET parameters
    program_name_filter = request.GET.get('program_name')
    uni_name_filters = request.GET.getlist('uni_name')  # Changed to getlist for multiple values
    country_filters = request.GET.getlist('country')  # Changed to getlist for multiple values
    city_filter = request.GET.get('city')
    min_tuition = request.GET.get('min_tuition')
    max_tuition = request.GET.get('max_tuition')
    min_ib = request.GET.get('min_ib')
    max_ib = request.GET.get('max_ib')
    discipline_filters = request.GET.getlist('discipline')  # Changed to getlist for multiple values

    if program_name_filter:
        queryset = queryset.filter(program_name__icontains=program_name_filter)
    if uni_name_filters:  # Changed to handle multiple universities
        # Create Q objects for each university and combine with OR
        from django.db.models import Q
        uni_q = Q()
        for uni_name in uni_name_filters:
            uni_q |= Q(uni_name__icontains=uni_name)
        queryset = queryset.filter(uni_q)
    if country_filters:  # Changed to handle multiple countries
        # Create Q objects for each country and combine with OR
        from django.db.models import Q
        country_q = Q()
        for country in country_filters:
            country_q |= Q(country__icontains=country)
        queryset = queryset.filter(country_q)
    if city_filter:
        queryset = queryset.filter(city__icontains=city_filter)
    if min_tuition:
        try:
            min_tuition = float(min_tuition)
            queryset = queryset.filter(tuition_fee_euro__gte=min_tuition)
        except ValueError:
            pass  # Ignore invalid tuition values
    if max_tuition:
        try:
            max_tuition = float(max_tuition)
            queryset = queryset.filter(tuition_fee_euro__lte=max_tuition)
        except ValueError:
            pass  # Ignore invalid tuition values
    if min_ib and max_ib:
        try:
            min_ib = int(min_ib)
            max_ib = int(max_ib)
            queryset = queryset.filter(ib_requirements__gte=min_ib, ib_requirements__lte=max_ib)
        except ValueError:
            pass  # Ignore invalid IB values
    if discipline_filters:  # Changed to handle multiple disciplines
        # Create Q objects for each discipline and combine with OR
        from django.db.models import Q
        discipline_q = Q()
        for discipline in discipline_filters:
            discipline_q |= Q(discipline__icontains=discipline)
        queryset = queryset.filter(discipline_q)

    # Order by Cambridge first, then UK universities, then by university name
    queryset = queryset.annotate(
        cambridge_priority=Case(
            When(uni_name__icontains='Cambridge', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        uk_priority=Case(
            When(country__icontains='United Kingdom', then=Value(1)),
            When(country__icontains='UK', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('-cambridge_priority', '-uk_priority', 'uni_name')

    # Pagination
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get unique values for filter dropdowns from the filtered queryset
    unique_countries = queryset.values_list('country', flat=True).distinct().order_by('country')
    unique_universities = queryset.values_list('uni_name', flat=True).distinct().order_by('uni_name')
    unique_disciplines = queryset.values_list('discipline', flat=True).distinct().order_by('discipline')

    context = {
        'page_obj': page_obj,
        'university_count': queryset.count(),
        'universities': page_obj.object_list,
        'unique_countries': unique_countries,
        'unique_universities': unique_universities, 
        'unique_disciplines': unique_disciplines,
        'user_type': request.session.get('user_type', 'free') if request.session.get('already_registered', False) else 'none',
        'already_registered': request.session.get('already_registered', False),
    }

    return render(request, 'uni_database.html', context)



########################################################
# WEBINARS
########################################################

@track_user_journey
def webinars(request):
    context = {
        'user_type': request.session.get('user_type', 'free') if request.session.get('already_registered', False) else 'none',
        'already_registered': request.session.get('already_registered', False),
    }
    
    return render(request, 'webinars.html', context)

@track_user_journey
def webinars_live(request):
    # Get all webinars
    webinars = Webinars_Live.objects.all()
    
    # Add end time (45 minutes after start) for calendar and check if webinar is past
    from datetime import timedelta
    webinar_list = []
    
    for webinar in webinars:
        webinar.webinar_end_date = webinar.webinar_date + timedelta(minutes=45)
        # Check if webinar is more than 2 hours past
        time_since_webinar = (timezone.now() - webinar.webinar_date).total_seconds() / 3600  # Convert to hours
        webinar.is_past_webinar = time_since_webinar > 2
        webinar_list.append(webinar)
    
    # Sort webinars: upcoming/current first (by date), then past webinars at the bottom (by date)
    webinar_list.sort(key=lambda w: (w.is_past_webinar, w.webinar_date))
    
    # Check if user is registered
    already_registered = request.session.get('already_registered', False)
    
    context = {
        'webinars': webinar_list,
        'user_type': request.session.get('user_type', 'free') if request.session.get('already_registered', False) else 'none',
        'already_registered': already_registered,
        'not_registered': not already_registered,  # Add the missing variable
    }
    return render(request, 'webinars_live.html', context)

def webinar_interview_preparation(request):
    return render(request, 'webinar_interview_preparation.html')

def webinar_cv(request):
    return render(request, 'webinar_cv.html')

def webinar_around_the_world(request):
    return render(request, 'webinar_around_the_world.html')

def webinar_suitability(request):
    return render(request, 'webinar_suit.html')

def webinar_application_portals(request):
    return render(request, 'webinar_application_portals.html')  

def webinar_ias_ees(request):
    return render(request, 'webinar_ias_ees.html')

def webinar_uni_docs(request):
    return render(request, 'webinar_uni_docs.html')

def webinar_personal_statement(request):
    return render(request, 'webinar_personal_statement.html')

def webinar_why_study_abroad(request):
    return render(request, 'webinar_why_study_abroad.html')

def webinar_surviving_a_degree(request):
    return render(request, 'webinar_surviving_a_degree.html')

def webinar_gap_year(request):
    return render(request, 'webinar_gap_year.html')


########################################################
# UNIVERSITY DOCUMENTS
########################################################

def pdf_viewer(request):
    """View for displaying PDF documents with card interface"""
    # Define available PDFs (you can expand this list)
    pdfs = [
        {
            'category': 'Personal Statement',
            'title': 'University of Cambridge',
            'description': 'Medicine',
            'file_path': '/static/website/images/Pitch Deck.pdf',
            'icon': 'fa-solid fa-file',
            'filter': 'ps'
        },
        {
            'title': 'OECD',
            'description': 'Young Associate',
            'file_path': '/static/website/images/Mateusz Kostrz.pdf',
            'icon': 'fas fa-user-tie',
            'category': 'Cover Letter',
            'filter': 'cover'
        },
        # Add more PDFs here as you upload them
        # {
        #     'title': 'Another Document',
        #     'description': 'Description of another document',
        #     'filename': 'another_doc.pdf',
        #     'file_path': '/static/website/images/another_doc.pdf',
        #     'icon': 'fas fa-file-pdf',
        #     'category': 'Educational'
        # },
    ]
    
    context = {
        'pdfs': pdfs,
        'page_title': 'PDF Document Viewer'
    }
    return render(request, 'pdf_viewer.html', context)



########################################################
# BASE CLASS FOR QUESTION BANK VIEWS
########################################################

class BaseQuestionBankListAPIView(generics.ListAPIView):
    """Base class for all question bank API views with common sorting logic"""
    
    def apply_custom_ordering(self, questions_data, user_logged_in, user_type):
        """Apply custom ordering based on user subscription status"""
        # Define difficulty order for sorting
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        
        # Separate questions by type
        free_questions = [q for q in questions_data if q['type'] == 'free']
        registered_questions = [q for q in questions_data if q['type'] == 'registered']
        premium_questions = [q for q in questions_data if q['type'] == 'premium']
        
        if not user_logged_in:
            # Non-registered users: free (easy first, then by ID) -> registered -> premium
            free_questions.sort(key=lambda x: (difficulty_order.get(x['difficulty'], 999), x['id']))
            ordered_questions = free_questions + registered_questions + premium_questions
        
        elif user_type == 'premium':
            # Premium users: all questions sorted by difficulty, then by ID
            all_questions = free_questions + registered_questions + premium_questions
            all_questions.sort(key=lambda x: (difficulty_order.get(x['difficulty'], 999), x['id']))
            ordered_questions = all_questions
        
        else:
            # Registered (free) users: accessible questions by difficulty and ID -> premium at bottom
            accessible_questions = free_questions + registered_questions
            accessible_questions.sort(key=lambda x: (difficulty_order.get(x['difficulty'], 999), x['id']))
            ordered_questions = accessible_questions + premium_questions
        
        return ordered_questions

########################################################
# MATH AI SL QUESTIONBANK
########################################################

class Math_AI_SL_QuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Math_AI_SL_QuestionsSerializer

    def get_queryset(self):
        queryset = Math_AI_SL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')  # <--- NEW
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            # Include questions where the chapter matches any of the three chapter fields
            from django.db.models import Q
            queryset = queryset.filter(
                Q(chapter=chapter) |
                Q(chapter2=chapter) |
                Q(chapter3=chapter)
            )

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            # Get user email from session
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.math_ai_sl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.math_ai_sl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    # Determine which IDs to filter by
                    if intersection == 'true':
                        # Intersection: questions that are both completed AND marked
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        # Only completed
                        target_ids = completed_ids
                    elif marked == 'true':
                        # Only marked
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        # Apply progress filter to the already-filtered queryset
                        # This preserves any existing difficulty, paper, and chapter filters
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        # If no target questions, return empty queryset
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    # If no progress record, return empty queryset
                    queryset = queryset.none()
            else:
                # If not logged in, return empty queryset
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = self.request.GET.get('chapter')
        
        # Get available papers for this chapter (or all if no chapter specified)
        if chapter:
            from django.db.models import Q
            chapter_filter = Q(chapter=chapter) | Q(chapter2=chapter) | Q(chapter3=chapter)
            available_papers_qs = Math_AI_SL_Questionbank.objects.filter(
                chapter_filter
            ).values_list('paper', flat=True).distinct().order_by('paper')
            available_difficulties_qs = Math_AI_SL_Questionbank.objects.filter(
                chapter_filter
            ).values_list('difficulty', flat=True).distinct().order_by('difficulty')
        else:
            available_papers_qs = Math_AI_SL_Questionbank.objects.values_list(
                'paper', flat=True
            ).distinct().order_by('paper')
            available_difficulties_qs = Math_AI_SL_Questionbank.objects.values_list(
                'difficulty', flat=True
            ).distinct().order_by('difficulty')
        
        available_papers = list(available_papers_qs)
        
        # Sort difficulties in the correct order (Easy, Medium, Hard)
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        available_difficulties = sorted(list(available_difficulties_qs), 
                                      key=lambda x: difficulty_order.get(x, 999))
        
        # Get user subscription status from session
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'none') if user_logged_in else 'none'
        
        # Serialize the questions
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all AI SL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })

def render_math_topic(request, template_name, chapter, topic_title, subject, db_name, pdf_name=None, pdf_title=None):
    """
    Generic view to render math topic templates with chapter parameter
    """
    # Get user object if logged in (check both Users and ApexUsers)
    user = None
    if request.session.get('already_registered', False):
        user_email = request.session.get('email', '')
        is_apex_user = request.session.get('is_apex_user', False)
        
        if is_apex_user:
            try:
                user = ApexUsers.objects.get(email=user_email)
            except ApexUsers.DoesNotExist:
                pass
        else:
            try:
                user = Users.objects.get(email=user_email)
            except Users.DoesNotExist:
                pass
    
    context = {
        'chapter': chapter,
        'topic_title': topic_title,
        'subject': subject,
        'db_name': db_name,
        'pdf_name': pdf_name,
        'pdf_title': pdf_title,
        'already_registered': request.session.get('already_registered', False),
        'user_logged_in': request.session.get('already_registered', False),
        'user_type': request.session.get('user_type', 'free') if request.session.get('already_registered', False) else 'none',
        'user': user,  # Add user object to context
    }
    return render(request, template_name, context)


@track_user_journey
def systems_lin_eq_ai_sl(request):
    return render_math_topic(request, 'systems_lin_eq.html', 'systems_lin_eq', 'Systems of Linear Equations', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def number_skills_ai_sl(request):
    return render_math_topic(request, 'number_skills_ai_sl.html', 'number_skills', 'Number Skills', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def seq_series_ai_sl(request):
    return render_math_topic(request, 'seq_series_ai_sl.html', 'seq_series', 'Sequences, Series, Financial Mathematics', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def lin_eq_graphs_ai_sl(request):
    return render_math_topic(request, 'lin_eq_graphs_ai_sl.html', 'lin_eq_graphs', 'Linear Equations & Graphs', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def hypothesis_testing_ai_sl(request):
    return render_math_topic(request, 'hypothesis_testing_ai_sl.html', 'hypothesis_testing', 'Hypothesis Testing', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def trigonometry_ai_sl(request):
    return render_math_topic(request, 'trigonometry_ai_sl.html', 'trigonometry', 'Trigonometry', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def applications_of_functions_ai_sl(request):
    return render_math_topic(request, 'applications_of_functions_ai_sl.html', 'applications_of_functions', 'Applications of Functions', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def voronoi_diagrams_ai_sl(request):
    return render_math_topic(request, 'voronoi_diagrams_ai_sl.html', 'voronoi_diagrams', 'Voronoi Diagrams', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def probability_ai_sl(request):
    return render_math_topic(request, 'probability_ai_sl.html', 'probability', 'Probability', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def properties_of_functions_ai_sl(request):
    return render_math_topic(request, 'properties_of_functions_ai_sl.html', 'properties_of_functions', 'Properties of Functions', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def integration_ai_sl(request):
    return render_math_topic(request, 'integration_ai_sl.html', 'integration', 'Integration', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def distributions_ai_sl(request):
    return render_math_topic(request, 'distributions_ai_sl.html', 'distributions', 'Distributions', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def geometry_shapes_ai_sl(request):
    return render_math_topic(request, 'geometry_shapes_ai_sl.html', 'geometry_shapes', 'Geometry of 3D Shapes', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def descriptive_stats_ai_sl(request):
    return render_math_topic(request, 'descriptive_stats_ai_sl.html', 'descriptive_stats', 'Descriptive Statistics', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def differentiation_ai_sl(request):
    return render_math_topic(request, 'differentiation_ai_sl.html', 'differentiation', 'Differentiation', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def bivariate_statistics_ai_sl(request):
    return render_math_topic(request, 'bivariate_statistics_ai_sl.html', 'bivariate_statistics', 'Bivariate Statistics', 'Math AI SL', 'math-ai-sl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')


@track_user_journey
def math_ai_sl(request):
    return render(request, 'math_ai_sl.html')

########################################################
# MATH AI SL PAST PAPERS
########################################################

@track_user_journey
def math_ai_sl_past_papers(request):
    return render(request, 'math_ai_sl_past_papers.html')

def render_past_papers_videos(request, db_name, page_name, session, time_zone, paper):
    """
    Render past papers videos with tiered access based on access_level field:
    - free: Available to all users (including anonymous)
    - registered: Registered users only
    - premium: Premium users only
    """

    if "Nov" in session and "November" not in session:
        session = session.replace("Nov", "November")

    videos = db_name.objects.filter(
        session=session,
        time_zone=time_zone,
        paper=paper
    ).annotate(question_int=Cast('question', IntegerField())).order_by('question_int')
    
    # Convert to list to enable indexing
    videos_list = list(videos)
    total_videos = len(videos_list)

    
    # Get user status
    is_authenticated = request.session.get('already_registered', False)
    # Get user_type from session (same logic as context processor)
    user_type = request.session.get('user_type', 'free') if request.session.get('already_registered', False) else 'none'
    
    # Use the access_level field from database instead of calculating
    for video in videos_list:
        # Get access level from database (default to 'premium' if not set)
        video.access_tier = getattr(video, 'access_level', 'premium')
        
        # Determine if user can access this video
        if video.access_tier == 'free':
            video.user_can_access = True
        elif video.access_tier == 'registered':
            video.user_can_access = is_authenticated
        elif video.access_tier == 'premium':
            video.user_can_access = user_type in ['premium', 'admin']
        
        # Format session names for display (Nov -> November for individual videos)
        if 'Nov ' in video.session and 'November' not in video.session:
            video.formatted_session = video.session.replace('Nov ', 'November ')
        else:
            video.formatted_session = video.session
    
    session_parts = session.split()
    if len(session_parts) == 2:
        month, year = session_parts
        month_code = "M" if month == "May" else "N"  # May = M, November = N
        year_short = year[-2:]  # Last 2 digits of year
        session_short = f"{month_code}{year_short}"
    else:
        session_short = session.replace(" ", "").upper()
    
    # Create dynamic title (e.g., "M24TZ1P1")
    dynamic_title = f"{session_short}TZ{time_zone}P{paper}"
    
    # Create dynamic exam description (e.g., "May 2024 TZ1 P1") - ensure November is displayed
    if 'Nov ' in session and 'November' not in session:
        display_session = session.replace('Nov ', 'November ')
    else:
        display_session = session
    dynamic_exam = f"{display_session} TZ{time_zone} P{paper}"
    
    context = {
        'videos': videos_list,
        'session': display_session,
        'time_zone': time_zone,
        'paper': paper,
        'dynamic_title': dynamic_title,
        'dynamic_exam': dynamic_exam,
        'total_videos': total_videos,
    }
    return render(request, page_name, context) 


def math_ai_sl_may25tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may25tz1p1.html', "May 2025", "1", "1")

def math_ai_sl_may25tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may25tz1p2.html', "May 2025", "1", "2")

def math_ai_sl_may24tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may24tz1p1.html', "May 2024", "1", "1")

def math_ai_sl_may24tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may24tz1p2.html', "May 2024", "1", "2")

def math_ai_sl_may23tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may23tz1p1.html', "May 2023", "1", "1")

def math_ai_sl_may23tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may23tz1p2.html', "May 2023", "1", "2")

def math_ai_sl_may23tz2p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may23tz2p1.html', "May 2023", "2", "1")

def math_ai_sl_may23tz2p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may23tz2p2.html', "May 2023", "2", "2")

def math_ai_sl_may23tz2p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may23tz2p2.html', "May 2023", "2", "2")

def math_ai_sl_nov23tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_nov23tz1p1.html', "November 2023", "1", "1")

def math_ai_sl_nov23tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_nov23tz1p1.html', "November 2023", "1", "2")

def math_ai_sl_may22tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may22tz1p1.html', "May 2022", "1", "1")

def math_ai_sl_may22tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may22tz1p2.html', "May 2022", "1", "2")

def math_ai_sl_may21tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may21tz1p1.html', "May 2021", "1", "1")

def math_ai_sl_may21tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may21tz1p2.html', "May 2021", "1", "2")

def math_ai_sl_may21tz2p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may21tz2p1.html', "May 2021", "2", "1")

def math_ai_sl_may21tz2p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_may21tz2p2.html', "May 2021", "2", "2")

def math_ai_sl_nov21tz0p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_nov21tz0p1.html', "November 2021", "0", "1")

def math_ai_sl_nov21tz0p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos, 'math_ai_sl_nov21tz0p2.html', "November 2021", "0", "2")


########################################################
# MATH AI SL PAST PAPERS PDF GENERATOR
########################################################

@track_user_journey
def math_ai_sl_pdf_generator(request):
    """View for the PDF generator page - now supports all math subjects"""
    # No need to pass chapters - they're now in JavaScript
    return render(request, 'past_papers_pdf/math_ai_sl_pdf_generator.html')


@csrf_exempt
def math_ai_sl_generate_pdf(request):
    """Generate PDF with question screenshots for a specific subject, chapter, and paper"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Image, PageBreak, Spacer, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from io import BytesIO
    import requests
    from PIL import Image as PILImage
    import logging
    import random
    logger = logging.getLogger(__name__)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
    # Check if user has access (Premium, Tutor, or Admin)
    user_logged_in = request.session.get("already_registered", False)
    user_type = request.session.get("user_type", "free")
    user_email = request.session.get("email")
    is_apex_user = request.session.get("is_apex_user", False)
    
    # Debug logging
    logger.info(f"PDF Generation Request - Logged in: {user_logged_in}, User type: {user_type}, Email: {user_email}, Is Apex: {is_apex_user}")
    
    has_access = False
    is_tutor = False
    is_admin = False
    user = None
    
    if user_logged_in and user_email:
        # Check if Apex user with premium access
        if is_apex_user and user_type == 'premium':
            has_access = True
            logger.info(f"Apex premium user granted access")
        else:
            # Check regular Users table
            try:
                user = Users.objects.get(email=user_email)
                is_tutor = user.occupation and user.occupation.lower() == 'tutor'
                is_admin = user.occupation and user.occupation.lower() == 'admin'
                logger.info(f"User found - Occupation: {user.occupation}, Is Tutor: {is_tutor}, Is Admin: {is_admin}")
                has_access = user_type == 'premium' or is_tutor or is_admin
            except Users.DoesNotExist:
                logger.warning(f"User not found for email: {user_email}")
                pass
    
    logger.info(f"Has access: {has_access}")
    
    if not has_access:
        debug_info = {
            'user_logged_in': user_logged_in,
            'user_type': user_type,
            'user_email': user_email,
            'is_apex_user': is_apex_user,
            'occupation': user.occupation if user else 'N/A',
            'is_tutor': is_tutor,
            'is_admin': is_admin,
        }
        return JsonResponse({
            'error': 'You must be a Premium member, Tutor, or Admin to generate PDFs',
            'debug': debug_info
        }, status=403)
    
    try:
        data = json.loads(request.body)
        subject = data.get('subject')
        chapters = data.get('chapters', [])  # Now expects a list of chapters
        paper = data.get('paper')
        question_limit = data.get('question_limit', 50)  # Default to 50 if not provided
        markscheme_mode = data.get('markscheme_mode', 'questions_only')
        # Backwards compatibility
        if 'include_markschemes' in data and not data.get('markscheme_mode'):
            markscheme_mode = 'include_both' if data.get('include_markschemes') else 'questions_only'
        include_videos = data.get('include_videos', 'all')
        
        # Backwards compatibility: if 'chapter' is sent instead of 'chapters'
        if not chapters and data.get('chapter'):
            chapters = [data.get('chapter')]
        
        if not subject or not chapters or not paper:
            return JsonResponse({'error': 'Subject, chapters, and paper are required'}, status=400)
        
        # Map subject to model and get chapters
        subject_model_map = {
            'ai_sl': (Past_Paper_Videos, Past_Paper_Videos.CHAPTERS),
            'ai_hl': (Past_Paper_Videos_AI_HL, Past_Paper_Videos_AI_HL.CHAPTERS),
            'aa_sl': (Past_Paper_Videos_AA_SL, Past_Paper_Videos_AA_SL.CHAPTERS),
            'aa_hl': (Past_Paper_Videos_AA_HL, Past_Paper_Videos_AA_HL.CHAPTERS),
            'physics_sl': (Past_Paper_Videos_Physics_SL, Past_Paper_Videos_Physics_SL.CHAPTERS),
            'physics_hl': (Past_Paper_Videos_Physics_HL, Past_Paper_Videos_Physics_HL.CHAPTERS),
        }
        
        if subject not in subject_model_map:
            return JsonResponse({'error': f'Invalid subject: {subject}'}, status=400)
        
        Model, CHAPTERS = subject_model_map[subject]
        
        # Get chapter display names
        chapters_dict = dict(CHAPTERS)
        chapter_names = [chapters_dict.get(ch, ch) for ch in chapters]
        chapter_names_str = ', '.join(chapter_names)
        
        # Build filter query for chapters (OR logic for multiple chapters)
        chapter_filters = Q()
        for chapter in chapters:
            chapter_filters |= Q(topic1=chapter) | Q(topic2=chapter) | Q(topic3=chapter)
        
        # Build filter query for paper
        # For Physics subjects, Paper 1A should also include Paper 1 questions
        is_physics = subject in ['physics_sl', 'physics_hl']
        if paper == 'all':
            paper_filter = Q()  # No filter for "all"
        elif paper == '1A' and is_physics:
            # Combine Paper 1 and Paper 1A for physics
            paper_filter = Q(paper='1') | Q(paper='1A')
        else:
            paper_filter = Q(paper=paper)
        
        # Get all videos for these chapters and paper
        all_videos = list(Model.objects.filter(
            chapter_filters & paper_filter
        ).exclude(
            Q(question_screenshots_url__isnull=True) | Q(question_screenshots_url='')
        ))
        
        # Optional filter by whether videos exist
        if include_videos in ['with_videos', 'without_videos']:
            filtered_videos = []
            for video in all_videos:
                link_value = (video.link or '').strip().lower()
                has_video = link_value not in ['', 'none', 'null']
                if include_videos == 'with_videos' and has_video:
                    filtered_videos.append(video)
                elif include_videos == 'without_videos' and not has_video:
                    filtered_videos.append(video)
            all_videos = filtered_videos
        
        # Shuffle for true randomization
        random.shuffle(all_videos)
        
        # Limit the number of questions
        videos = all_videos[:question_limit]
        
        if not videos:
            paper_text = f"Paper {paper}" if paper != 'all' else "All Papers"
            return JsonResponse({
                'error': f'No videos with screenshots found for {chapter_names_str} - {paper_text}'
            }, status=404)
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        
        # Container for PDF elements
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
        
        session_style = ParagraphStyle(
            'SessionStyle',
            parent=styles['Heading2'],
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=20,
        )
        
        # Add title
        subject_names = {
            'ai_sl': 'Math AI SL',
            'ai_hl': 'Math AI HL',
            'aa_sl': 'Math AA SL',
            'aa_hl': 'Math AA HL',
            'physics_sl': 'Physics SL',
            'physics_hl': 'Physics HL',
        }
        subject_name = subject_names.get(subject, 'Subject')
        paper_text = "All Papers" if paper == 'all' else f"Paper {paper}"
        title_text = f"{subject_name} Past Papers - {paper_text}"
        if markscheme_mode in ['markscheme_only', 'include_both']:
            title_text += " (with Markscheme)"
        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 0.2*inch))

        # Process each video
        for video in videos:
            if not video.question_screenshots_url:
                continue
            
            # Split question URLs if multiple (comma-separated)
            question_urls = [url.strip() for url in video.question_screenshots_url.split(',') if url.strip()]
            
            # For now, markschemes are supported on Math AI SL (Past_Paper_Videos model)
            markscheme_urls = []
            if markscheme_mode in ['markscheme_only', 'include_both'] and hasattr(video, 'markscheme_screenshots_url') and video.markscheme_screenshots_url:
                markscheme_urls = [url.strip() for url in video.markscheme_screenshots_url.split(',') if url.strip()]
            
            # Order:
            # - questions_only: question pages only
            # - markscheme_only: markscheme pages only
            # - include_both: question pages then markscheme pages
            image_entries = []
            if markscheme_mode == 'questions_only':
                image_entries.extend([('Question', url) for url in question_urls])
            elif markscheme_mode == 'markscheme_only':
                image_entries.extend([('Markscheme', url) for url in markscheme_urls])
            else:  # include_both
                image_entries.extend([('Question', url) for url in question_urls])
                image_entries.extend([('Markscheme', url) for url in markscheme_urls])

            if not image_entries:
                continue
            
            for idx, (image_label, screenshot_url) in enumerate(image_entries):
                # Add session info on first image of each video
                if idx == 0:
                    session_text = f"{video.session} Time Zone {video.time_zone} Paper {video.paper} Question {video.question}"
                    elements.append(Paragraph(session_text, session_style))
                    elements.append(Spacer(1, 0.2*inch))
                elif image_label == 'Markscheme':
                    session_text = f"{video.session} Time Zone {video.time_zone} Paper {video.paper} Question {video.question} - Markscheme"
                    elements.append(Paragraph(session_text, session_style))
                    elements.append(Spacer(1, 0.2*inch))
                
                try:
                    # Download image from ImageKit
                    response = requests.get(screenshot_url, timeout=10)
                    response.raise_for_status()
                    
                    # Open image with PIL to get dimensions
                    img_data = BytesIO(response.content)
                    pil_img = PILImage.open(img_data)
                    img_width, img_height = pil_img.size
                    
                    # Calculate dimensions to fit on page
                    max_width = 7.5 * inch  # A4 width minus margins
                    max_height = 9.5 * inch  # A4 height minus margins
                    
                    # Calculate aspect ratio
                    aspect = img_height / float(img_width)
                    
                    if img_width > max_width:
                        img_width = max_width
                        img_height = img_width * aspect
                    
                    if img_height > max_height:
                        img_height = max_height
                        img_width = img_height / aspect
                    
                    # Reset BytesIO position
                    img_data.seek(0)
                    
                    # Add image to PDF
                    img = Image(img_data, width=img_width, height=img_height)
                    elements.append(img)
                    
                except Exception as e:
                    # If image fails, add error message
                    error_para = Paragraph(
                        f"Error loading image: {str(e)[:100]}",
                        styles['Normal']
                    )
                    elements.append(error_para)
                
                # Add page break after each image
                elements.append(PageBreak())
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Save the generated exam to database
        video_ids = [video.id for video in videos]
        from .models import GeneratedExamsPastPapers
        
        if user:
            # Regular user
            GeneratedExamsPastPapers.objects.create(
                user=user,
                subject=subject,
                chapters=chapters,
                paper=paper,
                question_limit=question_limit,
                question_ids=video_ids
            )
            logger.info(f"Saved generated exam for user {user.email}: {subject}, {len(video_ids)} questions")
        elif is_apex_user:
            # Apex user - get apex_user object and save
            try:
                apex_user_obj = ApexUsers.objects.get(email=user_email)
                GeneratedExamsPastPapers.objects.create(
                    apex_user=apex_user_obj,
                    subject=subject,
                    chapters=chapters,
                    paper=paper,
                    question_limit=question_limit,
                    question_ids=video_ids
                )
                logger.info(f"Saved generated exam for Apex user {apex_user_obj.email}: {subject}, {len(video_ids)} questions")
            except ApexUsers.DoesNotExist:
                logger.warning(f"Could not save exam - Apex user not found: {user_email}")
        
        # Create response with dynamic filename
        subject_names = {
            'ai_sl': 'Math_AI_SL',
            'ai_hl': 'Math_AI_HL',
            'aa_sl': 'Math_AA_SL',
            'aa_hl': 'Math_AA_HL',
            'physics_sl': 'Physics_SL',
            'physics_hl': 'Physics_HL',
        }
        subject_name = subject_names.get(subject, 'Subject')
        paper_text = f"Paper_{paper}" if paper != 'all' else "All_Papers"
        
        # Create a shortened filename for multiple chapters
        if len(chapters) == 1:
            chapter_filename = chapter_names[0].replace(' ', '_')
        else:
            chapter_filename = f"{len(chapters)}_Chapters"
        
        response = HttpResponse(pdf_data, content_type='application/pdf')
        filename = f"{subject_name}_{paper_text}_{chapter_filename}_Questions.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception("An unexpected error occurred during PDF generation")
        return JsonResponse({'error': str(e)}, status=500)


def get_saved_exams(request):
    """Get all saved exams for the current user"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_logged_in = request.session.get("already_registered", False)
    user_email = request.session.get("email")
    is_apex_user = request.session.get("is_apex_user", False)
    
    logger.info(f"get_saved_exams: email={user_email}, is_apex={is_apex_user}")
    
    if not user_logged_in or not user_email:
        return JsonResponse({'exams': []})
    
    try:
        from .models import GeneratedExamsPastPapers
        
        if is_apex_user:
            apex_user = ApexUsers.objects.get(email=user_email)
            logger.info(f"Apex user found: id={apex_user.id}")
            saved_exams = GeneratedExamsPastPapers.objects.filter(apex_user=apex_user).order_by('-created_at')[:20]
            logger.info(f"Found {saved_exams.count()} exams for apex user")
        else:
            user = Users.objects.get(email=user_email)
            saved_exams = GeneratedExamsPastPapers.objects.filter(user=user).order_by('-created_at')[:20]
        
        # Map subject to model for getting chapter names
        subject_model_map = {
            'ai_sl': (Past_Paper_Videos, Past_Paper_Videos.CHAPTERS),
            'ai_hl': (Past_Paper_Videos_AI_HL, Past_Paper_Videos_AI_HL.CHAPTERS),
            'aa_sl': (Past_Paper_Videos_AA_SL, Past_Paper_Videos_AA_SL.CHAPTERS),
            'aa_hl': (Past_Paper_Videos_AA_HL, Past_Paper_Videos_AA_HL.CHAPTERS),
            'physics_sl': (Past_Paper_Videos_Physics_SL, Past_Paper_Videos_Physics_SL.CHAPTERS),
            'physics_hl': (Past_Paper_Videos_Physics_HL, Past_Paper_Videos_Physics_HL.CHAPTERS),
        }
        
        exams_data = []
        for exam in saved_exams:
            # Get chapter display names
            chapter_names = []
            if exam.subject in subject_model_map:
                Model, CHAPTERS = subject_model_map[exam.subject]
                chapters_dict = dict(CHAPTERS)
                chapter_names = [chapters_dict.get(ch, ch) for ch in exam.chapters]
            
            exams_data.append({
                'id': exam.id,
                'subject': exam.get_subject_display(),
                'subject_code': exam.subject,
                'chapters': exam.chapters,
                'chapter_names': chapter_names,  # Add display names
                'paper': exam.paper,
                'question_count': len(exam.question_ids),
                'created_at': exam.created_at.strftime('%b %d, %Y %I:%M %p'),
                'timestamp': exam.created_at.timestamp()
            })
        
        return JsonResponse({'exams': exams_data})
    except Users.DoesNotExist:
        return JsonResponse({'exams': []})
    except Exception as e:
        logger.exception("Error fetching saved exams")
        return JsonResponse({'error': str(e)}, status=500)


def download_saved_exam(request, exam_id):
    """Regenerate and download a previously saved exam"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Image, PageBreak, Spacer, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from io import BytesIO
    import requests
    from PIL import Image as PILImage
    import logging
    
    logger = logging.getLogger(__name__)
    
    user_logged_in = request.session.get("already_registered", False)
    user_email = request.session.get("email")
    user_type = request.session.get("user_type", "free")
    is_apex_user = request.session.get("is_apex_user", False)
    
    if not user_logged_in or not user_email:
        return JsonResponse({'error': 'User not logged in'}, status=401)
    
    try:
        # Check access
        has_access = False
        user = None
        apex_user_obj = None
        
        if is_apex_user and user_type == 'premium':
            has_access = True
            apex_user_obj = ApexUsers.objects.get(email=user_email)
        else:
            user = Users.objects.get(email=user_email)
            is_tutor = user.occupation and user.occupation.lower() == 'tutor'
            is_admin = user.occupation and user.occupation.lower() == 'admin'
            has_access = user_type == 'premium' or is_tutor or is_admin
        
        if not has_access:
            return JsonResponse({'error': 'You must be a Premium member, Tutor, or Admin to download PDFs'}, status=403)
        
        from .models import GeneratedExamsPastPapers
        
        if is_apex_user:
            exam = GeneratedExamsPastPapers.objects.get(id=exam_id, apex_user=apex_user_obj)
        else:
            exam = GeneratedExamsPastPapers.objects.get(id=exam_id, user=user)
    except (Users.DoesNotExist, ApexUsers.DoesNotExist):
        return JsonResponse({'error': 'User not found'}, status=404)
    except GeneratedExamsPastPapers.DoesNotExist:
        return JsonResponse({'error': 'Exam not found'}, status=404)
    
    try:
        # Map subject to model
        subject_model_map = {
            'ai_sl': (Past_Paper_Videos, Past_Paper_Videos.CHAPTERS),
            'ai_hl': (Past_Paper_Videos_AI_HL, Past_Paper_Videos_AI_HL.CHAPTERS),
            'aa_sl': (Past_Paper_Videos_AA_SL, Past_Paper_Videos_AA_SL.CHAPTERS),
            'aa_hl': (Past_Paper_Videos_AA_HL, Past_Paper_Videos_AA_HL.CHAPTERS),
            'physics_sl': (Past_Paper_Videos_Physics_SL, Past_Paper_Videos_Physics_SL.CHAPTERS),
            'physics_hl': (Past_Paper_Videos_Physics_HL, Past_Paper_Videos_Physics_HL.CHAPTERS),
        }
        
        Model, CHAPTERS = subject_model_map[exam.subject]
        
        # Get the exact same videos using stored IDs
        videos = list(Model.objects.filter(id__in=exam.question_ids))
        
        # Sort videos to maintain the original order
        video_dict = {video.id: video for video in videos}
        videos = [video_dict[vid_id] for vid_id in exam.question_ids if vid_id in video_dict]
        
        if not videos:
            return JsonResponse({'error': 'No videos found for this exam'}, status=404)
        
        # Create PDF in memory (same logic as original generation)
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        
        elements = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
        
        session_style = ParagraphStyle(
            'SessionStyle',
            parent=styles['Heading2'],
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=20,
        )
        
        # Get chapter display names
        chapters_dict = dict(CHAPTERS)
        chapter_names = [chapters_dict.get(ch, ch) for ch in exam.chapters]
        chapter_names_str = ', '.join(chapter_names)
        
        # Add title
        subject_names = {
            'ai_sl': 'Math AI SL',
            'ai_hl': 'Math AI HL',
            'aa_sl': 'Math AA SL',
            'aa_hl': 'Math AA HL',
            'physics_sl': 'Physics SL',
            'physics_hl': 'Physics HL',
        }
        subject_name = subject_names.get(exam.subject, 'Subject')
        
        if len(exam.chapters) > 1:
            title_text = f"{subject_name} Past Papers - {len(exam.chapters)} Chapters"
        else:
            title_text = f"{subject_name} Past Papers - {chapter_names_str}"
        
        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Process each video (same as original)
        for video in videos:
            if not video.question_screenshots_url:
                continue
            
            screenshot_urls = [url.strip() for url in video.question_screenshots_url.split(',') if url.strip()]
            
            for idx, screenshot_url in enumerate(screenshot_urls):
                if idx == 0:
                    session_text = f"{video.session} Time Zone {video.time_zone} Paper {video.paper} Question {video.question}"
                    elements.append(Paragraph(session_text, session_style))
                    elements.append(Spacer(1, 0.2*inch))
                
                try:
                    response = requests.get(screenshot_url, timeout=10)
                    response.raise_for_status()
                    
                    img_data = BytesIO(response.content)
                    pil_img = PILImage.open(img_data)
                    img_width, img_height = pil_img.size
                    
                    max_width = 7.5 * inch
                    max_height = 9.5 * inch
                    aspect = img_height / float(img_width)
                    
                    if img_width > max_width:
                        img_width = max_width
                        img_height = img_width * aspect
                    
                    if img_height > max_height:
                        img_height = max_height
                        img_width = img_height / aspect
                    
                    img = Image(img_data, width=img_width, height=img_height)
                    elements.append(img)
                    elements.append(Spacer(1, 0.2*inch))
                    elements.append(PageBreak())
                    
                except Exception as e:
                    logger.error(f"Error processing image {screenshot_url}: {e}")
        
        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response
        paper_text = f"Paper_{exam.paper}" if exam.paper != 'all' else "All_Papers"
        chapter_filename = f"{len(exam.chapters)}_Chapters" if len(exam.chapters) > 1 else chapter_names[0].replace(' ', '_')
        filename = f"{subject_name.replace(' ', '_')}_{paper_text}_{chapter_filename}_Questions.pdf"
        
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.exception("Error downloading saved exam")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def delete_saved_exam(request, exam_id):
    """Delete a saved exam"""
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Only DELETE requests are allowed'}, status=405)

    user_logged_in = request.session.get("already_registered", False)
    user_email = request.session.get("email")
    is_apex_user = request.session.get("is_apex_user", False)
    
    logger.info(f"Delete exam request: exam_id={exam_id}, email={user_email}, is_apex={is_apex_user}")

    if not user_logged_in or not user_email:
        return JsonResponse({'error': 'User not logged in'}, status=401)

    try:
        from .models import GeneratedExamsPastPapers

        if is_apex_user:
            apex_user = ApexUsers.objects.get(email=user_email)
            logger.info(f"Found apex user: id={apex_user.id}, email={apex_user.email}")
            
            # Debug: check if exam exists at all
            all_exams = GeneratedExamsPastPapers.objects.filter(id=exam_id)
            if all_exams.exists():
                exam_record = all_exams.first()
                logger.info(f"Exam {exam_id} exists - user_id={exam_record.user_id}, apex_user_id={exam_record.apex_user_id}")
            else:
                logger.info(f"Exam {exam_id} does not exist at all")
            
            exam = GeneratedExamsPastPapers.objects.get(id=exam_id, apex_user=apex_user)
        else:
            user = Users.objects.get(email=user_email)
            exam = GeneratedExamsPastPapers.objects.get(id=exam_id, user=user)

        exam.delete()
        logger.info(f"Deleted exam {exam_id}")
        return JsonResponse({'success': True})
    except (Users.DoesNotExist, ApexUsers.DoesNotExist) as e:
        logger.error(f"User not found: {e}")
        return JsonResponse({'error': 'User not found'}, status=404)
    except GeneratedExamsPastPapers.DoesNotExist:
        logger.error(f"Exam not found: id={exam_id}, is_apex={is_apex_user}")
        return JsonResponse({'error': 'Exam not found', 'exam_id': exam_id, 'is_apex': is_apex_user}, status=404)
    except Exception as e:
        logger.exception("Error deleting saved exam")
        return JsonResponse({'error': str(e)}, status=500)


########################################################
# MATH AI SL PAST PAPERS TOPICS
########################################################

@track_user_journey
def math_ai_sl_past_papers_topics(request):
    return render(request, 'math_ai_sl_past_papers_topics.html')

def render_past_papers_videos_by_topic(request, page_name, topic):
    """
    Render past papers videos filtered by topic1, topic2, or topic3 fields
    Ordered by topic priority: topic1 first, then topic2, then topic3
    Within each topic group, ordered by ID (earliest IDs first)
    """
    from django.db.models import Case, When, IntegerField as IntField
    
    videos = Past_Paper_Videos.objects.filter(
        Q(topic1__iexact=topic) | Q(topic2__iexact=topic) | Q(topic3__iexact=topic)
    ).annotate(
        question_int=Cast('question', IntegerField()),
        topic_priority=Case(
            When(topic1__iexact=topic, then=1),
            When(topic2__iexact=topic, then=2),
            When(topic3__iexact=topic, then=3),
            default=4,
            output_field=IntField()
        )
    ).order_by('topic_priority', 'id')
    
    # Format session names for display (November -> Nov)
    for video in videos:
        video.formatted_session = video.session.replace('November', 'Nov')
    
    # Create dynamic context for topic-based pages
    context = {
        'videos': videos,
        'topic': topic,
        'dynamic_title': f"{topic} | Past Papers",
        'dynamic_exam': f"{topic} Past Papers",
        'total_questions': videos.count()
    }
    return render(request, page_name, context)

# def math_ai_sl_number_skills_videos(request):
#     return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_number_skills_videos.html', "Number Skills", "Number Skills", Past_Paper_Videos)

def math_ai_sl_number_skills_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_number_skills_videos.html', "number_skills", 'Number Skills', Past_Paper_Videos)

def math_ai_sl_seq_series_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_seq_series_videos.html', "seq_series", "Sequences, Series, Financial Mathematics", Past_Paper_Videos)

def math_ai_sl_systems_of_equations_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_systems_of_lin_eq_videos.html', "systems_of_equations", "Systems of Linear Equations", Past_Paper_Videos)

def math_ai_sl_lin_eq_graphs_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_lin_eq_graphs_videos.html', "linear_equations_graphs", "Linear Equations And Graphs", Past_Paper_Videos)

def math_ai_sl_application_of_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_application_of_functions_videos.html', "application_of_functions", "Application Of Functions", Past_Paper_Videos)

def math_ai_sl_properties_of_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_prop_of_func_videos.html', "properties_of_functions", "Properties Of Functions", Past_Paper_Videos)

def math_ai_sl_geometry_shapes_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_geometry_shapes_videos.html', "geometry_shapes", "Geometry Of 3D Shapes", Past_Paper_Videos)

def math_ai_sl_trigonometry_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_trigonometry_videos.html', "trigonometry", "Trigonometry", Past_Paper_Videos)

def math_ai_sl_voronoi_diagrams_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_voronoi_videos.html', "voronoi_diagrams", "Voronoi Diagrams", Past_Paper_Videos)

def math_ai_sl_descriptive_stats_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_desc_stats_videos.html', "descriptive_statistics", "Descriptive Statistics", Past_Paper_Videos)

def math_ai_sl_bivariate_statistics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_biv_stats_videos.html', "bivariate_statistics", "Bivariate Statistics", Past_Paper_Videos)

def math_ai_sl_probability_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_probability_videos.html', "probability", "Probability", Past_Paper_Videos)

def math_ai_sl_distributions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_distributions_videos.html', "distributions", "Distributions", Past_Paper_Videos)

def math_ai_sl_hypothesis_testing_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_hypothesis_videos.html', "hypothesis_testing", "Hypothesis Testing", Past_Paper_Videos)

def math_ai_sl_differentiation_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_differentiation_videos.html', "differentiation", "Differentiation", Past_Paper_Videos)

def math_ai_sl_integration_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_sl_integration_videos.html', "integration", "Integration", Past_Paper_Videos)



########################################################
# MATH AI HL QUESTIONBANK
########################################################
@track_user_journey
def math_ai_hl(request):
    return render(request, 'math_ai_hl.html')

class Math_AI_HL_QuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Math_AI_HL_QuestionsSerializer

    def get_queryset(self):
        queryset = Math_AI_HL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            # Include questions where the chapter matches any of the three chapter fields
            from django.db.models import Q
            queryset = queryset.filter(
                Q(chapter__iexact=chapter) | 
                Q(chapter2__iexact=chapter) | 
                Q(chapter3__iexact=chapter)
            )

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            # Get user email from session
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.math_ai_hl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.math_ai_hl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    # Determine which IDs to filter by
                    if intersection == 'true':
                        # Intersection: questions that are both completed AND marked
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        # Only completed
                        target_ids = completed_ids
                    elif marked == 'true':
                        # Only marked
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        # Apply progress filter to the already-filtered queryset
                        # This preserves any existing difficulty, paper, and chapter filters
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        # If no target questions, return empty queryset
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    # If no progress record, return empty queryset
                    queryset = queryset.none()
            else:
                # If not logged in, return empty queryset
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = self.request.GET.get('chapter')
        
        # Get available papers for this chapter (or all if no chapter specified)
        if chapter:
            from django.db.models import Q
            chapter_filter = Q(chapter__iexact=chapter) | Q(chapter2__iexact=chapter) | Q(chapter3__iexact=chapter)
            available_papers_qs = Math_AI_HL_Questionbank.objects.filter(
                chapter_filter
            ).values_list('paper', flat=True).distinct().order_by('paper')
            available_difficulties_qs = Math_AI_HL_Questionbank.objects.filter(
                chapter_filter
            ).values_list('difficulty', flat=True).distinct().order_by('difficulty')
        else:
            available_papers_qs = Math_AI_HL_Questionbank.objects.values_list(
                'paper', flat=True
            ).distinct().order_by('paper')
            available_difficulties_qs = Math_AI_HL_Questionbank.objects.values_list(
                'difficulty', flat=True
            ).distinct().order_by('difficulty')
        
        available_papers = list(available_papers_qs)
        
        # Sort difficulties in the correct order (Easy, Medium, Hard)
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        available_difficulties = sorted(list(available_difficulties_qs), 
                                      key=lambda x: difficulty_order.get(x, 999))
        
        # Get user subscription status from session
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'none') if user_logged_in else 'none'
        
        # Serialize the questions
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all AI HL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })


@track_user_journey
def number_skills_ai_hl(request):
    return render_math_topic(request, 'number_skills_ai_hl.html', 'number_skills', 'Number Skills', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def systems_lin_eq_ai_hl(request):
    return render_math_topic(request, 'systems_lin_eq_ai_hl.html', 'systems_lin_eq', 'Systems of Linear Equations', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def seq_series_ai_hl(request):
    return render_math_topic(request, 'seq_and_series_ai_hl.html', 'seq_series', 'Sequences, Series, Financial Mathematics', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def matrices_ai_hl(request):
    return render_math_topic(request, 'matrices_ai_hl.html', 'matrices', 'Matrices', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def distributions_ai_hl(request):
    return render_math_topic(request, 'distributions_ai_hl.html', 'distributions', 'Distributions', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def differentiation_ai_hl(request):
    return render_math_topic(request, 'differentiation_ai_hl.html', 'differentiation', 'Differentiation', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def complex_numbers_ai_hl(request):
    return render_math_topic(request, 'complex_numbers_ai_hl.html', 'complex_numbers', 'Complex Numbers', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def linear_equations_graphs_ai_hl(request):
    return render_math_topic(request, 'linear_equations_graphs_ai_hl.html', 'lin_eq_graphs', 'Linear Equations & Graphs', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def application_of_functions_ai_hl(request):
    return render_math_topic(request, 'application_of_functions_ai_hl.html', 'applications_of_functions', 'Application of Functions', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def properties_of_functions_ai_hl(request):
    return render_math_topic(request, 'properties_of_functions_ai_hl.html', 'properties_of_functions', 'Properties of Functions', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def function_transformations_ai_hl(request):
    return render_math_topic(request, 'function_transformations_ai_hl.html', 'function_transformations', 'Function Transformations', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def trigonometry_ai_hl(request):
    return render_math_topic(request, 'trigonometry_ai_hl.html', 'trigonometry', 'Trigonometry', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def trigonometric_functions_ai_hl(request):
    return render_math_topic(request, 'trigonometric_functions_ai_hl.html', 'trigonometric_functions', 'Trigonometric Functions', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def geometry_shapes_ai_hl(request):
    return render_math_topic(request, 'geometry_shapes_ai_hl.html', 'geometry_shapes', 'Geometry of 3D Shapes', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def voronoi_diagrams_ai_hl(request):
    return render_math_topic(request, 'voronoi_diagrams_ai_hl.html', 'voronoi_diagrams', 'Voronoi Diagrams', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def geometric_transformations_ai_hl(request):
    return render_math_topic(request, 'geometric_transformations_ai_hl.html', 'geometric_transformations', 'Geometric Transformations', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def vectors_ai_hl(request):
    return render_math_topic(request, 'vectors_ai_hl.html', 'vectors', 'Vectors', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def graph_theory_ai_hl(request):
    return render_math_topic(request, 'graph_theory_ai_hl.html', 'graph_theory', 'Graph Theory', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def descriptive_stats_ai_hl(request):
    return render_math_topic(request, 'descriptive_stats_ai_hl.html', 'descriptive_stats', 'Descriptive Statistics', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def bivariate_statistics_ai_hl(request):
    return render_math_topic(request, 'bivariate_statistics_ai_hl.html', 'bivariate_statistics', 'Bivariate Statistics', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def probability_ai_hl(request):
    return render_math_topic(request, 'probability_ai_hl.html', 'probability', 'Probability', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def hypothesis_testing_ai_hl(request):
    return render_math_topic(request, 'hypothesis_testing_ai_hl.html', 'hypothesis_testing', 'Hypothesis Testing', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def confidence_intervals_ai_hl(request):
    return render_math_topic(request, 'confidence_intervals_ai_hl.html', 'estimations_and_confidence_intervals', 'Confidence Intervals', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def integration_ai_hl(request):
    return render_math_topic(request, 'integration_ai_hl.html', 'integration', 'Integration', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def kinematics_ai_hl(request):
    return render_math_topic(request, 'kinematics_ai_hl.html', 'kinematics', 'Kinematics', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')

@track_user_journey
def differential_equation_ai_hl(request):
    return render_math_topic(request, 'differential_equation_ai_hl.html', 'differential_equations', 'Differential Equations', 'Math AI HL', 'math-ai-hl-questions', 'math_ai.pdf', 'Math AI Formula Booklet')


########################################################
# MATH AI HL PAST PAPERS
########################################################

@track_user_journey
def math_ai_hl_past_papers(request):
    return render(request, 'math_ai_hl_past_papers.html')

def math_ai_hl_may24tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_may24tz1p1.html', "May 2024", "1", "1")

def math_ai_hl_may24tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_may24tz1p2.html', "May 2024", "1", "2")

def math_ai_hl_may23tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_may23tz1p1.html', "May 2023", "1", "1")

def math_ai_hl_may23tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_may23tz1p2.html', "May 2023", "1", "2")

def math_ai_hl_may23tz2p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_may23tz2p1.html', "May 2023", "2", "1")

def math_ai_hl_may23tz2p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_may23tz2p2.html', "May 2023", "2", "2")

def math_ai_hl_may22tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_may22tz1p1.html', "May 2022", "1", "1")

def math_ai_hl_may22tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_may22tz1p2.html', "May 2022", "1", "2")

def math_ai_hl_nov23tz0p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_nov23tz0p1.html', "November 2023", "0", "1")

def math_ai_hl_nov23tz0p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_nov23tz0p2.html', "November 2023", "0", "2")

def math_ai_hl_nov22tz0p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_nov22tz0p1.html', "November 2022", "0", "1")

def math_ai_hl_nov22tz0p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_nov22tz0p2.html', "November 2022", "0", "2")

def math_ai_hl_may21tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_may21tz1p1.html', "May 2021", "1", "1")

def math_ai_hl_may21tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AI_HL, 'math_ai_hl_may21tz1p2.html', "May 2021", "1", "2")

########################################################
# MATH AI HL PAST PAPERS TOPICS
########################################################

@track_user_journey

def math_ai_hl_past_papers_topics(request):
    return render(request, 'math_ai_hl_past_papers_topics.html')


def render_past_papers_videos_by_topic_with_access_control(request, page_name, topic, topic_display, db_name):
    """
    Render past papers videos filtered by topic with access based on access_level field:
    - free: Available to all users (including anonymous)
    - registered: Registered users only
    - premium: Premium users only
    """
    from django.db.models import Case, When, IntegerField as IntField
    
    videos = db_name.objects.filter(
        Q(topic1__iexact=topic) | Q(topic2__iexact=topic) | Q(topic3__iexact=topic)
    ).annotate(
        question_int=Cast('question', IntegerField()),
        topic_priority=Case(
            When(topic1__iexact=topic, then=1),
            When(topic2__iexact=topic, then=2),
            When(topic3__iexact=topic, then=3),
            default=4,
            output_field=IntField()
        )
    ).order_by('topic_priority', 'id')
    
    # Convert to list to enable indexing
    videos_list = list(videos)
    total_videos = len(videos_list)

    # Get user status
    is_authenticated = request.session.get('already_registered', False)
    # Get user_type from session (same logic as context processor)
    user_type = request.session.get('user_type', 'free') if request.session.get('already_registered', False) else 'none'
    
    # Use the access_level field from database instead of calculating
    for video in videos_list:
        # Get access level from database (default to 'premium' if not set)
        video.access_tier = getattr(video, 'access_level', 'premium')
        
        # Determine if user can access this video
        if video.access_tier == 'free':
            video.user_can_access = True
        elif video.access_tier == 'registered':
            video.user_can_access = is_authenticated
        elif video.access_tier == 'premium':
            video.user_can_access = user_type in ['premium', 'admin']
        
        # Format session names for display (November -> Nov)
        if 'Nov ' in video.session and 'November' not in video.session:
            video.formatted_session = video.session.replace('Nov ', 'November ')
        else:
            video.formatted_session = video.session.replace('November', 'Nov')
    
    # Find the first accessible video for the main player
    first_accessible_video = None
    for video in videos_list:
        if video.user_can_access:
            first_accessible_video = video
            break
    
    # Create dynamic context for topic-based pages
    context = {
        'videos': videos_list,
        'first_accessible_video': first_accessible_video,
        'topic': topic_display,
        'dynamic_title': f"{topic_display}",
        'dynamic_exam': f"{topic_display} Past Papers",
        'total_questions': total_videos
    }
    return render(request, page_name, context)

def math_ai_hl_seq_series_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_ai_hl/math_ai_hl_seq_series_videos.html', "seq_series", 'Sequences, Series, Financial Mathematics', Past_Paper_Videos_AI_HL)

def math_ai_hl_complex_numbers_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_complex_numbers_videos.html', "complex_numbers", 'Complex Numbers', Past_Paper_Videos_AI_HL)

def math_ai_hl_matrices_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_matrices_videos.html', "matrices", 'Matrices', Past_Paper_Videos_AI_HL)

def math_ai_hl_systems_of_linear_equations_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_systems_of_linear_equations_videos.html', "systems_of_equations", 'Systems of Linear Equations', Past_Paper_Videos_AI_HL)

def math_ai_hl_linear_equations_graphs_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_linear_equations_graphs_videos.html', "linear_equations_graphs", 'Linear Equations & Graphs', Past_Paper_Videos_AI_HL)

def math_ai_hl_applications_of_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_ai_hl/math_ai_hl_applications_of_functions_videos.html', "application_of_functions", 'Application of Functions', Past_Paper_Videos_AI_HL)

def math_ai_hl_function_transformations_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_function_transformations_videos.html', "function_transformations", 'Function Transformations', Past_Paper_Videos_AI_HL)

def math_ai_hl_trigonometric_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_trigonometric_functions_videos.html', "trigonometric_functions", 'Trigonometric Functions', Past_Paper_Videos_AI_HL)

def math_ai_hl_trigonometry_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_trigonometry_videos.html', "trigonometry", 'Trigonometry', Past_Paper_Videos_AI_HL)

def math_ai_hl_voronoi_diagrams_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_voronoi_diagrams_videos.html', "voronoi_diagrams", 'Voronoi Diagrams', Past_Paper_Videos_AI_HL)

def math_ai_hl_geometric_transformations_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_geometric_transformations_videos.html', "geometric_transformations", 'Geometric Transformations', Past_Paper_Videos_AI_HL)

def math_ai_hl_vectors_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_vectors_videos.html', "vectors", 'Vectors', Past_Paper_Videos_AI_HL)

def math_ai_hl_graph_theory_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_graph_theory_videos.html', "graph_theory", 'Graph Theory', Past_Paper_Videos_AI_HL)

def math_ai_hl_descriptive_stats_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_descriptive_stats_videos.html', "descriptive_statistics", 'Descriptive Statistics', Past_Paper_Videos_AI_HL)

def math_ai_hl_bivariate_statistics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_bivariate_statistics_videos.html', "bivariate_statistics", 'Bivariate Statistics', Past_Paper_Videos_AI_HL)

def math_ai_hl_probability_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_probability_videos.html', "probability", 'Probability', Past_Paper_Videos_AI_HL)

def math_ai_hl_distributions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_distributions_videos.html', "distributions", 'Distributions', Past_Paper_Videos_AI_HL)

def math_ai_hl_geometry_shapes_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_geometry_shapes_videos.html', "geometry_shapes", 'Geometry of 3D Shapes', Past_Paper_Videos_AI_HL)

def math_ai_hl_hypothesis_testing_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_hypothesis_testing_videos.html', "hypothesis_testing", 'Hypothesis Testing', Past_Paper_Videos_AI_HL)

def math_ai_hl_confidence_intervals_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_confidence_intervals_videos.html', "confidence_intervals", 'Confidence Intervals', Past_Paper_Videos_AI_HL)

def math_ai_hl_differential_equation_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_differential_equation_videos.html', "differential_equations", 'Differential Equations', Past_Paper_Videos_AI_HL)

def math_ai_hl_kinematics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_kinematics_videos.html', "kinematics", 'Kinematics', Past_Paper_Videos_AI_HL)

def math_ai_hl_integration_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_integration_videos.html', "integration", 'Integration', Past_Paper_Videos_AI_HL)

def math_ai_hl_differentiation_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'math_ai_hl_differentiation_videos.html', "differentiation", 'Differentiation', Past_Paper_Videos_AI_HL)



########################################################
# MATH AA SL QUESTIONBANK
########################################################

class Math_AA_SL_QuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Math_AA_SL_QuestionsSerializer

    def get_queryset(self):
        queryset = Math_AA_SL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            # Include questions where the chapter matches any of the three chapter fields
            from django.db.models import Q
            queryset = queryset.filter(
                Q(chapter__iexact=chapter) | 
                Q(chapter2__iexact=chapter) | 
                Q(chapter3__iexact=chapter)
            )

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            # Get user email from session
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.math_aa_sl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.math_aa_sl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    # Determine which IDs to filter by
                    if intersection == 'true':
                        # Intersection: questions that are both completed AND marked
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        # Only completed
                        target_ids = completed_ids
                    elif marked == 'true':
                        # Only marked
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        # Apply progress filter to the already-filtered queryset
                        # This preserves any existing difficulty, paper, and chapter filters
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        # If no target questions, return empty queryset
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    # If no progress record, return empty queryset
                    queryset = queryset.none()
            else:
                # If not logged in, return empty queryset
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = self.request.GET.get('chapter')
        
        # Get available papers for this chapter (or all if no chapter specified)
        if chapter:
            from django.db.models import Q
            chapter_filter = Q(chapter__iexact=chapter) | Q(chapter2__iexact=chapter) | Q(chapter3__iexact=chapter)
            available_papers_qs = Math_AA_SL_Questionbank.objects.filter(
                chapter_filter
            ).values_list('paper', flat=True).distinct().order_by('paper')
            available_difficulties_qs = Math_AA_SL_Questionbank.objects.filter(
                chapter_filter
            ).values_list('difficulty', flat=True).distinct().order_by('difficulty')
        else:
            available_papers_qs = Math_AA_SL_Questionbank.objects.values_list(
                'paper', flat=True
            ).distinct().order_by('paper')
            available_difficulties_qs = Math_AA_SL_Questionbank.objects.values_list(
                'difficulty', flat=True
            ).distinct().order_by('difficulty')
        
        available_papers = list(available_papers_qs)
        
        # Sort difficulties in the correct order (Easy, Medium, Hard)
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        available_difficulties = sorted(list(available_difficulties_qs), 
                                      key=lambda x: difficulty_order.get(x, 999))
        
        # Get user subscription status from session
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'none') if user_logged_in else 'none'
        
        # Serialize the questions
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all AA SL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })

@track_user_journey
def seq_and_series_aa_sl(request):
    return render_math_topic(request, 'sequences_series_aa_sl.html', 'seq_series', 'Sequences, Series, Financial Mathematics', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def integration_aa_sl(request):
    return render_math_topic(request, 'integration_aa_sl.html', 'integration', 'Integral Calculus', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def kinematics_aa_sl(request):
    return render_math_topic(request, 'kinematics_aa_sl.html', 'kinematics', 'Kinematics', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def statistics_aa_sl(request):
    return render_math_topic(request, 'statistics_aa_sl.html', 'statistics', 'Statistics', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def trig_functions_aa_sl(request):
    return render_math_topic(request, 'trig_functions_aa_sl.html', 'trig_functions', 'Trigonometric Functions', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def properties_of_functions_aa_sl(request):
    return render_math_topic(request, 'properties_of_functions_aa_sl.html', 'properties_of_functions', 'Properties of Functions', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def quadratic_functions_aa_sl(request):
    return render_math_topic(request, 'quadratic_functions_aa_sl.html', 'quadratic_functions', 'Quadratic Functions', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def rational_functions_aa_sl(request):
    return render_math_topic(request, 'rational_functions_aa_sl.html', 'rational_functions', 'Rational Functions', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def probability_aa_sl(request):
    return render_math_topic(request, 'probability_aa_sl.html', 'probability', 'Probability', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def proofs_aa_sl(request):
    return render_math_topic(request, 'proofs_aa_sl.html', 'proofs', 'Proofs', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def geometry_aa_sl(request):
    return render_math_topic(request, 'geometry_aa_sl.html', 'geometry', 'Geometry', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def exp_and_logs_aa_sl(request):
    return render_math_topic(request, 'exp_and_logs_aa_sl.html', 'exp_and_logs', 'Exponentials and Logarithms', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def exp_and_logs_functions_aa_sl(request):
    return render_math_topic(request, 'exp_and_logs_functions_aa_sl.html', 'exp_and_logs_functions', 'Exponential and Logarithmic Functions', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def function_transformations_aa_sl(request):
    return render_math_topic(request, 'function_transformations_aa_sl.html', 'function_transformations', 'Function Transformations', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def differentiation_aa_sl(request):
    return render_math_topic(request, 'differentiation_aa_sl.html', 'differentiation', 'Differentiatial Calculus', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def distributions_aa_sl(request):
    return render_math_topic(request, 'distributions_aa_sl.html', 'distributions', 'Distributions', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def binomial_expansion_aa_sl(request):
    return render_math_topic(request, 'binomial_expansion_aa_sl.html', 'binomial_expansion', 'Binomial Expansion', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def bivariate_stats_aa_sl(request):
    return render_math_topic(request, 'bivariate_stats_aa_sl.html', 'bivariate_stats', 'Bivariate Statistics', 'Math AA SL', 'math-aa-sl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def math_aa_sl(request):
    return render(request, 'math_aa_sl.html')


########################################################
# MATH AA SL PAST PAPERS YEARS
########################################################

@track_user_journey
def math_aa_sl_past_papers(request):
    return render(request, 'math_aa_sl_past_papers.html')

def math_aa_sl_may24tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may24tz1p1.html', "May 2024", "1", "1")

def math_aa_sl_may24tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may24tz1p2.html', "May 2024", "1", "2")

def math_aa_sl_may24tz2p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may24tz2p1.html', "May 2024", "2", "1")

def math_aa_sl_may24tz2p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may24tz2p2.html', "May 2024", "2", "2")

def math_aa_sl_may23tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may23tz1p1.html', "May 2023", "1", "1")

def math_aa_sl_may23tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may23tz1p2.html', "May 2023", "1", "2")

def math_aa_sl_may23tz2p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may23tz2p1.html', "May 2023", "2", "1")

def math_aa_sl_may23tz2p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may23tz2p2.html', "May 2023", "2", "2")

def math_aa_sl_nov23tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_nov23tz1p1.html', "Nov 2023", "1", "1")

def math_aa_sl_nov23tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_nov23tz1p2.html', "Nov 2023", "1", "2")

def math_aa_sl_may22tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may22tz1p1.html', "May 2022", "1", "1")

def math_aa_sl_may22tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may22tz1p2.html', "May 2022", "1", "2")

def math_aa_sl_nov22tz0p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_nov22tz0p1.html', "Nov 2022", "0", "1")

def math_aa_sl_nov22tz0p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_nov22tz0p2.html', "November 2022", "0", "2")

def math_aa_sl_may21tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may21tz1p1.html', "May 2021", "1", "1")

def math_aa_sl_may21tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_may21tz1p2.html', "May 2021", "1", "2")

def math_aa_sl_nov21tz0p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_nov21tz0p1.html', "Nov 2021", "0", "1")

def math_aa_sl_nov21tz0p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_SL, 'math_aa_sl_nov21tz0p2.html', "Nov 2021", "0", "2")


########################################################
# MATH AA SL PAST PAPERS TOPICS
########################################################

@track_user_journey
def math_aa_sl_past_papers_topics(request):
    return render(request, 'math_aa_sl_past_papers_topics.html')

def math_aa_sl_seq_series_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_seq_series_videos.html', "seq_series", 'Sequences, Series, Financial Mathematics', Past_Paper_Videos_AA_SL)

def math_aa_sl_exponents_and_logs_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_exp_logs_videos.html', "exp_and_logs", 'Exponents and Logs', Past_Paper_Videos_AA_SL)

def math_aa_sl_binomial_expansion_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_binomial_videos.html', "binomial_expansion", 'Binomial Expansion', Past_Paper_Videos_AA_SL)

def math_aa_sl_proofs_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_proofs_videos.html', "proofs", 'Proofs', Past_Paper_Videos_AA_SL)

def math_aa_sl_properties_of_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_prop_func_videos.html', "properties_of_functions", 'Properties of Functions', Past_Paper_Videos_AA_SL)

def math_aa_sl_quadratic_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_quad_func_videos.html', "quadratic_functions", 'Quadratic Functions', Past_Paper_Videos_AA_SL)

def math_aa_sl_rational_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_rational_func_videos.html', "rational_functions", 'Rational Functions', Past_Paper_Videos_AA_SL)

def math_aa_sl_exp_and_logs_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_exp_logs_func_videos.html', "exp_and_logs_functions", 'Exponential and Logarithmic Functions', Past_Paper_Videos_AA_SL)

def math_aa_sl_function_transformations_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_func_transform_videos.html', "function_transformations", 'Function Transformations', Past_Paper_Videos_AA_SL)

def math_aa_sl_geometry_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_geometry_videos.html', "geometry", 'Geometry', Past_Paper_Videos_AA_SL)

def math_aa_sl_trigonometric_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_trig_videos.html', "trig_functions", 'Trigonometric Functions', Past_Paper_Videos_AA_SL)

def math_aa_sl_statistics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_stat_videos.html', "statistics", 'Statistics', Past_Paper_Videos_AA_SL)

def math_aa_sl_bivariate_statistics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_biv_stat_videos.html', "bivariate_stats", 'Bivariate Statistics', Past_Paper_Videos_AA_SL)

def math_aa_sl_probability_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_prob_videos.html', "probability", 'Probability', Past_Paper_Videos_AA_SL)

def math_aa_sl_distributions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_distributions_videos.html', "distributions", 'Distributions', Past_Paper_Videos_AA_SL)

def math_aa_sl_differential_calculus_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_differential_videos.html', "differential_calculus", 'Differential Calculus', Past_Paper_Videos_AA_SL)

def math_aa_sl_integral_calculus_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_integral_videos.html', "integral_calculus", 'Integral Calculus', Past_Paper_Videos_AA_SL)

def math_aa_sl_kinematics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_sl/math_aa_sl_kinematics_videos.html', "kinematics", 'Kinematics', Past_Paper_Videos_AA_SL)


########################################################
# MATH AA HL QUESTIONBANK
########################################################

class Math_AA_HL_QuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Math_AA_HL_QuestionsSerializer

    def get_queryset(self):
        queryset = Math_AA_HL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            # Include questions where the chapter matches any of the three chapter fields
            from django.db.models import Q
            queryset = queryset.filter(
                Q(chapter__iexact=chapter) | 
                Q(chapter2__iexact=chapter) | 
                Q(chapter3__iexact=chapter)
            )

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            # Get user email from session
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.math_aa_hl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.math_aa_hl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    # Determine which IDs to filter by
                    if intersection == 'true':
                        # Intersection: questions that are both completed AND marked
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        # Only completed
                        target_ids = completed_ids
                    elif marked == 'true':
                        # Only marked
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        # Apply progress filter to the already-filtered queryset
                        # This preserves any existing difficulty, paper, and chapter filters
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        # If no target questions, return empty queryset
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    # If no progress record, return empty queryset
                    queryset = queryset.none()
            else:
                # If not logged in, return empty queryset
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = self.request.GET.get('chapter')
        
        # Get available papers for this chapter (or all if no chapter specified)
        if chapter:
            from django.db.models import Q
            chapter_filter = Q(chapter__iexact=chapter) | Q(chapter2__iexact=chapter) | Q(chapter3__iexact=chapter)
            available_papers_qs = Math_AA_HL_Questionbank.objects.filter(
                chapter_filter
            ).values_list('paper', flat=True).distinct().order_by('paper')
            available_difficulties_qs = Math_AA_HL_Questionbank.objects.filter(
                chapter_filter
            ).values_list('difficulty', flat=True).distinct().order_by('difficulty')
        else:
            available_papers_qs = Math_AA_HL_Questionbank.objects.values_list(
                'paper', flat=True
            ).distinct().order_by('paper')
            available_difficulties_qs = Math_AA_HL_Questionbank.objects.values_list(
                'difficulty', flat=True
            ).distinct().order_by('difficulty')
        
        available_papers = list(available_papers_qs)
        
        # Sort difficulties in the correct order (Easy, Medium, Hard)
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        available_difficulties = sorted(list(available_difficulties_qs), 
                                      key=lambda x: difficulty_order.get(x, 999))
        
        # Get user subscription status from session
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'none') if user_logged_in else 'none'
        
        # Serialize the questions
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all AA SL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })


########################################################
# MATH AA HL BACKUP QUESTIONBANK
########################################################

class Math_AA_HL_Backup_QuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Math_AA_HL_Backup_QuestionsSerializer

    def get_queryset(self):
        queryset = Math_AA_HL_Questionbank_Backup.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            queryset = queryset.filter(chapter__iexact=chapter)

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = self.request.GET.get('chapter')
        
        # Get available papers for this chapter (or all if no chapter specified)
        if chapter:
            available_papers_qs = Math_AA_HL_Questionbank_Backup.objects.filter(
                chapter__iexact=chapter
            ).values_list('paper', flat=True).distinct().order_by('paper')
            available_difficulties_qs = Math_AA_HL_Questionbank_Backup.objects.filter(
                chapter__iexact=chapter
            ).values_list('difficulty', flat=True).distinct().order_by('difficulty')
        else:
            available_papers_qs = Math_AA_HL_Questionbank_Backup.objects.values_list(
                'paper', flat=True
            ).distinct().order_by('paper')
            available_difficulties_qs = Math_AA_HL_Questionbank_Backup.objects.values_list(
                'difficulty', flat=True
            ).distinct().order_by('difficulty')
        
        available_papers = list(available_papers_qs)
        
        # Sort difficulties in the correct order (Easy, Medium, Hard)
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        available_difficulties = sorted(list(available_difficulties_qs), 
                                      key=lambda x: difficulty_order.get(x, 999))
        
        # Get user subscription status from session
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'none') if user_logged_in else 'none'
        
        # Serialize the questions
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all AA HL backup chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })


@csrf_exempt
def delete_question_api(request):
    """API endpoint to delete questions"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        subject = data.get('subject')
        question_id = data.get('id')
        
        # Map subject to model
        model_mapping = {
            'math_ai_hl': Math_AI_HL_Questionbank,
            'math_ai_sl': Math_AI_SL_Questionbank,
            'math_aa_hl': Math_AA_HL_Questionbank,
            'math_aa_sl': Math_AA_SL_Questionbank,
            'biology_hl': Biology_HL_Questionbank,
            'biology_sl': Biology_SL_Questionbank,
            'physics_hl': Physics_HL_Questionbank,
            'physics_sl': Physics_SL_Questionbank,
        }
        
        if subject not in model_mapping:
            return JsonResponse({'success': False, 'message': 'Invalid subject'}, status=400)
        
        QuestionModel = model_mapping[subject]
        
        try:
            question = QuestionModel.objects.get(id=question_id)
            question.delete()
            return JsonResponse({
                'success': True,
                'message': 'Question deleted successfully'
            })
        except QuestionModel.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Question not found'}, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error deleting question: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Error deleting question: {str(e)}'}, status=500)

@csrf_exempt
def save_question_api(request):
    """API endpoint to save new questions"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Extract data from request
        subject = data.get('subject')
        chapter = data.get('chapter')
        paper = data.get('paper')
        difficulty = data.get('difficulty')
        type_value = data.get('type')
        question_text = data.get('question')
        answer_text = data.get('answer')
        marks = data.get('marks', 1)
        correct_answer = data.get('correct_answer')
        video_url = data.get('video')
        
        # Validation
        required_fields = ['subject', 'chapter', 'question', 'answer']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'success': False, 'message': f'{field.capitalize()} is required'}, status=400)
        
        # Map subject to model
        model_mapping = {
            'math_ai_hl': Math_AI_HL_Questionbank,
            'math_ai_sl': Math_AI_SL_Questionbank,
            'math_aa_hl': Math_AA_HL_Questionbank,
            'math_aa_sl': Math_AA_SL_Questionbank,
            'biology_hl': Biology_HL_Questionbank,
            'biology_sl': Biology_SL_Questionbank,
            'physics_hl': Physics_HL_Questionbank,
            'physics_sl': Physics_SL_Questionbank,
        }
        
        if subject not in model_mapping:
            return JsonResponse({'success': False, 'message': 'Invalid subject'}, status=400)
        
        QuestionModel = model_mapping[subject]
        
        # Create new question
        question_data = {
            'question': question_text,
            'answer': answer_text,
            'chapter': chapter,
            'paper': paper,
            'difficulty': difficulty,
            'type': type_value,
            'marks': marks,
            'video': video_url if video_url else ''
        }
        
        # Add correct_answer field only for models that have it
        if subject in ['biology_sl', 'biology_hl', 'physics_sl', 'physics_hl'] and correct_answer:
            question_data['correct_answer'] = correct_answer
            
        # Add chapter fields for Math AI SL
        if subject == 'math_ai_sl':
            question_data['chapter2'] = data.get('chapter2', '')
            question_data['chapter3'] = data.get('chapter3', '')
        
        new_question = QuestionModel.objects.create(**question_data)
        
        return JsonResponse({
            'success': True, 
            'message': 'Question saved successfully',
            'question_id': new_question.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error saving question: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Error saving question: {str(e)}'}, status=500)


@track_user_journey
def math_aa_hl(request):
    return render(request, 'math_aa_hl.html')

@track_user_journey
def seq_and_series_aa_hl(request):
    return render_math_topic(request, 'sequences_series_aa_hl.html', 'seq_series', 'Sequences, Series, Financial Mathematics', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def proofs_aa_hl(request):
    return render_math_topic(request, 'proofs_aa_hl.html', 'proofs', 'Proofs', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def exp_and_logs_aa_hl(request):
    return render_math_topic(request, 'exp_and_logs_aa_hl.html', 'exp_and_logs', 'Exponentials and Logarithms', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def binomial_expansion_aa_hl(request):
    return render_math_topic(request, 'binomial_expansion_aa_hl.html', 'binomial_expansion', 'Binomial Expansion', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def properties_of_functions_aa_hl(request):
    return render_math_topic(request, 'properties_of_functions_aa_hl.html', 'properties_of_functions', 'Properties of Functions', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def quadratic_functions_aa_hl(request):
    return render_math_topic(request, 'quadratic_functions_aa_hl.html', 'quadratic_functions', 'Quadratic Functions', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def counting_principles_aa_hl(request):
    return render_math_topic(request, 'counting_principles_aa_hl.html', 'counting_principles', 'Counting Principles', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def complex_numbers_aa_hl(request):
    return render_math_topic(request, 'complex_numbers_aa_hl.html', 'complex_numbers', 'Complex Numbers', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def systems_of_equations_aa_hl(request):
    return render_math_topic(request, 'systems_of_equations_aa_hl.html', 'systems_of_equations', 'Systems of Equations', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def geometry_aa_hl(request):
    return render_math_topic(request, 'geometry_aa_hl.html', 'geometry', 'Geometry', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def trig_functions_aa_hl(request):
    return render_math_topic(request, 'trig_functions_aa_hl.html', 'trig_functions', 'Trigonometric Functions', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def vectors_aa_hl(request):
    return render_math_topic(request, 'vectors_aa_hl.html', 'vectors', 'Vectors', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def rational_functions_aa_hl(request):
    return render_math_topic(request, 'rational_functions_aa_hl.html', 'rational_functions', 'Rational Functions', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def exp_and_logs_functions_aa_hl(request):
    return render_math_topic(request, 'exp_and_log_functions_aa_hl.html', 'exp_and_logs_functions', 'Exponential and Logarithmic Functions', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def function_transformations_aa_hl(request):
    return render_math_topic(request, 'function_transformations_aa_hl.html', 'function_transformations', 'Function Transformations', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def polynomials_aa_hl(request):
    return render_math_topic(request, 'polynomials_aa_hl.html', 'polynomials', 'Polynomials', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def mod_inequalities_aa_hl(request):
    return render_math_topic(request, 'modulus_ineq_aa_hl.html', 'mod_inequalities', 'Mod & Inequalities', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def statistics_aa_hl(request):
    return render_math_topic(request, 'statistics_aa_hl.html', 'statistics', 'Statistics', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def distributions_aa_hl(request):
    return render_math_topic(request, 'distributions_aa_hl.html', 'distributions', 'Distributions', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def probability_aa_hl(request):
    return render_math_topic(request, 'probability_aa_hl.html', 'probability', 'Probability', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def bivariate_stats_aa_hl(request):
    return render_math_topic(request, 'bivariate_stats_aa_hl.html', 'bivariate_stats', 'Bivariate Statistics', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def kinematics_aa_hl(request):
    return render_math_topic(request, 'kinematics_aa_hl.html', 'kinematics', 'Kinematics', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def differential_equations_aa_hl(request):
    return render_math_topic(request, 'differential_equations_aa_hl.html', 'differential_equations', 'Differential Equations', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def differential_calculus_aa_hl(request):
    return render_math_topic(request, 'differential_calculus_aa_hl.html', 'differentiation', 'Differential Calculus', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def integral_calculus_aa_hl(request):
    return render_math_topic(request, 'integral_calculus_aa_hl.html', 'integration', 'Integral Calculus', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')

@track_user_journey
def maclaurin_series_aa_hl(request):
    return render_math_topic(request, 'maclaurin_aa_hl.html', 'maclaurin_series', 'Maclaurin Series', 'Math AA HL', 'math-aa-hl-questions', 'math_aa.pdf', 'Math AA Formula Booklet')


########################################################
# MATH AA HL PAST PAPERS
########################################################

@track_user_journey
def math_aa_hl_past_papers(request):
    return render(request, 'math_aa_hl_past_papers.html')

def math_aa_hl_may24tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_may24tz1p1.html', "May 2024", "1", "1")

def math_aa_hl_may24tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_may24tz1p2.html', "May 2024", "1", "2")

def math_aa_hl_may24tz2p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_may24tz2p1.html', "May 2024", "2", "1")

def math_aa_hl_may24tz2p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_may24tz2p2.html', "May 2024", "2", "2")

def math_aa_hl_may23tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_may23tz1p1.html', "May 2023", "1", "1")

def math_aa_hl_may23tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_may23tz1p2.html', "May 2023", "1", "2")

def math_aa_hl_nov23tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_nov23tz1p1.html', "Nov 2023", "1", "1")

def math_aa_hl_nov23tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_nov23tz1p2.html', "Nov 2023", "1", "2")

def math_aa_hl_may22tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_may22tz1p1.html', "May 2022", "1", "1")

def math_aa_hl_may22tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_may22tz1p2.html', "May 2022", "1", "2")

def math_aa_hl_nov22tz0p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_nov22tz0p1.html', "Nov 2022", "0", "1")

def math_aa_hl_nov22tz0p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_nov22tz0p2.html', "Nov 2022", "0", "2")

def math_aa_hl_may21tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_may21tz1p1.html', "May 2021", "1", "1")

def math_aa_hl_may21tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_may21tz1p2.html', "May 2021", "1", "2")

def math_aa_hl_nov21tz0p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_nov21tz0p1.html', "Nov 2021", "0", "1")

def math_aa_hl_nov21tz0p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_AA_HL, 'math_aa_hl_nov21tz0p2.html', "Nov 2021", "0", "2")

########################################################
# MATH AA HL PAST PAPERS TOPICS
########################################################

@track_user_journey

def math_aa_hl_past_papers_topics(request):
    return render(request, 'math_aa_hl_past_papers_topics.html')

def math_aa_hl_seq_series_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_seq_series_videos.html', "seq_series", 'Sequences, Series, Financial Mathematics', Past_Paper_Videos_AA_HL)

def math_aa_hl_proofs_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_proofs_videos.html', "proofs", 'Proofs', Past_Paper_Videos_AA_HL)

def math_aa_hl_exp_and_logs_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_exp_and_logs_videos.html', "exp_and_logs", 'Exponentials and Logarithms', Past_Paper_Videos_AA_HL)

def math_aa_hl_binomial_expansion_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_binomial_expansion_videos.html', "binomial_expansion", 'Binomial Expansion', Past_Paper_Videos_AA_HL)

def math_aa_hl_properties_of_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_properties_of_functions_videos.html', "properties_of_functions", 'Properties of Functions', Past_Paper_Videos_AA_HL)

def math_aa_hl_quadratic_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_quadratic_functions_videos.html', "quadratic_functions", 'Quadratic Functions', Past_Paper_Videos_AA_HL)

def math_aa_hl_counting_principles_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_counting_principles_videos.html', "counting_principles", 'Counting Principles', Past_Paper_Videos_AA_HL)

def math_aa_hl_complex_numbers_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_complex_numbers_videos.html', "complex_numbers", 'Complex Numbers', Past_Paper_Videos_AA_HL)

def math_aa_hl_systems_of_equations_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_systems_of_equations_videos.html', "systems_of_equations", 'Systems of Equations', Past_Paper_Videos_AA_HL)

def math_aa_hl_geometry_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_geometry_videos.html', "geometry", 'Geometry', Past_Paper_Videos_AA_HL)

def math_aa_hl_trig_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_trig_functions_videos.html', "trig_functions", 'Trigonometric Functions', Past_Paper_Videos_AA_HL)

def math_aa_hl_vectors_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_vectors_videos.html', "vectors", 'Vectors', Past_Paper_Videos_AA_HL)

def math_aa_hl_rational_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_rational_functions_videos.html', "rational_functions", 'Rational Functions', Past_Paper_Videos_AA_HL)

def math_aa_hl_exp_and_logs_functions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_exp_and_logs_functions_videos.html', "exp_and_logs_functions", 'Exponential and Logarithmic Functions', Past_Paper_Videos_AA_HL)

def math_aa_hl_function_transformations_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_function_transformations_videos.html', "function_transformations", 'Function Transformations', Past_Paper_Videos_AA_HL)

def math_aa_hl_polynomials_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_polynomials_videos.html', "polynomials", 'Polynomials', Past_Paper_Videos_AA_HL)

def math_aa_hl_mod_inequalities_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_mod_inequalities_videos.html', "mod_inequalities", 'Mod & Inequalities', Past_Paper_Videos_AA_HL)

def math_aa_hl_statistics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_statistics_videos.html', "statistics", 'Statistics', Past_Paper_Videos_AA_HL)

def math_aa_hl_distributions_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_distributions_videos.html', "distributions", 'Distributions', Past_Paper_Videos_AA_HL)

def math_aa_hl_probability_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_probability_videos.html', "probability", 'Probability', Past_Paper_Videos_AA_HL)

def math_aa_hl_bivariate_stats_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_bivariate_stats_videos.html', "bivariate_stats", 'Bivariate Statistics', Past_Paper_Videos_AA_HL)

def math_aa_hl_kinematics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_kinematics_videos.html', "kinematics", 'Kinematics', Past_Paper_Videos_AA_HL)

def math_aa_hl_differential_equations_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_differential_equations_videos.html', "differential_equations", 'Differential Equations', Past_Paper_Videos_AA_HL)

def math_aa_hl_differential_calculus_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_differential_calculus_videos.html', "differential_calculus", 'Differential Calculus', Past_Paper_Videos_AA_HL)

def math_aa_hl_integral_calculus_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_integral_calculus_videos.html', "integral_calculus", 'Integral Calculus', Past_Paper_Videos_AA_HL)

def math_aa_hl_maclaurin_series_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/math_aa_hl/math_aa_hl_maclaurin_series_videos.html', "maclaurin_series", 'Maclaurin Series', Past_Paper_Videos_AA_HL)

########################################################
# PHYSICS SL QUESTIONBANK
########################################################

class PhysicsSLQuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Physics_SL_QuestionbankSerializer

    def get_queryset(self):
        queryset = Physics_SL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            queryset = queryset.filter(chapter__iexact=chapter)

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.physics_sl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.physics_sl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    if intersection == 'true':
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        target_ids = completed_ids
                    elif marked == 'true':
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    queryset = queryset.none()
            else:
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = self.request.GET.get('chapter')
        
        # Get available papers for this chapter (or all if no chapter specified)
        if chapter:
            available_papers_qs = Physics_SL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('paper', flat=True).distinct().order_by('paper')
            available_difficulties_qs = Physics_SL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('difficulty', flat=True).distinct().order_by('difficulty')
        else:
            available_papers_qs = Physics_SL_Questionbank.objects.values_list(
                'paper', flat=True
            ).distinct().order_by('paper')
            available_difficulties_qs = Physics_SL_Questionbank.objects.values_list(
                'difficulty', flat=True
            ).distinct().order_by('difficulty')
        
        available_papers = list(available_papers_qs)
        
        # Sort difficulties in the correct order (Easy, Medium, Hard)
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        available_difficulties = sorted(list(available_difficulties_qs), 
                                      key=lambda x: difficulty_order.get(x, 999))
        
        # Get user subscription status from session
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'none') if user_logged_in else 'none'
        
        # Serialize the questions
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all Physics SL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })


@track_user_journey    
def physics_sl(request):
    return render(request, 'physics_sl.html')

@track_user_journey
def kinematics_sl(request):
    return render_math_topic(request, 'kinematics_sl.html', 'kinematics', 'Kinematics', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def forces_momentum_sl(request):
    return render_math_topic(request, 'forces_momentum_sl.html', 'forces_and_momentum', 'Forces and Momentum', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def work_energy_power_sl(request):
    return render_math_topic(request, 'work_energy_power_sl.html', 'work_energy_power', 'Work, Energy and Power', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def thermal_energy_sl(request):
    return render_math_topic(request, 'thermal_energy_sl.html', 'thermal_energy', 'Thermal Energy', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def greenhouse_effect_sl(request):
    return render_math_topic(request, 'greenhouse_effect_sl.html', 'greenhouse_effect', 'Greenhouse Effect', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def ideal_gas_model_sl(request):
    return render_math_topic(request, 'ideal_gas_model_sl.html', 'ideal_gas_model', 'Ideal Gas Model', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def electric_circuits_sl(request):
    return render_math_topic(request, 'electric_circuits_sl.html', 'electric_circuits', 'Electric Circuits', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def simple_harmonic_motion_sl(request):
    return render_math_topic(request, 'simple_harmonic_motion_sl.html', 'simple_harmonic_motion', 'Simple Harmonic Motion', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def wave_model_sl(request):
    return render_math_topic(request, 'wave_model_sl.html', 'wave_model', 'Wave Model', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def wave_phenomena_sl(request):
    return render_math_topic(request, 'wave_phenomena_sl.html', 'wave_phenomena', 'Wave Phenomena', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def standing_waves_sl(request):
    return render_math_topic(request, 'standing_waves_sl.html', 'standing_waves', 'Standing Wave and Resonance', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def doppler_effect_sl(request):
    return render_math_topic(request, 'doppler_effect_sl.html', 'doppler_effect', 'Doppler Effect', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def gravitational_fields_sl(request):
    return render_math_topic(request, 'gravitational_fields_sl.html', 'gravitational_fields', 'Gravitational Fields', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def electric_magnetic_fields_sl(request):
    return render_math_topic(request, 'electric_magnetic_fields_sl.html', 'electric_magnetic_fields', 'Electric and Magnetic Fields', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def motion_in_fields_sl(request):
    return render_math_topic(request, 'motion_in_fields_sl.html', 'motion_in_fields', 'Motion in Electromagnetic Fields', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def structure_atom_sl(request):
    return render_math_topic(request, 'structure_atom_sl.html', 'structure_atom', 'Structure of the Atom', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def radioactive_decay_sl(request):
    return render_math_topic(request, 'radioactive_decay_sl.html', 'radioactive_decay', 'Radioactive Decay', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def fission_sl(request):
    return render_math_topic(request, 'fission_sl.html', 'fission', 'Fission', 'Physics SL', 'physics-sl-questions', 'none.pdf')

@track_user_journey
def fusion_and_stars_sl(request):
    return render_math_topic(request, 'fusion_and_stars_sl.html', 'fusion_and_stars', 'Fusion and Stars', 'Physics SL', 'physics-sl-questions', 'none.pdf')


########################################################
# PHYSICS SL PAST PAPERS
########################################################


@track_user_journey
def physics_sl_past_papers(request):
    return render(request, 'physics_sl_past_papers.html')

def physics_sl_may21tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may21tz1p1.html', "May 2021", "1", "1")

def physics_sl_may21tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may21tz1p2.html', "May 2021", "1", "2")

def physics_sl_may22tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may22tz1p1.html', "May 2022", "1", "1")

def physics_sl_may22tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may22tz1p2.html', "May 2022", "1", "2")

def physics_sl_may23tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may23tz1p1.html', "May 2023", "1", "1")

def physics_sl_may23tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may23tz1p2.html', "May 2023", "1", "2")

def physics_sl_may24tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may24tz1p1.html', "May 2024", "1", "1")

def physics_sl_may24tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may24tz1p2.html', "May 2024", "1", "2")

def physics_sl_nov20tz0p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_nov20tz0p1.html', "Nov 2020", "0", "1")

def physics_sl_nov20tz0p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_nov20tz0p2.html', "Nov 2020", "0", "2")

def physics_sl_specimen2025_p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_specimen2025_p1.html', "Specimen 2025", "0", "1A")

def physics_sl_specimen2025_p1b(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_specimen2025_p1b.html', "Specimen 2025", "0", "1B")

def physics_sl_specimen2025_p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_specimen2025_p2.html', "Specimen 2025", "0", "2")

def physics_sl_may25tz1p1a(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may25tz1p1a.html', "May 2025", "1", "1A")

def physics_sl_may25tz2p1a(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may25tz2p1a.html', "May 2025", "2", "1A")

def physics_sl_may25tz3p1a(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may25tz3p1a.html', "May 2025", "3", "1A")

def physics_sl_may25tz1p1b(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may25tz1p1b.html', "May 2025", "1", "1B")

def physics_sl_may25tz2p1b(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may25tz2p1b.html', "May 2025", "2", "1B")

def physics_sl_may25tz3p1b(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may25tz3p1b.html', "May 2025", "3", "1B")

def physics_sl_may25tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may25tz1p2.html', "May 2025", "1", "2")

def physics_sl_may25tz2p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may25tz2p2.html', "May 2025", "2", "2")

def physics_sl_may25tz3p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_SL, 'physics_sl_may25tz3p2.html', "May 2025", "3", "2")

########################################################
# PHYICS SL PAST PAPERS TOPICS
########################################################

@track_user_journey
def physics_sl_past_papers_topics(request):
    return render(request, 'physics_sl_past_papers_topics.html')

def physics_sl_kinematics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_kinematics_videos.html', "kinematics", 'Kinematics', Past_Paper_Videos_Physics_SL)

def physics_sl_forces_momentum_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_forces_momentum_videos.html', "forces_and_momentum", 'Forces and Momentum', Past_Paper_Videos_Physics_SL)

def physics_sl_work_energy_power_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_work_energy_power_videos.html', "work_energy_power", 'Work, Energy and Power', Past_Paper_Videos_Physics_SL)

def physics_sl_thermal_energy_transfer_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_thermal_energy_transfer_videos.html', "thermal_energy", 'Thermal Energy', Past_Paper_Videos_Physics_SL)

def physics_sl_greenhouse_effect_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_greenhouse_effect_videos.html', "greenhouse_effect", 'Greenhouse Effect', Past_Paper_Videos_Physics_SL)

def physics_sl_ideal_gas_model_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_ideal_gas_model_videos.html', "ideal_gas_model", 'Ideal Gas Model', Past_Paper_Videos_Physics_SL)

def physics_sl_electric_circuits_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_electric_circuits_videos.html', "electric_circuits", 'Electric Circuits', Past_Paper_Videos_Physics_SL)

def physics_sl_simple_harmonic_motion_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_simple_harmonic_motion_videos.html', "simple_harmonic_motion", 'Simple Harmonic Motion', Past_Paper_Videos_Physics_SL)

def physics_sl_wave_model_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_wave_model_videos.html', "wave_model", 'Wave Model', Past_Paper_Videos_Physics_SL)

def physics_sl_wave_phenomena_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_wave_phenomena_videos.html', "wave_phenomena", 'Wave Phenomena', Past_Paper_Videos_Physics_SL)

def physics_sl_standing_waves_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_standing_waves_videos.html', "standing_waves", 'Standing Wave and Resonance', Past_Paper_Videos_Physics_SL)

def physics_sl_doppler_effect_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_doppler_effect_videos.html', "doppler_effect", 'Doppler Effect', Past_Paper_Videos_Physics_SL)

def physics_sl_gravitational_fields_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_gravitational_fields_videos.html', "gravitational_fields", 'Gravitational Fields', Past_Paper_Videos_Physics_SL)

def physics_sl_electric_magnetic_fields_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_electric_magnetic_fields_videos.html', "electric_magnetic_fields", 'Electric and Magnetic Fields', Past_Paper_Videos_Physics_SL)

def physics_sl_motion_in_fields_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_motion_in_fields_videos.html', "motion_in_fields", 'Motion in Electromagnetic Fields', Past_Paper_Videos_Physics_SL)

def physics_sl_structure_of_the_atom_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_structure_of_the_atom_videos.html', "structure_atom", 'Structure of the Atom', Past_Paper_Videos_Physics_SL)

def physics_sl_radioactive_decay_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_radioactive_decay_videos.html', "radioactive_decay", 'Radioactive Decay', Past_Paper_Videos_Physics_SL)

def physics_sl_fission_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_fission_videos.html', "fission", 'Fission', Past_Paper_Videos_Physics_SL)

def physics_sl_fusion_and_stars_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_sl/physics_sl_fusion_and_stars_videos.html', "fusion_and_stars", 'Fusion and Stars', Past_Paper_Videos_Physics_SL)


########################################################
# PHYSICS HL QUESTIONBANK
########################################################


class PhysicsHLQuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Physics_HL_QuestionbankSerializer

    def get_queryset(self):
        queryset = Physics_HL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            queryset = queryset.filter(chapter__iexact=chapter)

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.physics_hl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.physics_hl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    if intersection == 'true':
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        target_ids = completed_ids
                    elif marked == 'true':
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    queryset = queryset.none()
            else:
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = self.request.GET.get('chapter')
        
        # Get available papers for this chapter (or all if no chapter specified)
        if chapter:
            available_papers_qs = Physics_HL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('paper', flat=True).distinct().order_by('paper')
            available_difficulties_qs = Physics_HL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('difficulty', flat=True).distinct().order_by('difficulty')
        else:
            available_papers_qs = Physics_HL_Questionbank.objects.values_list(
                'paper', flat=True
            ).distinct().order_by('paper')
            available_difficulties_qs = Physics_HL_Questionbank.objects.values_list(
                'difficulty', flat=True
            ).distinct().order_by('difficulty')
        
        available_papers = list(available_papers_qs)
        
        # Sort difficulties in the correct order (Easy, Medium, Hard)
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        available_difficulties = sorted(list(available_difficulties_qs), 
                                      key=lambda x: difficulty_order.get(x, 999))
        
        # Get user subscription status from session
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'none') if user_logged_in else 'none'
        
        # Serialize the questions
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all Physics HL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })

    
@track_user_journey
def physics_hl(request):
    return render(request, 'physics_hl.html')

@track_user_journey
def kinematics_hl(request):
    return render_math_topic(request, 'kinematics_hl.html', 'kinematics', 'Kinematics', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def forces_momentum_hl(request):
    return render_math_topic(request, 'forces_momentum_hl.html', 'forces_and_momentum', 'Forces and Momentum', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def work_energy_power_hl(request):
    return render_math_topic(request, 'work_energy_power_hl.html', 'work_energy_power', 'Work, Energy and Power', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def rigid_body_mechanics_hl(request):
    return render_math_topic(request, 'rigid_body_mechanics_hl.html', 'rigid_body_mechanics', 'Rigid Body Mechanics', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def galilean_and_special_relativity_hl(request):
    return render_math_topic(request, 'galilean_and_special_relativity_hl.html', 'galilean_and_special_relativity', 'Galilean and Special Relativity', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def thermal_energy_hl(request):
    return render_math_topic(request, 'thermal_energy_hl.html', 'thermal_energy', 'Thermal Energy', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def greenhouse_effect_hl(request):
    return render_math_topic(request, 'greenhouse_effect_hl.html', 'greenhouse_effect', 'Greenhouse Effect', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def ideal_gas_model_hl(request):
    return render_math_topic(request, 'ideal_gas_model_hl.html', 'ideal_gas_model', 'Ideal Gas Model', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def thermodynamics_hl(request):
    return render_math_topic(request, 'thermodynamics_hl.html', 'thermodynamics', 'Thermodynamics', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def electric_circuits_hl(request):
    return render_math_topic(request, 'electric_circuits_hl.html', 'electric_circuits', 'Electric Circuits', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def simple_harmonic_motion_hl(request):
    return render_math_topic(request, 'simple_harmonic_motion_hl.html', 'simple_harmonic_motion', 'Simple Harmonic Motion', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def wave_model_hl(request):
    return render_math_topic(request, 'wave_model_hl.html', 'wave_model', 'Wave Model', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def wave_phenomena_hl(request):
    return render_math_topic(request, 'wave_phenomena_hl.html', 'wave_phenomena', 'Wave Phenomena', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def standing_waves_hl(request):
    return render_math_topic(request, 'standing_waves_hl.html', 'standing_waves', 'Standing Wave and Resonance', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def doppler_effect_hl(request):
    return render_math_topic(request, 'doppler_effect_hl.html', 'doppler_effect', 'Doppler Effect', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def gravitational_fields_hl(request):
    return render_math_topic(request, 'gravitational_fields_hl.html', 'gravitational_fields', 'Gravitational Fields', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def electric_magnetic_fields_hl(request):
    return render_math_topic(request, 'electric_magnetic_fields_hl.html', 'electric_magnetic_fields', 'Electric and Magnetic Fields', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def motion_in_fields_hl(request):
    return render_math_topic(request, 'motion_in_fields_hl.html', 'motion_in_fields', 'Motion in Electromagnetic Fields', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def induction_hl(request):
    return render_math_topic(request, 'induction_hl.html', 'induction', 'Induction', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def structure_atom_hl(request):
    return render_math_topic(request, 'structure_atom_hl.html', 'structure_atom', 'Structure of the Atom', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def quantum_physics_hl(request):
    return render_math_topic(request, 'quantum_physics_hl.html', 'quantum_physics', 'Quantum Physics', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def radioactive_decay_hl(request):
    return render_math_topic(request, 'radioactive_decay_hl.html', 'radioactive_decay', 'Radioactive Decay', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def fission_hl(request):
    return render_math_topic(request, 'fission_hl.html', 'fission', 'Fission', 'Physics HL', 'physics-hl-questions', 'none.pdf')

@track_user_journey
def fusion_and_stars_hl(request):
    return render_math_topic(request, 'fusion_and_stars_hl.html', 'fusion_and_stars', 'Fusion and Stars', 'Physics HL', 'physics-hl-questions', 'none.pdf')

########################################################
# PHYSICS HL PAST PAPERS TOPICS
########################################################

@track_user_journey
def physics_hl_past_papers_topics(request):
    return render(request, 'physics_hl_past_papers_topics.html')

def physics_hl_kinematics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_kinematics_videos.html', "kinematics", 'Kinematics', Past_Paper_Videos_Physics_HL)

def physics_hl_forces_momentum_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_forces_momentum_videos.html', "forces_and_momentum", 'Forces and Momentum', Past_Paper_Videos_Physics_HL)

def physics_hl_work_energy_power_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_work_energy_power_videos.html', "work_energy_power", 'Work, Energy and Power', Past_Paper_Videos_Physics_HL)

def physics_hl_rigid_body_mechanics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_rigid_body_mechanics_videos.html', 'rigid_body_mechanics', 'Rigid Body Mechanics', Past_Paper_Videos_Physics_HL)

def physics_hl_galilean_and_special_relativity_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_galilean_and_special_relativity_videos.html', 'galilean_and_special_relativity', 'Galilean and Special Relativity', Past_Paper_Videos_Physics_HL)

def physics_hl_thermal_energy_transfer_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_thermal_energy_transfer_videos.html', 'thermal_energy', 'Thermal Energy', Past_Paper_Videos_Physics_HL)

def physics_hl_greenhouse_effect_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_greenhouse_effect_videos.html', 'greenhouse_effect', 'Greenhouse Effect', Past_Paper_Videos_Physics_HL)

def physics_hl_ideal_gas_model_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_ideal_gas_model_videos.html', 'ideal_gas_model', 'Ideal Gas Model', Past_Paper_Videos_Physics_HL)

def physics_hl_thermodynamics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_thermodynamics_videos.html', 'thermodynamics', 'Thermodynamics', Past_Paper_Videos_Physics_HL)

def physics_hl_electric_circuits_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_electric_circuits_videos.html', 'electric_circuits', 'Electric Circuits', Past_Paper_Videos_Physics_HL)

def physics_hl_wave_phenomena_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_wave_phenomena_videos.html', 'wave_phenomena', 'Wave Phenomena', Past_Paper_Videos_Physics_HL)

def physics_hl_simple_harmonic_motion_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_simple_harmonic_motion_videos.html', 'simple_harmonic_motion', 'Simple Harmonic Motion', Past_Paper_Videos_Physics_HL)

def physics_hl_wave_model_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_wave_model_videos.html', 'wave_model', 'Wave Model', Past_Paper_Videos_Physics_HL)

def physics_hl_standing_waves_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_standing_waves_videos.html', 'standing_waves', 'Standing Wave and Resonance', Past_Paper_Videos_Physics_HL)

def physics_hl_doppler_effect_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_doppler_effect_videos.html', 'doppler_effect', 'Doppler Effect', Past_Paper_Videos_Physics_HL)

def physics_hl_gravitational_fields_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_gravitational_fields_videos.html', 'gravitational_fields', 'Gravitational Fields', Past_Paper_Videos_Physics_HL)

def physics_hl_electric_magnetic_fields_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_electric_magnetic_fields_videos.html', 'electric_magnetic_fields', 'Electric and Magnetic Fields', Past_Paper_Videos_Physics_HL)

def physics_hl_motion_in_fields_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_motion_in_fields_videos.html', 'motion_in_fields', 'Motion in Electromagnetic Fields', Past_Paper_Videos_Physics_HL)

def physics_hl_structure_of_the_atom_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_structure_of_the_atom_videos.html', 'structure_atom', 'Structure of the Atom', Past_Paper_Videos_Physics_HL)

def physics_hl_radioactive_decay_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_radioactive_decay_videos.html', 'radioactive_decay', 'Radioactive Decay', Past_Paper_Videos_Physics_HL)

def physics_hl_fission_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_fission_videos.html', 'fission', 'Fission', Past_Paper_Videos_Physics_HL)

def physics_hl_fusion_and_stars_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_fusion_and_stars_videos.html', 'fusion_and_stars', 'Fusion and Stars', Past_Paper_Videos_Physics_HL)

def physics_hl_induction_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_induction_videos.html', 'induction', 'Induction', Past_Paper_Videos_Physics_HL)

def physics_hl_quantum_physics_videos(request):
    return render_past_papers_videos_by_topic_with_access_control(request, 'past_papers_topics/physics_hl/physics_hl_quantum_physics_videos.html', 'quantum_physics', 'Quantum Physics', Past_Paper_Videos_Physics_HL)



########################################################
# PHYSICS HL PAST PAPERS
########################################################

@track_user_journey
def physics_hl_past_papers(request):
    return render(request, 'physics_hl_past_papers.html')

def physics_hl_may21tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may21tz1p1.html', "May 2021", "1", "1")

def physics_hl_may21tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may21tz1p2.html', "May 2021", "1", "2")

def physics_hl_may22tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may22tz1p1.html', "May 2022", "1", "1")

def physics_hl_may22tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may22tz1p2.html', "May 2022", "1", "2")

def physics_hl_may23tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may23tz1p1.html', "May 2023", "1", "1")

def physics_hl_may23tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may23tz1p2.html', "May 2023", "1", "2")

def physics_hl_may24tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may24tz1p1.html', "May 2024", "1", "1")

def physics_hl_may24tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may24tz1p2.html', "May 2024", "1", "2")

def physics_hl_nov20tz0p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_nov20tz0p1.html', "Nov 2020", "0", "1")

def physics_hl_nov20tz0p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_nov20tz0p2.html', "Nov 2020", "0", "2")

def physics_hl_specimen2025_p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_specimen2025_p1.html', "Specimen 2025", "0", "1A")

def physics_hl_specimen2025_p1b(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_specimen2025_p1b.html', "Specimen 2025", "0", "1B")

def physics_hl_specimen2025_p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_specimen2025_p2.html', "Specimen 2025", "0", "2")

def physics_hl_may25tz1p1a(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may25tz1p1a.html', "May 2025", "1", "1A")

def physics_hl_may25tz2p1a(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may25tz2p1a.html', "May 2025", "2", "1A")

def physics_hl_may25tz3p1a(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may25tz3p1a.html', "May 2025", "3", "1A") 

def physics_hl_may25tz1p1b(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may25tz1p1b.html', "May 2025", "1", "1B")

def physics_hl_may25tz2p1b(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may25tz2p1b.html', "May 2025", "2", "1B")

def physics_hl_may25tz3p1b(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may25tz3p1b.html', "May 2025", "3", "1B")

def physics_hl_may25tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may25tz1p2.html', "May 2025", "1", "2")

def physics_hl_may25tz2p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may25tz2p2.html', "May 2025", "2", "2")

def physics_hl_may25tz3p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may25tz3p2.html', "May 2025", "3", "2")

########################################################
# CHEMISTRY SL QUESTIONBANK    
########################################################


class ChemistrySLQuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Chemistry_SL_QuestionbankSerializer

    def get_queryset(self):
        queryset = Chemistry_SL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            queryset = queryset.filter(chapter__iexact=chapter)

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.chemistry_sl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.chemistry_sl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    if intersection == 'true':
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        target_ids = completed_ids
                    elif marked == 'true':
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    queryset = queryset.none()
            else:
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = self.request.GET.get('chapter')
        
        # Get available papers for this chapter (or all if no chapter specified)
        if chapter:
            available_papers_qs = Chemistry_SL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('paper', flat=True).distinct().order_by('paper')
            available_difficulties_qs = Chemistry_SL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('difficulty', flat=True).distinct().order_by('difficulty')
        else:
            available_papers_qs = Chemistry_SL_Questionbank.objects.values_list(
                'paper', flat=True
            ).distinct().order_by('paper')
            available_difficulties_qs = Chemistry_SL_Questionbank.objects.values_list(
                'difficulty', flat=True
            ).distinct().order_by('difficulty')
        
        available_papers = list(available_papers_qs)
        
        # Sort difficulties in the correct order (Easy, Medium, Hard)
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        available_difficulties = sorted(list(available_difficulties_qs), 
                                      key=lambda x: difficulty_order.get(x, 999))
        
        # Get user subscription status from session
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'none') if user_logged_in else 'none'
        
        # Serialize the questions
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all Chemistry SL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })

    
@track_user_journey
def chemistry_sl(request):
    return render(request, 'chemistry_sl.html')

def introduction_particulate_matter(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/introduction_particulate_matter.html', 'introduction_particulate_matter', 'Introduction to the Particulate Nature of Matter', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def ideal_gases(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/ideal_gases.html', 'ideal_gases', 'Ideal Gases', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def nuclear_atom(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/nuclear_atom.html', 'nuclear_atom', 'The Nuclear Atom', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def electron_configurations(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/electron_configurations.html', 'electron_configurations', 'Electron Configurations', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def counting_particles_mole(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/counting_particles_mole.html', 'counting_particles_mole', 'Counting Particles by Mass: The Mole', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def ionic_model(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/ionic_model.html', 'ionic_model', 'The Ionic Model', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def covalent_model(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/covalent_model.html', 'covalent_model', 'The Covalent Model', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def metallic_model(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/metallic_model.html', 'metallic_model', 'The Metallic Model', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def models_to_materials(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/models_to_materials.html', 'models_to_materials', 'From Models to Materials', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def periodic_table(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/periodic_table.html', 'periodic_table', 'The Periodic Table', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def functional_groups(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/functional_groups.html', 'functional_groups', 'Functional Groups', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def measuring_enthalpy(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/measuring_enthalpy.html', 'measuring_enthalpy', 'Measuring Enthalpy Changes', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def energy_cycles(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/energy_cycles.html', 'energy_cycles', 'Energy Cycles in Reactions', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def energy_from_fuels(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/energy_from_fuels.html', 'energy_from_fuels', 'Energy from Fuels', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def amount_chemical_change(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/amount_chemical_change.html', 'amount_chemical_change', 'How Much? The Amount of Chemical Change', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def rate_chemical_change(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/rate_chemical_change.html', 'rate_chemical_change', 'How Fast? The Rate of Chemical Change', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def extent_chemical_change(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/extent_chemical_change.html', 'extent_chemical_change', 'How Far? The Extent of Chemical Change', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def proton_transfer(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/proton_transfer.html', 'proton_transfer', 'Proton Transfer Reactions', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def electron_transfer(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/electron_transfer.html', 'electron_transfer', 'Electron Transfer Reactions', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def electron_sharing(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/electron_sharing.html', 'electron_sharing', 'Electron Sharing Reactions', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

def electron_pair_sharing(request):
    return render_math_topic(request, 'questionbank/chemistry/sl/electron_pair_sharing.html', 'electron_pair_sharing', 'Electron-Pair Sharing Reactions', 'Chemistry SL', 'chemistry-sl-questions', 'none.pdf')

########################################################
# CHEMISTRY SL PAST PAPERS
########################################################

@track_user_journey
def chemistry_sl_past_papers(request):
    return render(request, 'chemistry_sl_past_papers.html')

# def physics_hl_may21tz1p1(request):
#     return render_past_papers_videos(request, Past_Paper_Videos_Physics_HL, 'physics_hl_may21tz1p1.html', "May 2021", "1", "1")





########################################################
# CHEMISTRY HL QUESTIONBANK    
########################################################


class ChemistryHLQuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Chemistry_HL_QuestionbankSerializer

    def get_queryset(self):
        queryset = Chemistry_HL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            queryset = queryset.filter(chapter__iexact=chapter)

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.chemistry_sl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.chemistry_sl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    if intersection == 'true':
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        target_ids = completed_ids
                    elif marked == 'true':
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    queryset = queryset.none()
            else:
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = self.request.GET.get('chapter')
        
        # Get available papers for this chapter (or all if no chapter specified)
        if chapter:
            available_papers_qs = Chemistry_HL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('paper', flat=True).distinct().order_by('paper')
            available_difficulties_qs = Chemistry_HL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('difficulty', flat=True).distinct().order_by('difficulty')
        else:
            available_papers_qs = Chemistry_HL_Questionbank.objects.values_list(
                'paper', flat=True
            ).distinct().order_by('paper')
            available_difficulties_qs = Chemistry_HL_Questionbank.objects.values_list(
                'difficulty', flat=True
            ).distinct().order_by('difficulty')
        
        available_papers = list(available_papers_qs)
        
        # Sort difficulties in the correct order (Easy, Medium, Hard)
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        available_difficulties = sorted(list(available_difficulties_qs), 
                                      key=lambda x: difficulty_order.get(x, 999))
        
        # Get user subscription status from session
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'none') if user_logged_in else 'none'
        
        # Serialize the questions
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all Chemistry SL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })

    
@track_user_journey
def chemistry_hl(request):
    return render(request, 'chemistry_hl.html')

def introduction_particulate_matter_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/introduction_particulate_matter_hl.html', 'introduction_particulate_nature', 'Introduction to the Particulate Nature of Matter', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def nuclear_atom_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/nuclear_atom_hl.html', 'nuclear_atom', 'The Nuclear Atom', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def electron_configurations_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/electron_configurations_hl.html', 'electron_configurations', 'Electron Configurations', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def counting_particles_mole_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/counting_particles_mole_hl.html', 'counting_particles_mole', 'Counting Particles by Mass: The Mole', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def ideal_gases_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/ideal_gases_hl.html', 'ideal_gases', 'Ideal Gases', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def ionic_model_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/ionic_model_hl.html', 'ionic_model', 'The Ionic Model', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def covalent_model_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/covalent_model_hl.html', 'covalent_model', 'The Covalent Model', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def metallic_model_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/metallic_model_hl.html', 'metallic_model', 'The Metallic Model', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def models_to_materials_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/models_to_materials_hl.html', 'models_to_materials', 'From Models to Materials', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def periodic_table_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/periodic_table_hl.html', 'periodic_table', 'The Periodic Table', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def functional_groups_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/functional_groups_hl.html', 'functional_groups', 'Functional Groups', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def measuring_enthalpy_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/measuring_enthalpy_hl.html', 'measuring_enthalpy', 'Measuring Enthalpy Changes', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def energy_cycles_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/energy_cycles_hl.html', 'energy_cycles', 'Energy Cycles in Reactions', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def energy_from_fuels_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/energy_from_fuels_hl.html', 'energy_from_fuels', 'Energy from Fuels', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def entropy_spontaneity_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/entropy_spontaneity_hl.html', 'entropy_spontaneity', 'Entropy and Spontaneity', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def amount_chemical_change_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/amount_chemical_change_hl.html', 'amount_chemical_change', 'How Much? The Amount of Chemical Change', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def rate_chemical_change_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/rate_chemical_change_hl.html', 'rate_chemical_change', 'How Fast? The Rate of Chemical Change', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def extent_chemical_change_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/extent_chemical_change_hl.html', 'extent_chemical_change', 'How Far? The Extent of Chemical Change', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def proton_transfer_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/proton_transfer_hl.html', 'proton_transfer', 'Proton Transfer Reactions', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def electron_transfer_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/electron_transfer_hl.html', 'electron_transfer', 'Electron Transfer Reactions', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def electron_sharing_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/electron_sharing_hl.html', 'electron_sharing', 'Electron Sharing Reactions', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')

def electron_pair_sharing_hl(request):
    return render_math_topic(request, 'questionbank/chemistry/hl/electron_pair_sharing_hl.html', 'electron_pair_sharing', 'Electron-Pair Sharing Reactions', 'Chemistry HL', 'chemistry-hl-questions', 'none.pdf')



########################################################
# BIOLOGY SL QUESTIONBANK
########################################################

class BiologySLQuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Biology_SL_QuestionbankSerializer

    def get_queryset(self):
        queryset = Biology_SL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            queryset = queryset.filter(chapter__iexact=chapter)

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.biology_sl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.biology_sl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    if intersection == 'true':
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        target_ids = completed_ids
                    elif marked == 'true':
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    queryset = queryset.none()
            else:
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = self.request.GET.get('chapter')
        
        # Get available papers for this chapter (or all if no chapter specified)
        if chapter:
            available_papers_qs = Biology_SL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('paper', flat=True).distinct().order_by('paper')
            available_difficulties_qs = Biology_SL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('difficulty', flat=True).distinct().order_by('difficulty')
        else:
            available_papers_qs = Biology_SL_Questionbank.objects.values_list(
                'paper', flat=True
            ).distinct().order_by('paper')
            available_difficulties_qs = Biology_SL_Questionbank.objects.values_list(
                'difficulty', flat=True
            ).distinct().order_by('difficulty')
        
        available_papers = list(available_papers_qs)
        
        # Sort difficulties in the correct order (Easy, Medium, Hard)
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        available_difficulties = sorted(list(available_difficulties_qs), 
                                      key=lambda x: difficulty_order.get(x, 999))
        
        # Get user subscription status from session
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'none') if user_logged_in else 'none'
        
        # Serialize the questions
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all Bio SL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })

@track_user_journey
def biology_sl(request):
    return render(request, 'biology_sl.html')

def water_sl(request):
    return render_math_topic(request, 'water_sl.html', 'water', 'Water', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def water_sl_chatgpt(request):
    return render_math_topic(request, 'water_sl_chatgpt.html', 'water', 'Water', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def nucleic_acids_sl(request):
    return render_math_topic(request, 'nucleic_acids_sl.html', 'nucleic_acids', 'Nucleic Acids', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def cell_structure_sl(request):
    return render_math_topic(request, 'cell_structure_sl.html', 'cell_structure', 'Cell Structure', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def diversity_of_organisms_sl(request):
    return render_math_topic(request, 'diversity_of_organisms_sl.html', 'diversity_of_organisms', 'Diversity of Organisms', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def evolution_and_speciation_sl(request):
    return render_math_topic(request, 'evolution_and_speciation_sl.html', 'evolution_and_speciation', 'Evolution and Speciation', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def conservation_of_biodiversity_sl(request):
    return render_math_topic(request, 'conservation_of_biodiversity_sl.html', 'conservation_of_biodiversity', 'Conservation of Biodiversity', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def carbohydrates_and_lipids_sl(request):
    return render_math_topic(request, 'carbohydrates_and_lipids_sl.html', 'carbohydrates_and_lipids', 'Carbohydrates and Lipids', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def proteins_sl(request):
    return render_math_topic(request, 'proteins_sl.html', 'proteins', 'Proteins', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def membranes_transport_sl(request):
    return render_math_topic(request, 'membranes_transport_sl.html', 'membranes_and_membrane_transport', 'Membranes and Membrane Transport', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def organelles_comperatment_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/organelles_compartment_sl.html', 'organelles_and_compartmentalization', 'Organelles and Compartmentalization', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def cell_specialization_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/cell_specialization_sl.html', 'cell_specialization', 'Cell Specialization', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def gas_exchange_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/gas_exchange_sl.html', 'gas_exchange', 'Gas Exchange', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def transport_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/transport_sl.html', 'transport', 'Transport', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def adaptation_to_environment_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/adaptation_to_environment_sl.html', 'adaptation_to_environment', 'Adaptation to Environment', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def ecological_niches_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/ecological_niches_sl.html', 'ecological_niches', 'Ecological Niches', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def enzymes_metabolism_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/enzymes_metabolism_sl.html', 'enzymes_metabolism', 'Enzymes and Metabolism', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def cell_respiration_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/cell_respiration_sl.html', 'cell_respiration', 'Cell Respiration', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def photosynthesis_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/photosynthesis_sl.html', 'photosynthesis', 'Photosynthesis', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def neural_signaling_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/neural_signaling_sl.html', 'neural_signaling', 'Neural Signaling', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def integration_body_systems_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/integration_body_system_sl.html', 'integration_of_body_systems', 'Integration of Body Systems', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def defence_against_disease_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/defence_against_disease_sl.html', 'defence_against_disease', 'Defence Against Disease', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def population_and_communities_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/population_and_communities_sl.html', 'population_and_communities', 'Population and Communities', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def transfer_of_energy_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/transfer_of_energy_sl.html', 'transfer_of_energy', 'Transfer of Energy and Matter', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def dna_replication_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/dna_replication_sl.html', 'dna_replication', 'DNA Replication', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def protein_synthesis_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/protein_synthesis_sl.html', 'protein_synthesis', 'Protein Synthesis', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def mutations_editing_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/mutations_editing_sl.html', 'mutations_editing', 'Mutations and Gene Editing', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def natural_selection_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/natural_selection_sl.html', 'natural_selection', 'Natural Selection', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def inheritance_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/inheritance_sl.html', 'inheritance', 'Inheritance', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def climate_change_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/climate_change_sl.html', 'climate_change', 'Climate Change', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def water_potential_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/water_potential_sl.html', 'water_potential', 'Water Potential', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def cell_division_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/cell_division_sl.html', 'cell_division', 'Cell and Nuclear Division', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def reproduction_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/reproduction_sl.html', 'reproduction', 'Reproduction', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def stability_change_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/stability_change_sl.html', 'stability_change', 'Stability & Change', 'Biology SL', 'biology-sl-questions', 'none.pdf')

def homeostasis_sl(request):
    return render_math_topic(request, 'questionbank/biology/sl/homeostasis_sl.html', 'homeostasis', 'Homeostasis', 'Biology SL', 'biology-sl-questions', 'none.pdf')



########################################################
# BIOLOGY HL QUESTIONBANK
########################################################

class BiologyHLQuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Biology_HL_QuestionbankSerializer

    def get_queryset(self):
        queryset = Biology_HL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            queryset = queryset.filter(chapter__iexact=chapter)

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.biology_hl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.biology_hl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    if intersection == 'true':
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        target_ids = completed_ids
                    elif marked == 'true':
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    queryset = queryset.none()
            else:
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = self.request.GET.get('chapter')
        
        # Get available papers for this chapter (or all if no chapter specified)
        if chapter:
            available_papers_qs = Biology_HL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('paper', flat=True).distinct().order_by('paper')
            available_difficulties_qs = Biology_HL_Questionbank.objects.filter(
                chapter__iexact=chapter
            ).values_list('difficulty', flat=True).distinct().order_by('difficulty')
        else:
            available_papers_qs = Biology_HL_Questionbank.objects.values_list(
                'paper', flat=True
            ).distinct().order_by('paper')
            available_difficulties_qs = Biology_HL_Questionbank.objects.values_list(
                'difficulty', flat=True
            ).distinct().order_by('difficulty')
        
        available_papers = list(available_papers_qs)
        
        # Sort difficulties in the correct order (Easy, Medium, Hard)
        difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
        available_difficulties = sorted(list(available_difficulties_qs), 
                                      key=lambda x: difficulty_order.get(x, 999))
        
        # Get user subscription status from session
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'none') if user_logged_in else 'none'
        
        # Serialize the questions
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all Bio HL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })


@track_user_journey
def biology_hl(request):
    return render(request, 'biology_hl.html')

def water_hl(request):
    return render_math_topic(request, 'water_hl.html', 'water', 'Water', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def nucleic_acids_hl(request):
    return render_math_topic(request, 'nucleic_acids_hl.html', 'nucleic_acids', 'Nucleic Acids', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def origin_of_cells_hl(request):
    return render_math_topic(request, 'origin_of_cells_hl.html', 'origin_of_cells', 'Origin of Cells', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def cell_structure_hl(request):
    return render_math_topic(request, 'cell_structure_hl.html', 'cell_structure', 'Cell Structure', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def viruses_hl(request):
    return render_math_topic(request, 'viruses_hl.html', 'viruses', 'Viruses', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def diversity_of_organisms_hl(request):
    return render_math_topic(request, 'diversity_of_organisms_hl.html', 'diversity_of_organisms', 'Diversity of Organisms', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def classification_hl(request):
    return render_math_topic(request, 'classification_hl.html', 'classification', 'Classification', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def evolution_and_speciation_hl(request):
    return render_math_topic(request, 'evolution_and_speciation_hl.html', 'evolution_and_speciation', 'Evolution and Speciation', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def conservation_of_biodiversity_hl(request):
    return render_math_topic(request, 'conservation_of_biodiversity_hl.html', 'conservation_of_biodiversity', 'Conservation of Biodiversity', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def carbohydrates_and_lipids_hl(request):
    return render_math_topic(request, 'carbohydrates_and_lipids_hl.html', 'carbohydrates_and_lipids', 'Carbohydrates and Lipids', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def proteins_hl(request):
    return render_math_topic(request, 'proteins_hl.html', 'proteins', 'Proteins', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def membranes_transport_hl(request):
    return render_math_topic(request, 'membranes_transport_hl.html', 'membranes_and_membrane_transport', 'Membranes and Membrane Transport', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def organelles_comperatment_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/organelles_compartment_hl.html', 'organelles_and_compartmentalization', 'Organelles and Compartmentalization', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def cell_specialization_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/cell_specialization_hl.html', 'cell_specialization', 'Cell Specialization', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def gas_exchange_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/gas_exchange_hl.html', 'gas_exchange', 'Gas Exchange', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def transport_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/transport_hl.html', 'transport', 'Transport', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def muscle_and_motility_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/muscle_and_motility_hl.html', 'muscle_and_motility', 'Muscle and Motility', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def adaptation_to_environment_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/adaptation_to_environment_hl.html', 'adaptation_to_environment', 'Adaptation to Environment', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def ecological_niches_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/ecological_niches_hl.html', 'ecological_niches', 'Ecological Niches', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def enzymes_metabolism_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/enzymes_metabolism_hl.html', 'enzymes_metabolism', 'Enzymes and Metabolism', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def cell_respiration_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/cell_respiration_hl.html', 'cell_respiration', 'Cell Respiration', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def photosynthesis_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/photosynthesis_hl.html', 'photosynthesis', 'Photosynthesis', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def chemical_signaling_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/chemical_signaling_hl.html', 'chemical_signaling', 'Chemical Signaling', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def neural_signaling_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/neural_signaling_hl.html', 'neural_signaling', 'Neural Signaling', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def integration_body_systems_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/integration_body_system_hl.html', 'integration_of_body_systems', 'Integration of Body Systems', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def defence_against_disease_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/defence_against_disease_hl.html', 'defence_against_disease', 'Defence Against Disease', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def population_and_communities_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/population_and_communities_hl.html', 'population_and_communities', 'Population and Communities', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def transfer_of_energy_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/transfer_of_energy_hl.html', 'transfer_of_energy', 'Transfer of Energy and Matter', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def dna_replication_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/dna_replication_hl.html', 'dna_replication', 'DNA Replication', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def protein_synthesis_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/protein_synthesis_hl.html', 'protein_synthesis', 'Protein Synthesis', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def mutations_editing_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/mutations_editing_hl.html', 'mutations_editing', 'Mutations and Gene Editing', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def natural_selection_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/natural_selection_hl.html', 'natural_selection', 'Natural Selection', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def inheritance_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/inheritance_hl.html', 'inheritance', 'Inheritance', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def climate_change_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/climate_change_hl.html', 'climate_change', 'Climate Change', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def water_potential_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/water_potential_hl.html', 'water_potential', 'Water Potential', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def cell_division_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/cell_division_hl.html', 'cell_division', 'Cell and Nuclear Division', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def reproduction_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/reproduction_hl.html', 'reproduction', 'Reproduction', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def stability_change_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/stability_change_hl.html', 'stability_change', 'Stability & Change', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def homeostasis_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/homeostasis_hl.html', 'homeostasis', 'Homeostasis', 'Biology HL', 'biology-hl-questions', 'none.pdf')

def gene_expression_hl(request):
    return render_math_topic(request, 'questionbank/biology/hl/gene_expression_hl.html', 'gene_expression', 'Gene Expression', 'Biology HL', 'biology-hl-questions', 'none.pdf')


########################################################
# COMP SCI SL QUESTIONBANK
########################################################

class CompSciSLQuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Comp_Sci_SL_QuestionbankSerializer

    def get_queryset(self):
        queryset = Comp_Sci_SL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            queryset = queryset.filter(chapter__iexact=chapter)

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            # Get user email from session
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.comp_sci_sl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.comp_sci_sl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    # Determine which IDs to filter by
                    if intersection == 'true':
                        # Intersection: questions that are both completed AND marked
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        # Only completed
                        target_ids = completed_ids
                    elif marked == 'true':
                        # Only marked
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        # Apply progress filter to the already-filtered queryset
                        # This preserves any existing difficulty, paper, and chapter filters
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        # If no target questions, return empty queryset
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    # If no progress record, return empty queryset
                    queryset = queryset.none()
            else:
                # If not logged in, return empty queryset
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = request.GET.get('chapter')
        
        # Get user authentication status
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'free')
        
        # Derive available filters from the current queryset (respecting chapter and other filters)
        available_papers = list(
            queryset.order_by().values_list('paper', flat=True).distinct()
        )
        available_difficulties = list(
            queryset.order_by().values_list('difficulty', flat=True).distinct()
        )
        
        # Serialize the queryset
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all Computer Science SL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })


@track_user_journey
def comp_sci_sl(request):
    return render(request, 'questionbank/computer_science/sl/comp_sci_sl.html')

@track_user_journey
def system_fundamentals_sl(request):
    return render_math_topic(request, 'questionbank/computer_science/sl/system_fundamentals_sl.html', 'system_fundamentals', 'System Fundamentals', 'Computer Science SL', 'comp-sci-sl-questions', 'none.pdf')

@track_user_journey
def computer_organisation_sl(request):
    return render_math_topic(request, 'questionbank/computer_science/sl/computer_organisation_sl.html', 'computer_organisation', 'Computer Organisation', 'Computer Science SL', 'comp-sci-sl-questions', 'none.pdf')

@track_user_journey
def networks_sl(request):
    return render_math_topic(request, 'questionbank/computer_science/sl/networks_sl.html', 'networks', 'Networks', 'Computer Science SL', 'comp-sci-sl-questions', 'none.pdf')

@track_user_journey
def computational_thinking_sl(request):
    return render_math_topic(request, 'questionbank/computer_science/sl/computational_thinking_sl.html', 'computational_thinking', 'Computational Thinking', 'Computer Science SL', 'comp-sci-sl-questions', 'none.pdf')

@track_user_journey
def variables_and_input_sl(request):
    return render_math_topic(request, 'questionbank/computer_science/sl/variables_and_input_sl.html', 'variables_input', 'Variables and Input', 'Computer Science SL', 'comp-sci-sl-questions', 'none.pdf')

@track_user_journey
def if_statements_sl(request):
    return render_math_topic(request, 'questionbank/computer_science/sl/if_statements_sl.html', 'if_statements', 'If Statements', 'Computer Science SL', 'comp-sci-sl-questions', 'none.pdf')

@track_user_journey
def loops_sl(request):
    return render_math_topic(request, 'questionbank/computer_science/sl/loops_sl.html', 'loops', 'Loops', 'Computer Science SL', 'comp-sci-sl-questions', 'none.pdf')

@track_user_journey
def arrays_sl(request):
    return render_math_topic(request, 'questionbank/computer_science/sl/arrays_sl.html', 'arrays', 'Arrays', 'Computer Science SL', 'comp-sci-sl-questions', 'none.pdf')

@track_user_journey
def methods_sl(request):
    return render_math_topic(request, 'questionbank/computer_science/sl/methods_sl.html', 'methods', 'Methods', 'Computer Science SL', 'comp-sci-sl-questions', 'none.pdf')

@track_user_journey
def constructors_sl(request):
    return render_math_topic(request, 'questionbank/computer_science/sl/constructors_sl.html', 'constructors', 'Constructors', 'Computer Science SL', 'comp-sci-sl-questions', 'none.pdf')

@track_user_journey
def oop_sl(request):
    return render_math_topic(request, 'questionbank/computer_science/sl/oop_sl.html', 'oop', 'OOP', 'Computer Science SL', 'comp-sci-sl-questions', 'none.pdf')


########################################################
# COMPUTER SCIENCE SL PAST PAPERS
########################################################

@track_user_journey
def comp_sci_sl_past_papers(request):
    return render(request, 'comp_sci_sl_past_papers.html')

def comp_sci_sl_may22tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Comp_Sci_SL, 'comp_sci_sl_may22tz1p1.html', "May 2022", "1", "1")

def comp_sci_sl_may23tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Comp_Sci_SL, 'comp_sci_sl_may23tz1p1.html', "May 2023", "1", "1")

def comp_sci_sl_may24tz1p2(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Comp_Sci_SL, 'comp_sci_sl_may24tz1p2.html', "May 2024", "1", "2")

########################################################
# COMP SCI HL QUESTIONBANK
########################################################

class CompSciHLQuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = Comp_Sci_HL_QuestionbankSerializer

    def get_queryset(self):
        queryset = Comp_Sci_HL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')
        completed = self.request.GET.get('completed')
        marked = self.request.GET.get('marked')
        intersection = self.request.GET.get('intersection')

        # Support multiple papers
        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        # Support multiple difficulties
        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            queryset = queryset.filter(chapter__iexact=chapter)

        # Special ordering for ALL Computer Science HL chapters for non-registered users
        if chapter:
            # Check if user is registered
            is_authenticated = self.request.session.get('already_registered', False)
            
            if not is_authenticated:
                # For non-registered users, order: Free, Registered, Premium
                from django.db.models import Case, When, Value, IntegerField
                queryset = queryset.annotate(
                    type_order=Case(
                        When(type='free', then=Value(1)),
                        When(type='registered', then=Value(2)),
                        When(type='premium', then=Value(3)),
                        default=Value(4),
                        output_field=IntegerField()
                    )
                ).order_by('type_order', 'id')  # Secondary sort by id for consistency
            else:
                # For registered users, use default ordering (by id)
                queryset = queryset.order_by('id')
        else:
            # For no chapter specified, use default ordering
            queryset = queryset.order_by('id')

        # Handle progress filters (completed, marked, or intersection)
        if completed == 'true' or marked == 'true' or intersection == 'true':
            # Get user email from session
            user_email = self.request.session.get('email')
            if user_email:
                try:
                    from .models import UserQuestionProgress
                    import json
                    user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                    completed_ids = json.loads(user_progress.comp_sci_hl_completed) if completed == 'true' or intersection == 'true' else []
                    marked_ids = json.loads(user_progress.comp_sci_hl_marked) if marked == 'true' or intersection == 'true' else []
                    
                    # Determine which IDs to filter by
                    if intersection == 'true':
                        # Intersection: questions that are both completed AND marked
                        target_ids = list(set(completed_ids) & set(marked_ids))
                    elif completed == 'true':
                        # Only completed
                        target_ids = completed_ids
                    elif marked == 'true':
                        # Only marked
                        target_ids = marked_ids
                    else:
                        target_ids = []
                    
                    if target_ids:
                        # Apply progress filter to the already-filtered queryset
                        # This preserves any existing difficulty, paper, and chapter filters
                        queryset = queryset.filter(id__in=target_ids)
                    else:
                        # If no target questions, return empty queryset
                        queryset = queryset.none()
                except UserQuestionProgress.DoesNotExist:
                    # If no progress record, return empty queryset
                    queryset = queryset.none()
            else:
                # If not logged in, return empty queryset
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        # Get the filtered queryset
        queryset = self.get_queryset()
        
        # Get the chapter parameter
        chapter = request.GET.get('chapter')
        
        # Get user authentication status
        user_logged_in = request.session.get('already_registered', False)
        user_type = request.session.get('user_type', 'free')
        
        # Derive available filters from the current queryset (respecting chapter and other filters)
        available_papers = list(
            queryset.order_by().values_list('paper', flat=True).distinct()
        )
        available_difficulties = list(
            queryset.order_by().values_list('difficulty', flat=True).distinct()
        )
        
        # Serialize the queryset
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        # Apply custom ordering for all Computer Science HL chapters
        if chapter:
            questions_data = self.apply_custom_ordering(questions_data, user_logged_in, user_type)
        
        # Return custom response format
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })

@track_user_journey
def comp_sci_hl(request):
    return render(request, 'questionbank/computer_science/hl/comp_sci_hl.html')

@track_user_journey
def system_fundamentals_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/system_fundamentals_hl.html', 'system_fundamentals', 'System Fundamentals', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def computer_organisation_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/computer_organisation_hl.html', 'computer_organisation', 'Computer Organisation', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def networks_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/networks_hl.html', 'networks', 'Networks', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def computational_thinking_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/computational_thinking_hl.html', 'computational_thinking', 'Computational Thinking', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def variables_and_input_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/variables_and_input_hl.html', 'variables_input', 'Variables and Input', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def if_statements_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/if_statements_hl.html', 'if_statements', 'If Statements', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def loops_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/loops_hl.html', 'loops', 'Loops', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def arrays_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/arrays_hl.html', 'arrays', 'Arrays', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def methods_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/methods_hl.html', 'methods', 'Methods', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def constructors_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/constructors_hl.html', 'constructors', 'Constructors', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def resource_management_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/resource_management_hl.html', 'resource_management', 'Resource Management', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def abstract_data_structures_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/abstract_data_structures_hl.html', 'abstract_data_structures', 'Abstract Data Structures', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

@track_user_journey
def oop_hl(request):
    return render_math_topic(request, 'questionbank/computer_science/hl/oop_hl.html', 'oop', 'OOP', 'Computer Science HL', 'comp-sci-hl-questions', 'none.pdf')

########################################################
# COMPUTER SCIENCE HL PAST PAPERS
########################################################

@track_user_journey
def comp_sci_hl_past_papers(request):
    return render(request, 'comp_sci_hl_past_papers.html')

def comp_sci_hl_may23tz1p1(request):
    return render_past_papers_videos(request, Past_Paper_Videos_Comp_Sci_HL, 'comp_sci_hl_may23tz1p1.html', "May 2023", "1", "1")



########################################################
# EXAM BUILDER
########################################################

def exam_builder_landing(request):
    """
    Landing page for exam builder - choose between questionbank or past papers
    """
    # Get user session information
    user_logged_in = request.session.get("already_registered", False)
    user_type = request.session.get("user_type", "free")
    user_email = request.session.get("email")
    is_apex_user = request.session.get("is_apex_user", False)
    
    # Get user object if logged in (check both Users and ApexUsers)
    user = None
    is_tutor = False
    is_admin = False
    if user_logged_in and user_email:
        if is_apex_user:
            try:
                user = ApexUsers.objects.get(email=user_email)
                is_tutor = user.occupation and user.occupation.lower() == 'tutor'
                is_admin = user.occupation and user.occupation.lower() in ['admin', 'adminexternal']
            except ApexUsers.DoesNotExist:
                user = None
        else:
            try:
                user = Users.objects.get(email=user_email)
                is_tutor = user.occupation and user.occupation.lower() == 'tutor'
                is_admin = user.occupation and user.occupation.lower() == 'admin'
            except Users.DoesNotExist:
                user = None
    
    # Check if user has access to past papers (Premium OR Tutor OR Admin)
    has_past_papers_access = user_type == 'premium' or is_tutor or is_admin
    
    context = {
        'user_logged_in': user_logged_in,
        'user_type': user_type,
        'user': user,
        'has_past_papers_access': has_past_papers_access,
    }
    
    return render(request, 'exam_builder_landing.html', context)


def exam_builder_questionbank(request):
    """
    Exam builder for questionbank questions (existing functionality)
    """
    # Get user session information
    user_logged_in = request.session.get("already_registered", False)
    user_type = request.session.get("user_type", "free")
    user_email = request.session.get("email")
    is_apex_user = request.session.get("is_apex_user", False)
    
    # Get user object if logged in (check both Users and ApexUsers)
    user = None
    if user_logged_in and user_email:
        if is_apex_user:
            try:
                user = ApexUsers.objects.get(email=user_email)
            except ApexUsers.DoesNotExist:
                user = None
        else:
            try:
                user = Users.objects.get(email=user_email)
            except Users.DoesNotExist:
                user = None
    
    # Handle AJAX request for topics
    if request.GET.get('get_topics') == 'true':
        subject = request.GET.get('subject')
        subject_model_map = {
            'math_aa_sl': Math_AA_SL_Questionbank,
            'math_aa_hl': Math_AA_HL_Questionbank,
            'math_ai_sl': Math_AI_SL_Questionbank,
            'math_ai_hl': Math_AI_HL_Questionbank,
            'comp_sci_sl': Comp_Sci_SL_Questionbank,
            'comp_sci_hl': Comp_Sci_HL_Questionbank,
            'biology_sl': Biology_SL_Questionbank,
            'biology_hl': Biology_HL_Questionbank,
            'physics_sl': Physics_SL_Questionbank,
            'physics_hl': Physics_HL_Questionbank,
        }
        model = subject_model_map.get(subject)
        topics = []
        if model and hasattr(model, 'CHAPTERS'):
            topics = [
                {'value': chapter[0], 'label': chapter[1]} 
                for chapter in model.CHAPTERS 
                if chapter[0] and chapter[0] not in ['', 'null']
            ]
        return JsonResponse({'topics': topics})
    
    # Initialize questions as empty
    questions = []
    selected_subject = None
    selected_papers = []
    selected_topics = []
    selected_difficulties = []
    selected_status = None
    selected_time = None
    error_message = None
    warning_message = None
    available_topics = []
    total_marks = 0
    actual_time = 0
    
    # Check if this is a build request (has GET parameters)
    if request.GET.get('subject'):
        selected_subject = request.GET.get('subject')
        selected_papers = request.GET.getlist('paper')  # Get multiple papers
        selected_topics = request.GET.getlist('topic')  # Get multiple topics
        selected_difficulties = request.GET.getlist('difficulty')  # Get multiple difficulties
        selected_status = request.GET.get('status', 'all')
        selected_time = int(request.GET.get('time', 60))
        
        # Check if specific question IDs are provided (from exam_answers back button)
        question_ids_str = request.GET.get('question_ids', '')
        if question_ids_str:
            # User is returning from exam answers - use the exact same questions
            try:
                question_ids = [int(id.strip()) for id in question_ids_str.split(',') if id.strip()]
            except ValueError:
                question_ids = []
        else:
            question_ids = []
        
        # Define time-to-marks conversion for each subject and paper
        # Format: {subject: {paper: (total_minutes, total_marks)}}
        time_marks_conversion = {
            'math_aa_hl': {
                'paper1': (120, 110),  # 2 hours for 110 marks
                'paper2': (120, 110),  # 2 hours for 110 marks
            },
            'math_aa_sl': {
                'paper1': (90, 80),    # 90 minutes for 80 marks
                'paper2': (90, 80),    # 90 minutes for 80 marks
            },
            'math_ai_hl': {
                'paper1': (120, 110),  # 2 hours for 110 marks
                'paper2': (120, 110),  # 2 hours for 110 marks
            },
            'math_ai_sl': {
                'paper1': (90, 80),    # 90 minutes for 80 marks
                'paper2': (90, 80),    # 90 minutes for 80 marks
            },
            'comp_sci_hl': {
                'paper1': (130, 100),  # 2 hours 10 minutes for 100 marks
                'paper2': (80, 65),    # 1 hour 20 minutes for 65 marks
            },
            'comp_sci_sl': {
                'paper1': (90, 70),    # 1.5 hours for 70 marks
                'paper2': (60, 45),    # 1 hour for 45 marks
            },
            'biology_sl': {
                'paper1A': (49, 30),   # 49 minutes for 30 marks (multiple choice)
                'paper1B': (41, 25),   # 41 minutes for 25 marks (multiple choice)
                'paper2': (90, 50),    # 90 minutes for 50 marks
            },
            'biology_hl': {
                'paper1A': (64, 40),   # 64 minutes for 40 marks (multiple choice)
                'paper1B': (56, 35),   # 56 minutes for 35 marks (multiple choice)
                'paper2': (150, 80),   # 150 minutes (2.5 hours) for 80 marks
            },
            'physics_sl': {
                'paper1A': (50, 25),   # 50 minutes for 25 marks (multiple choice)
                'paper1B': (40, 20),   # 40 minutes for 20 marks
                'paper2': (90, 50),    # 90 minutes for 50 marks
            },
            'physics_hl': {
                'paper1A': (80, 40),   # 80 minutes for 40 marks (multiple choice)
                'paper1B': (40, 20),   # 40 minutes for 20 marks
                'paper2': (150, 90),   # 150 minutes (2.5 hours) for 90 marks
            },
        }
        
        def calculate_time_for_question(question):
            """Calculate time in minutes for a question based on its paper type and marks"""
            try:
                marks = int(question.marks) if question.marks else 0
            except (ValueError, TypeError):
                marks = 0
            
            if marks == 0:
                return 0
            
            # Get conversion ratio for this subject and paper
            if selected_subject in time_marks_conversion:
                paper_key = question.paper
                if paper_key in time_marks_conversion[selected_subject]:
                    total_minutes, total_marks = time_marks_conversion[selected_subject][paper_key]
                    # Calculate minutes per mark for this paper
                    minutes_per_mark = total_minutes / total_marks
                    return marks * minutes_per_mark
            
            # Default: 1 mark = 1 minute
            return marks
        
        # Use exact target time (no range)
        target_time = selected_time
        
        # Map subject to model
        subject_model_map = {
            'math_aa_sl': Math_AA_SL_Questionbank,
            'math_aa_hl': Math_AA_HL_Questionbank,
            'math_ai_sl': Math_AI_SL_Questionbank,
            'math_ai_hl': Math_AI_HL_Questionbank,
            'comp_sci_sl': Comp_Sci_SL_Questionbank,
            'comp_sci_hl': Comp_Sci_HL_Questionbank,
            'biology_sl': Biology_SL_Questionbank,
            'biology_hl': Biology_HL_Questionbank,
            'physics_sl': Physics_SL_Questionbank,
            'physics_hl': Physics_HL_Questionbank,
        }
        
        model = subject_model_map.get(selected_subject)
        
        if model:
            # If specific question IDs are provided, use them directly
            if question_ids:
                # Get questions in the order they were provided (from exam_answers)
                questions_dict = {q.id: q for q in model.objects.filter(id__in=question_ids)}
                selected_questions = [questions_dict[id] for id in question_ids if id in questions_dict]
                questions = selected_questions
                
                # Calculate total marks and time for these questions
                total_marks = sum(int(q.marks) if q.marks else 0 for q in questions)
                actual_time = selected_time  # Use the provided time
            else:
                # Build a new exam based on filters
                # Start with base queryset
                queryset = model.objects.all()
                
                # Apply question type filter based on user type
                if user_type == 'premium':
                    # Premium users get all questions
                    pass
                else:
                    # Registered (non-premium) users get only 'free' and 'registered' questions
                    queryset = queryset.filter(type__in=['free', 'registered'])
                
                # Filter by papers if selected
                if selected_papers:
                    queryset = queryset.filter(paper__in=selected_papers)
                else:
                    # If no papers selected (Any), include appropriate papers for each subject
                    if selected_subject in ['biology_sl', 'biology_hl', 'physics_sl', 'physics_hl']:
                        # For Biology and Physics, include Paper 1A, 1B, and 2
                        queryset = queryset.filter(paper__in=['paper1A', 'paper1B', 'paper2'])
                    else:
                        # For other subjects, only include Paper 1 and Paper 2
                        queryset = queryset.filter(paper__in=['paper1', 'paper2'])
                
                # Filter by topics if selected
                if selected_topics:
                    queryset = queryset.filter(chapter__in=selected_topics)
                
                # Filter by difficulties if selected
                if selected_difficulties:
                    queryset = queryset.filter(difficulty__in=selected_difficulties)
                
                # Apply status filter if not "all"
                if selected_status != 'all' and user_email:
                    # Map subject to field names in UserQuestionProgress
                    field_map = {
                        'math_aa_sl': ('math_aa_sl_completed', 'math_aa_sl_marked'),
                        'math_aa_hl': ('math_aa_hl_completed', 'math_aa_hl_marked'),
                        'math_ai_sl': ('math_ai_sl_completed', 'math_ai_sl_marked'),
                        'math_ai_hl': ('math_ai_hl_completed', 'math_ai_hl_marked'),
                        'comp_sci_sl': ('comp_sci_sl_completed', 'comp_sci_sl_marked'),
                        'comp_sci_hl': ('comp_sci_hl_completed', 'comp_sci_hl_marked'),
                        'biology_sl': ('biology_sl_completed', 'biology_sl_marked'),
                        'biology_hl': ('biology_hl_completed', 'biology_hl_marked'),
                        'physics_sl': ('physics_sl_completed', 'physics_sl_marked'),
                        'physics_hl': ('physics_hl_completed', 'physics_hl_marked'),
                    }
                    
                    fields = field_map.get(selected_subject)
                    if fields:
                        try:
                            user_progress = UserQuestionProgress.objects.get(user_email=user_email)
                            
                            # Get completed and marked IDs from JSON fields
                            completed_field, marked_field = fields
                            completed_ids = json.loads(getattr(user_progress, completed_field, '[]'))
                            marked_ids = json.loads(getattr(user_progress, marked_field, '[]'))
                            
                            if selected_status == 'exclude_completed':
                                # Exclude completed questions
                                queryset = queryset.exclude(id__in=completed_ids)
                            elif selected_status == 'exclude_marked':
                                # Exclude marked questions
                                queryset = queryset.exclude(id__in=marked_ids)
                            elif selected_status == 'exclude_both':
                                # Exclude both completed and marked questions
                                all_excluded_ids = list(set(completed_ids + marked_ids))
                                queryset = queryset.exclude(id__in=all_excluded_ids)
                        except UserQuestionProgress.DoesNotExist:
                            # User has no progress, so no questions to exclude
                            pass
                
                # Get all questions with marks
                all_questions = list(queryset.exclude(marks__isnull=True).exclude(marks=0))
                
                if all_questions:
                    # Build an exam that matches the exact target time
                    import random
                    random.shuffle(all_questions)
                    
                    selected_questions = []
                    current_time = 0
                    
                    # Keep adding questions until we reach the exact target time
                    for question in all_questions:
                        question_time = calculate_time_for_question(question)
                        
                        # Keep adding questions as long as we haven't exceeded the target
                        if current_time + question_time <= target_time:
                            selected_questions.append(question)
                            current_time += question_time
                        
                        # Stop if we've reached exactly the target time
                        if current_time >= target_time:
                            break
                    
                    questions = selected_questions
                    
                    # Calculate total marks and actual time for the selected questions
                    total_marks = 0
                    actual_time = 0
                    for q in questions:
                        try:
                            marks = int(q.marks) if q.marks else 0
                            total_marks += marks
                            actual_time += calculate_time_for_question(q)
                        except (ValueError, TypeError):
                            pass
                    
                    # Debug: Print the calculated values

                    
                    # Check if marks are 15% below what they should be for the selected time
                    # Calculate expected marks for the selected time based on the conversion ratio
                    if selected_subject in time_marks_conversion:
                        # Calculate the expected marks based on the papers selected
                        total_expected_time = 0
                        total_expected_marks = 0
                        
                        # If no papers selected (Any), use all available papers for the subject
                        papers_to_check = selected_papers if selected_papers else list(time_marks_conversion[selected_subject].keys())
                        
                        for paper in papers_to_check:
                            if paper in time_marks_conversion[selected_subject]:
                                paper_minutes, paper_marks = time_marks_conversion[selected_subject][paper]
                                total_expected_time += paper_minutes
                                total_expected_marks += paper_marks
                        
                        if total_expected_time > 0:
                            # Calculate marks per minute for selected papers
                            marks_per_minute = total_expected_marks / total_expected_time
                            
                            # Expected marks for the selected time
                            expected_marks = target_time * marks_per_minute
                            
                            # Check if actual marks are 15% below expected
                            if total_marks < expected_marks * 0.85:
                                warning_message = "The selected filters don't allow to create a full exam for the given time. Consider reducing the time or adjusting your filters."
                                # print(f"DEBUG: Expected marks: {expected_marks}, Actual marks: {total_marks}, 85% threshold: {expected_marks * 0.85}")
                    
                    if not questions:
                        error_message = f"Could not build an exam with {target_time} minutes. Try adjusting your filters or time."
                else:
                    error_message = "No questions found matching your criteria."
        else:
            error_message = "Invalid subject selected."
    
    # Get available topics for the selected subject
    if selected_subject:
        subject_model_map = {
            'math_aa_sl': Math_AA_SL_Questionbank,
            'math_aa_hl': Math_AA_HL_Questionbank,
            'math_ai_sl': Math_AI_SL_Questionbank,
            'math_ai_hl': Math_AI_HL_Questionbank,
            'comp_sci_sl': Comp_Sci_SL_Questionbank,
            'comp_sci_hl': Comp_Sci_HL_Questionbank,
        }
        model = subject_model_map.get(selected_subject)
        if model and hasattr(model, 'CHAPTERS'):
            # Get chapters list and convert to format for template
            available_topics = [
                {'value': chapter[0], 'label': chapter[1]} 
                for chapter in model.CHAPTERS 
                if chapter[0] and chapter[0] not in ['', 'null']
            ]
    
    # Prepare conversion info for display
    conversion_info = {}
    if selected_subject:
        # Define the same conversion dictionary for template use
        time_marks_conversion = {
            'math_aa_hl': {
                'paper1': (120, 110),
                'paper2': (120, 110),
            },
            'math_aa_sl': {
                'paper1': (90, 80),
                'paper2': (90, 80),
            },
            'math_ai_hl': {
                'paper1': (120, 110),
                'paper2': (120, 110),
            },
            'math_ai_sl': {
                'paper1': (90, 80),
                'paper2': (90, 80),
            },
            'comp_sci_hl': {
                'paper1': (130, 100),
                'paper2': (80, 65),
            },
            'comp_sci_sl': {
                'paper1': (90, 70),
                'paper2': (60, 45),
            },
            'biology_sl': {
                'paper1A': (49, 30),
                'paper1B': (41, 25),
                'paper2': (90, 50),
            },
            'biology_hl': {
                'paper1A': (64, 40),
                'paper1B': (56, 35),
                'paper2': (150, 80),
            },
            'physics_sl': {
                'paper1A': (50, 25),
                'paper1B': (40, 20),
                'paper2': (90, 50),
            },
            'physics_hl': {
                'paper1A': (80, 40),
                'paper1B': (40, 20),
                'paper2': (150, 90),
            },
        }
        
        if selected_subject in time_marks_conversion:
            # For Biology and Physics subjects, check paper1A, paper1B, paper2
            if selected_subject in ['biology_sl', 'biology_hl', 'physics_sl', 'physics_hl']:
                papers_to_check = ['paper1A', 'paper1B', 'paper2']
            else:
                # For other subjects, check paper1, paper2
                papers_to_check = ['paper1', 'paper2']
            
            for paper in papers_to_check:
                if paper in time_marks_conversion[selected_subject]:
                    total_minutes, total_marks_for_paper = time_marks_conversion[selected_subject][paper]
                    minutes_per_mark = total_minutes / total_marks_for_paper
                    conversion_info[paper] = {
                        'minutes_per_mark': round(minutes_per_mark, 2),
                        'total_minutes': total_minutes,
                        'total_marks': total_marks_for_paper,
                    }
    
    context = {
        'user_logged_in': user_logged_in,
        'user_type': user_type,
        'user': user,
        'questions': questions,
        'selected_subject': selected_subject,
        'selected_papers': selected_papers,
        'selected_topics': selected_topics,
        'selected_difficulties': selected_difficulties,
        'selected_status': selected_status,
        'selected_time': selected_time,
        'error_message': error_message,
        'warning_message': warning_message,
        'total_marks': total_marks,
        'actual_time': selected_time if selected_time else 0,  # Display exact selected time, not calculated
        'available_topics': available_topics,
        'conversion_info': conversion_info,
    }
    
    return render(request, 'exam_builder_questionbank.html', context)


def exam_builder_past_papers(request):
    """
    Past papers PDF generator - Premium, Tutors, and Admins
    """
    # Get user session information
    user_logged_in = request.session.get("already_registered", False)
    user_type = request.session.get("user_type", "free")
    user_email = request.session.get("email")
    is_apex_user = request.session.get("is_apex_user", False)
    
    # Get user object if logged in (check both Users and ApexUsers)
    user = None
    is_tutor = False
    is_admin = False
    if user_logged_in and user_email:
        if is_apex_user:
            try:
                user = ApexUsers.objects.get(email=user_email)
                is_tutor = user.occupation and user.occupation.lower() == 'tutor'
                is_admin = user.occupation and user.occupation.lower() in ['admin', 'adminexternal']
            except ApexUsers.DoesNotExist:
                user = None
        else:
            try:
                user = Users.objects.get(email=user_email)
                is_tutor = user.occupation and user.occupation.lower() == 'tutor'
                is_admin = user.occupation and user.occupation.lower() == 'admin'
            except Users.DoesNotExist:
                user = None
    
    # Check access: Premium OR Tutor OR Admin
    has_access = user_type == 'premium' or is_tutor or is_admin
    
    if not has_access:
        # Redirect to landing page with error
        messages.error(request, 'Past Papers PDF Generator is available for Premium members, Tutors, and Admins.')
        return redirect('exam-builder')
    
    # For PDF download purposes, both tutors and admins can download
    # Apex users should NOT be able to download, they see modal preview
    can_download = (is_tutor or is_admin) and not is_apex_user
    
    context = {
        'user_logged_in': user_logged_in,
        'user_type': user_type,
        'user': user,
        'is_tutor': can_download,  # This includes both tutors and admins for download capability (but not Apex)
    }
    
    return render(request, 'exam_builder_past_papers.html', context)


# Legacy support - redirect old exam-builder URL to questionbank
def exam_builder(request):
    """Legacy redirect"""
    return exam_builder_landing(request)

def exam_answers(request):
    """Display answers for exam builder questions"""
    # Get user info from session (using the same keys as context_processors.py)
    user_logged_in = request.session.get('already_registered', False)
    user_type = request.session.get('user_type', 'free') if user_logged_in else 'none'
    user_email = request.session.get('email', '')
    is_apex_user = request.session.get('is_apex_user', False)
    
    # Get user object (check both Users and ApexUsers)
    user = None
    if user_email:
        if is_apex_user:
            try:
                user = ApexUsers.objects.get(email=user_email)
            except ApexUsers.DoesNotExist:
                pass
        else:
            try:
                user = Users.objects.get(email=user_email)
            except Users.DoesNotExist:
                pass
    
    # Get parameters from URL
    subject = request.GET.get('subject')
    question_ids_str = request.GET.get('question_ids', '')
    
    # Get exam builder parameters to pass back for the "Back" button
    papers = request.GET.getlist('paper')
    topics = request.GET.getlist('topic')
    difficulties = request.GET.getlist('difficulty')
    status = request.GET.get('status', '')
    time = request.GET.get('time', '')
    
    questions = []
    error_message = None
    
    if subject and question_ids_str:
        # Parse question IDs
        try:
            question_ids = [int(id.strip()) for id in question_ids_str.split(',') if id.strip()]
        except ValueError:
            error_message = "Invalid question IDs provided."
            question_ids = []
        
        if question_ids:
            # Map subject to model
            subject_model_map = {
                'math_aa_sl': Math_AA_SL_Questionbank,
                'math_aa_hl': Math_AA_HL_Questionbank,
                'math_ai_sl': Math_AI_SL_Questionbank,
                'math_ai_hl': Math_AI_HL_Questionbank,
                'comp_sci_sl': Comp_Sci_SL_Questionbank,
                'comp_sci_hl': Comp_Sci_HL_Questionbank,
                'biology_sl': Biology_SL_Questionbank,
                'biology_hl': Biology_HL_Questionbank,
                'physics_sl': Physics_SL_Questionbank,
                'physics_hl': Physics_HL_Questionbank,
            }
            
            model = subject_model_map.get(subject)
            
            if model:
                # Get questions in the order they were provided
                questions_dict = {q.id: q for q in model.objects.filter(id__in=question_ids)}
                questions = [questions_dict[id] for id in question_ids if id in questions_dict]
            else:
                error_message = "Invalid subject selected."
    else:
        error_message = "No questions to display. Please build an exam first."
    
    # Serialize questions to JSON for JavaScript
    questions_json = json.dumps([{
        'id': q.id,
        'question': q.question,
        'answer': q.answer,
        'correct_answer': q.correct_answer if hasattr(q, 'correct_answer') else '',
        'difficulty': q.difficulty,
        'paper': q.paper,
        'marks': q.marks if hasattr(q, 'marks') else None,
        'video_url': q.video if hasattr(q, 'video') else 'none',
    } for q in questions])
    
    # Build query string for back button
    back_params = []
    if subject:
        back_params.append(f'subject={subject}')
    for paper in papers:
        back_params.append(f'paper={paper}')
    for topic in topics:
        back_params.append(f'topic={topic}')
    for difficulty in difficulties:
        back_params.append(f'difficulty={difficulty}')
    if status:
        back_params.append(f'status={status}')
    if time:
        back_params.append(f'time={time}')
    if question_ids_str:
        back_params.append(f'question_ids={question_ids_str}')
    
    back_url = '/exam-builder/?' + '&'.join(back_params) if back_params else '/exam-builder/'
    
    context = {
        'user_logged_in': user_logged_in,
        'user_type': user_type,
        'user': user,
        'questions': questions,
        'questions_json': questions_json,
        'subject': subject,
        'error_message': error_message,
        'back_url': back_url,
    }
    
    return render(request, 'exam_answers.html', context)

########################################################
# QUESTION STATUS API ENDPOINTS
########################################################

@csrf_exempt
def update_question_status(request):
    """Update user's question completion/marking status"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_email = data.get('user_email')
        question_id = data.get('question_id')
        subject = data.get('subject')  # e.g., 'math_ai_sl'
        status_type = data.get('status_type')  # 'completed' or 'marked'
        action = data.get('action')  # 'add' or 'remove'
        
        if not all([user_email, question_id, subject, status_type, action]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Map db_name to model field format
        subject_mapping = {
            'math-ai-sl-questions': 'math_ai_sl',
            'math-ai-hl-questions': 'math_ai_hl',
            'math-aa-sl-questions': 'math_aa_sl',
            'math-aa-hl-questions': 'math_aa_hl',
            'physics-sl-questions': 'physics_sl',
            'physics-hl-questions': 'physics_hl',
            'chemistry-sl-questions': 'chemistry_sl',
            'chemistry-hl-questions': 'chemistry_hl',
            'biology-sl-questions': 'biology_sl',
            'biology-hl-questions': 'biology_hl',
            'comp-sci-sl-questions': 'comp_sci_sl',
            'comp-sci-hl-questions': 'comp_sci_hl',
        }
        
        # Convert subject to model field format
        model_subject = subject_mapping.get(subject, subject)
        
        # Get or create user progress record
        progress, created = UserQuestionProgress.objects.get_or_create(
            user_email=user_email,
            defaults={}
        )
        
        # Get the current list for the subject and status type
        field_name = f"{model_subject}_{status_type}"
        if not hasattr(progress, field_name):
            return JsonResponse({'error': 'Invalid subject or status type'}, status=400)
        
        current_list = json.loads(getattr(progress, field_name) or '[]')
        question_id = int(question_id)
        
        if action == 'add':
            if question_id not in current_list:
                current_list.append(question_id)
        elif action == 'remove':
            if question_id in current_list:
                current_list.remove(question_id)
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        # Update the field
        setattr(progress, field_name, json.dumps(current_list))
        progress.save()
        
        return JsonResponse({
            'success': True,
            'status': status_type,
            'action': action,
            'question_id': question_id,
            'updated_list': current_list
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def debug_user_progress(request):
    """Debug endpoint to check user progress data"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    user_email = request.session.get('email')
    if not user_email:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    
    try:
        from .models import UserQuestionProgress
        import json
        user_progress = UserQuestionProgress.objects.get(user_email=user_email)
        
        completed_ids = json.loads(user_progress.math_ai_sl_completed)
        marked_ids = json.loads(user_progress.math_ai_sl_marked)
        
        # Check if any of these questions exist in the database
        from .models import Math_AI_SL_Questionbank
        existing_completed = Math_AI_SL_Questionbank.objects.filter(id__in=completed_ids)
        existing_marked = Math_AI_SL_Questionbank.objects.filter(id__in=marked_ids)
        
        return JsonResponse({
            'user_email': user_email,
            'completed_ids': completed_ids,
            'marked_ids': marked_ids,
            'existing_completed_count': existing_completed.count(),
            'existing_marked_count': existing_marked.count(),
            'existing_completed_details': [
                {'id': q.id, 'chapter': q.chapter, 'paper': q.paper, 'difficulty': q.difficulty}
                for q in existing_completed
            ],
            'existing_marked_details': [
                {'id': q.id, 'chapter': q.chapter, 'paper': q.paper, 'difficulty': q.difficulty}
                for q in existing_marked
            ]
        })
    except UserQuestionProgress.DoesNotExist:
        return JsonResponse({'error': 'No progress record found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def get_question_status(request):
    """Get user's question status for a specific subject"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        user_email = request.GET.get('user_email')
        subject = request.GET.get('subject')
        
        if not user_email or not subject:
            return JsonResponse({'error': 'Missing user_email or subject'}, status=400)
        
        # Map db_name to model field format
        subject_mapping = {
            'math-ai-sl-questions': 'math_ai_sl',
            'math-ai-hl-questions': 'math_ai_hl',
            'math-aa-sl-questions': 'math_aa_sl',
            'math-aa-hl-questions': 'math_aa_hl',
            'physics-sl-questions': 'physics_sl',
            'physics-hl-questions': 'physics_hl',
            'chemistry-sl-questions': 'chemistry_sl',
            'chemistry-hl-questions': 'chemistry_hl',
            'biology-sl-questions': 'biology_sl',
            'biology-hl-questions': 'biology_hl',
            'comp-sci-sl-questions': 'comp_sci_sl',
            'comp-sci-hl-questions': 'comp_sci_hl',
        }
        
        # Convert subject to model field format
        model_subject = subject_mapping.get(subject, subject)
        
        try:
            progress = UserQuestionProgress.objects.get(user_email=user_email)
        except UserQuestionProgress.DoesNotExist:
            return JsonResponse({
                'completed': [],
                'marked': []
            })
        
        completed_field = f"{model_subject}_completed"
        marked_field = f"{model_subject}_marked"
        
        completed = json.loads(getattr(progress, completed_field, '[]'))
        marked = json.loads(getattr(progress, marked_field, '[]'))
        
        return JsonResponse({
            'completed': completed,
            'marked': marked
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def report_question_problem(request):
    """Email staff when a user reports an issue with a questionbank question."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        subject = (data.get('subject') or '').strip()
        question_id = data.get('question_id')
        message = (data.get('message') or '').strip()
        topic = (data.get('topic') or '').strip()

        if not subject or not question_id or not message:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        if len(message) > 5000:
            return JsonResponse({'error': 'Message too long'}, status=400)

        reporter_email = (
            (data.get('user_email') or '').strip()
            or request.session.get('email')
            or 'Anonymous'
        )

        email_body = (
            f"A user reported a problem with a question.\n\n"
            f"Subject: {subject}\n"
            f"Question ID: {question_id}\n"
            f"Topic: {topic or 'N/A'}\n"
            f"Reported by: {reporter_email}\n\n"
            f"Complaint:\n{message}\n"
        )

        send_mail(
            subject=f'Question report: {subject} — Q{question_id}',
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=settings.QUESTION_REPORT_RECIPIENTS,
            fail_silently=False,
        )

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except BadHeaderError:
        return JsonResponse({'error': 'Invalid email header'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Question Editor Views
def question_editor(request):
    """View for the question editor interface"""
    return render(request, 'question_editor.html')

def question_maker(request):
    """View for the question maker interface"""
    return render(request, 'question_maker.html')


@method_decorator(csrf_exempt, name='dispatch')
class UpdateQuestionAPIView(View):
    """API view to update question metadata and content"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            subject = data.get('subject')
            question_id = data.get('id')
            
            # Map subject to model
            model_mapping = {
                'math_ai_hl': Math_AI_HL_Questionbank,
                'math_ai_sl': Math_AI_SL_Questionbank,
                'math_aa_hl': Math_AA_HL_Questionbank,
                'math_aa_hl_backup': Math_AA_HL_Questionbank_Backup,
                'math_aa_sl': Math_AA_SL_Questionbank,
                'biology_hl': Biology_HL_Questionbank,
                'biology_sl': Biology_SL_Questionbank,
                'physics_hl': Physics_HL_Questionbank,
                'physics_sl': Physics_SL_Questionbank,
                'comp_sci_hl': Comp_Sci_HL_Questionbank,
                'comp_sci_sl': Comp_Sci_SL_Questionbank,
            }
            
            if subject not in model_mapping:
                return JsonResponse({'success': False, 'error': 'Invalid subject'})
            
            model_class = model_mapping[subject]
            
            try:
                question = model_class.objects.get(id=question_id)
            except model_class.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Question not found'})
            
            # Update fields
            if 'paper' in data:
                question.paper = data['paper']
            if 'difficulty' in data:
                question.difficulty = data['difficulty']
            if 'type' in data:
                question.type = data['type']
            if 'marks' in data and data['marks']:
                question.marks = data['marks']
            if 'question' in data:
                question.question = data['question']
            if 'answer' in data:
                question.answer = data['answer']
            # Update correct_answer field for Biology and Physics subjects
            if 'correct_answer' in data and subject in ['biology_sl', 'biology_hl', 'physics_sl', 'physics_hl']:
                question.correct_answer = data['correct_answer']
                
            # Update chapter fields for Math AI SL
            if subject == 'math_ai_sl':
                if 'chapter' in data:
                    question.chapter = data['chapter']
                if 'chapter2' in data:
                    question.chapter2 = data['chapter2']
                if 'chapter3' in data:
                    question.chapter3 = data['chapter3']
            
            question.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Question updated successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        

@track_user_journey
def suitability_survey(request):
    context = {}

    # Check if user is registered (has email in session)
    email = request.session.get('email', '')
    
    # If user is not registered, show registration message
    if not email:
        context.update({
            'not_registered': True
        })
        return render(request, 'suitability_survey.html', context)
    
    # User is logged in, now check if they have survey results
    results = Fillout_Survey.objects.filter(email=email).order_by('-date').values().first()

    # If no survey results found
    if not results:
        context.update({
                'email': email,
                'no_results': True,
                'not_registered': False
            })
        return render(request, 'suitability_survey.html', context)

    context['no_results'] = False
    context['not_registered'] = False
    context['email'] = email  # Add email to context for retake survey button
    # User has survey results, process them
    economics = float(results.get('economics_score', 0))
    law = float(results.get('law_score', 0))
    medicine = float(results.get('medicine_score', 0))
    engineering = float(results.get('engineering_score', 0))
    creative = float(results.get('creative_score', 0))
    social = float(results.get('soc_sciences_score', 0))
    sciences = float(results.get('sciences_score', 0))
    human = float(results.get('humanities_score', 0))
    architect = float(results.get('architecture_score', 0))

    scores = {
        "Economics": economics,
        "Law": law,
        "Medicine": medicine,
        "Engineering": engineering,
        "Creative": creative,
        "Social Sciences": social,
        "Sciences": sciences,
        "Humanities": human,
        "Architecture": architect
    }

    percentages = {field: min((score / 25) * 100, 100) for field, score in scores.items()}

    # Sort by percentages in descending order
    sorted_percentages = sorted(percentages.items(), key=lambda x: x[1], reverse=True)

    # Get the top 3 fields
    top_3 = sorted_percentages[:3]

    # Extract names and percentages
    first_place, first_score = top_3[0]
    second_place, second_score = top_3[1]
    third_place, third_score = top_3[2]

    # Set profile descriptions based on the top disciplines
    profile_descriptions = {
        "Economics": "You think in numbers, patterns, and trends. You enjoy subjects like Economics, Business, and Math, and you're interested in how money moves in the world. You enjoy analyzing financial decisions, understanding markets, and figuring out ways to maximize value.",
        "Law": "You have a strong sense of justice and enjoy debates and logical reasoning. You're interested in how rules and regulations shape society, and you're good at analyzing arguments from different perspectives. You enjoy solving complex problems using established frameworks.",
        "Medicine": "You have a natural inclination to help others and an interest in how the human body works. You're methodical, detail-oriented, and have good memory. You're interested in health sciences and enjoy learning about biological systems.",
        "Engineering": "You enjoy solving practical problems using technical and scientific knowledge. You're logical, methodical, and enjoy understanding how things work. You're good at spatial reasoning and may enjoy building or taking things apart.",
        "Creative": "You have an artistic sensibility and enjoy expressing yourself through various media. You think outside the box and are comfortable with ambiguity. You notice aesthetic details others might miss and enjoy creating new things.",
        "Social Sciences": "You're fascinated by human behavior, societies, and cultures. You enjoy understanding why people do what they do and how groups interact. You're observant of social patterns and interested in how societies function.",
        "Sciences": "You have a naturally analytical mind and enjoy understanding the world through systematic inquiry. You're curious about natural phenomena and enjoy learning through experimentation. You're comfortable with abstract concepts and data analysis.",
        "Humanities": "You're interested in human culture, language, and expression. You enjoy analyzing texts, ideas, and historical contexts. You're good at making connections between different concepts and have strong communication skills.",
        "Architecture": "You have a unique blend of creative and analytical skills. You enjoy visualizing spaces and how they interact with people. You have good spatial reasoning and an eye for design while also appreciating technical precision."
    }


    profile_images = {
        "Economics": "https://www.clarkson.edu/sites/default/files/2023-06/Economics-Hero-1600x900.jpeg",
        "Law": "https://www.lawnow.org/wp-content/uploads/2021/11/pexels-ekaterina-bolovtsova-6077326.jpg",
        "Medicine": "https://www.sciencepharma.com/wp-content/uploads/2024/09/forms_drugs_baner_rf-scaled.jpg",
        "Engineering": "https://www.bmu.edu.in/wp-content/uploads/2025/02/Types-of-Engineering.webp",
        "Creative": "https://www.strategiclearning.asia/wp-content/uploads/2024/04/stimulate-creative-thinking.jpg",
        "Social Sciences": "https://www.worldatlas.com/r/w1200/upload/38/4f/7a/shutterstock-87113380.jpg",
        "Sciences": "https://platform.vox.com/wp-content/uploads/sites/2/chorus/uploads/chorus_asset/file/15414153/shutterstock_172355312.0.0.1435352379.jpg?quality=90&strip=all&crop=0%2C9.7745324109659%2C100%2C80.450935178068&w=2400",
        "Humanities": "https://eminence.edu.bd/wp-content/uploads/2021/10/HSC-in-Humanities-1024x565.jpg",
        "Architecture": "https://archimash.com/wp-content/uploads/2021/10/AM-021-A-What-To-Know-About-Practicing-Architecture-1280x720-BLANK.png"
    }
    
    # Get discipline degrees data
    first_degrees = []
    second_degrees = []
    third_degrees = []
    
    # Add degree data from discipline_data dictionary
    if first_place in discipline_data:
        for degree_name, degree_info in discipline_data[first_place]['degrees'].items():
            first_degrees.append({
                'name': degree_name,
                'description': degree_info['description'],
                'jobs': ', '.join(degree_info['jobs'])
            })
    
    if second_place in discipline_data:
        for degree_name, degree_info in discipline_data[second_place]['degrees'].items():
            second_degrees.append({
                'name': degree_name,
                'description': degree_info['description'],
                'jobs': ', '.join(degree_info['jobs'])
            })
    
    if third_place in discipline_data:
        for degree_name, degree_info in discipline_data[third_place]['degrees'].items():
            third_degrees.append({
                'name': degree_name,
                'description': degree_info['description'],
                'jobs': ', '.join(degree_info['jobs'])
            })
    
    # Add degree data to context
    context['first_place'] = first_place
    context['first_score'] = int(first_score)
    context['second_place'] = second_place
    context['second_score'] = int(second_score)
    context['third_place'] = third_place
    context['third_score'] = int(third_score)
    context['first_description'] = profile_descriptions.get(first_place, "")
    context['second_description'] = profile_descriptions.get(second_place, "")
    context['third_description'] = profile_descriptions.get(third_place, "")
    context['first_degrees'] = first_degrees
    context['second_degrees'] = second_degrees
    context['third_degrees'] = third_degrees
    context['first_image'] = profile_images.get(first_place, "")



    
    # Getting information about proposed universities
    business_unis = list(Uni_Database.objects.filter(
        discipline_survey__icontains=first_place, 
        # tuition_fee_euro__lte=float(results.get('uni_cost', 0)),
        ib_requirements__lt=float(results.get('grades', 0)) + 5,
        ib_requirements__gt=23,
    ).order_by('-ib_requirements'))


    

    economics_unis = list(Uni_Database.objects.filter(
        discipline_survey__icontains=second_place, 
        tuition_fee_euro__lte=float(results.get('uni_cost', 0)),
        ib_requirements__lt=float(results.get('grades', 0)) + 5,
        ib_requirements__gt=23,
    ))

    # if third_place == "Social Sciences":
    #     third_place = "Social Science"

    law_unis = list(Uni_Database.objects.filter(
        discipline_survey__icontains=third_place, 
        tuition_fee_euro__lte=float(results.get('uni_cost', 0)),
        ib_requirements__lt=float(results.get('grades', 0)) + 5,
        ib_requirements__gt=23,
    ))

    # print(law_unis)
    print(results.get('uni_cost'))
    
    # Take 10 random universities from each discipline
    if business_unis:
        random.shuffle(business_unis)
        context['business_unis'] = business_unis  # Keep all business universities
    else:
        context['business_unis'] = []
        
    if economics_unis:
        random.shuffle(economics_unis)
        context['economics_unis'] = economics_unis
    else:
        context['economics_unis'] = []
        
    if law_unis:
        random.shuffle(law_unis)
        context['law_unis'] = law_unis  # Keep all law universities
    else:
        context['law_unis'] = []
    
    # context['unique_disciplines'] = sorted(list(primary_disciplines))
    context['selected_discipline'] = 'all'  # Default selection
    context['already_user'] = True
    context['no_results'] = False

    


    return render(request, 'suitability_survey.html', context)




@csrf_exempt  # Webhooks often come from external sources, so we disable CSRF for this view
def fillout_webhook(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Parse JSON payload


            name = next((q["value"] for q in data["submission"]["questions"] if q["id"] == "84YU"), None)
            name = "No name" if name is None else name

            email = next((q["value"] for q in data["submission"]["urlParameters"] if q["id"] == "email"), None)
            email = "No email" if email is None else email 

            medicine = next((q["value"] for q in data["submission"]["calculations"] if q["id"] == "1fWF"), 0)
            sciences = next((q["value"] for q in data["submission"]["calculations"] if q["id"] == "7TLZ"), 0)
            economics = next((q["value"] for q in data["submission"]["calculations"] if q["id"] == "8sNQ"), 0)
            creative = next((q["value"] for q in data["submission"]["calculations"] if q["id"] == "9HeS"), 0)
            human = next((q["value"] for q in data["submission"]["calculations"] if q["id"] == "m6oW"), 0)
            social = next((q["value"] for q in data["submission"]["calculations"] if q["id"] == "nahz"), 0)
            law = next((q["value"] for q in data["submission"]["calculations"] if q["id"] == "qEit"), 0)
            architect = next((q["value"] for q in data["submission"]["calculations"] if q["id"] == "vC2a"), 0)
            engineer = next((q["value"] for q in data["submission"]["calculations"] if q["id"] == "wdGc"), 0)

            uni_cost = next((q["value"] for q in data["submission"]["questions"] if q["id"] == "h8F1"), 0)
            uni_language = next((q["value"] for q in data["submission"]["questions"] if q["id"] == "nNHj"), 0)
            uni_setting = next((q["value"] for q in data["submission"]["questions"] if q["id"] == "t7Up"), 0)
            funding = next((q["value"] for q in data["submission"]["questions"] if q["id"] == "vQQN"), 0)
            grades = next((q["value"] for q in data["submission"]["questions"] if q["id"] == "fBzv"), 0)

    
            cost_dict = {
            "Money is no problem. I can afford every school as long as I get in ": 100000,
            "25000+ Euro – I can afford UK, but maybe not all schools in the USA": 25000,
            "10000-20000 Euro – I can afford most of universities except most expensive countries": 20000,
            "Maximum 5000 Euro a year – I am looking for an affordable option": 5000,
            "I am looking only for universities without any tuition fees": 0,
            }

            mapped_uni_cost = cost_dict.get(uni_cost, 0)


            grades_dict = {
            "High grades (90%+ or A-level equivalent)": 38,
            "Good grades (80%+ or B-level equivalent)": 35,
            "Average grades (60-79% or C-level equivalent)": 30,
            "Below Average grades (59-49% or D-level equivalent)": 26,
            "I struggle…": 0,
            }

            mapped_grades = grades_dict.get(grades, 0)

            email_body = f"""
            We got a new answer to the survey!

            Name: {name}
            Email: {email}

            Scores:
            - Medicine: {medicine}
            - Sciences: {sciences}
            - Finance: {economics}
            - Creative: {creative}
            - Human: {human}
            - Social: {social}
            - Law: {law}
            - Architecture: {architect}
            - Engineering: {engineer}
            """


            email_message = EmailMessage(
                subject="New Survey Answer!",
                body=email_body,
                from_email="Edunade Academy <contact@edunade.com>",
                to=["mati.kostrz@gmail.com"]
            )
            email_message.send()

            survey = Fillout_Survey(first_name = name, email = email, medicine_score = medicine, law_score = law, engineering_score = engineer, 
                                    sciences_score = sciences, economics_score = economics, creative_score = creative, humanities_score = human, 
                                    soc_sciences_score = social, architecture_score = architect, uni_cost = mapped_uni_cost, uni_setting = uni_setting, uni_language = uni_language,
                                    funding = funding, grades = mapped_grades)
            survey.save()



            return JsonResponse({"message": "Webhook received successfully"}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)


"""@csrf_exempt
def chatgpt_query(request):
    
    #API endpoint to handle ChatGPT queries from questionbank pages
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        question_context = data.get('question_context', '')
        user_question = data.get('user_question', '')
        
        if not question_context or not user_question:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # For now, return a placeholder response
        # In a real implementation, you would integrate with OpenAI's API
        response_text = f"I understand you're asking: "{user_question}"

This is a placeholder response. To implement actual ChatGPT integration, you would need to:

1. Install the OpenAI Python library: pip install openai
2. Get an OpenAI API key from https://platform.openai.com/
3. Replace this placeholder with actual OpenAI API calls

The question context I received:
{question_context[:200]}...

For now, here are some general tips for biology questions:
- Break down complex processes into steps
- Focus on key vocabulary and definitions
- Connect concepts to real-world examples
- Practice drawing diagrams to visualize processes

        return JsonResponse({'response': response_text})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)"""

@csrf_exempt  
def chatgpt_query(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_question = data.get('user_question')
            question_context = data.get('question_context', '')

            if not user_question:
                return JsonResponse({'error': 'No question provided.'}, status=400)

            # Build a prompt with context if provided, otherwise use default
            if question_context:
                prompt = f"""{question_context}

As an IB tutor, please answer the student's follow-up question clearly and concisely: "{user_question}" """
            else:
                prompt = f"""The question from the IB questionbank is:
"Which property of water explains its use as a coolant in sweat, helping regulate body temperature?"
The answer options are:
a) Hydrophobicity, b) High heat capacity, c) Low heat of vaporization
The correct answer is: b

Now the user has a follow-up question: "{user_question}" 
Please answer the user's question clearly and concisely as an IB tutor would."""

            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are an IB tutor helping students understand exam questions."},
                    {"role": "user", "content": prompt}
                ]
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            result = response.json()

            content = result['choices'][0]['message']['content']

            return JsonResponse({'response': content})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)

# ======= TUTOR ADMIN PANEL VIEWS =======

@track_user_journey
def tutor_management_admin(request):
    """Tutor management admin panel view"""
    if not request.session.get('already_registered', False):
        return redirect('login')
    
    # Check if user is Admin or AdminExternal
    user_occupation = request.session.get('occupation', '')
    
    # Allow access only for Admin or AdminExternal users
    if user_occupation not in ['Admin', 'AdminExternal']:
        return redirect('home')

    # Determine which domain's users to show based on current theme
    current_theme = getattr(request, 'theme', None)
    if not current_theme:
        host = request.get_host().lower()
        if 'topibtutors' in host:
            current_theme = 'topibtutors'
        elif 'apex' in host:
            current_theme = 'apex'
        else:
            # Fallback to session's source_domain or default to apex
            current_theme = request.session.get('source_domain', 'apex')
    
    # Get only Teachers from the current domain
    teachers = ApexUsers.objects.filter(
        occupation='Teacher',
        source_domain=current_theme
    ).order_by('-registration_date')

    # Get premium members with their end dates
    premium_members = {
        pm.customer_id: pm.subscription_end_date 
        for pm in Premium_Members.objects.filter(subscription_type='apex_teacher', subscribed='Yes')
    }

    # Add premium status and end date to each teacher
    teachers_with_premium = []
    for teacher in teachers:
        teacher.has_premium = teacher.customer_id in premium_members
        teacher.premium_end_date = premium_members.get(teacher.customer_id)
        teachers_with_premium.append(teacher)

    # Count teachers
    total_teacher_count = teachers.count()
    confirmed_teacher_count = teachers.filter(confirmed_teacher=True).count()
    pending_teacher_count = total_teacher_count - confirmed_teacher_count

    # Get domain display name
    domain_names = {
        'apex': 'Apex Tuition Australia',
        'topibtutors': 'Top IB Tutors',
    }
    
    context = {
        'teachers': teachers_with_premium,
        'total_teacher_count': total_teacher_count,
        'confirmed_teacher_count': confirmed_teacher_count,
        'pending_teacher_count': pending_teacher_count,
        'current_domain': current_theme,
        'current_domain_name': domain_names.get(current_theme, current_theme),
    }

    return render(request, 'tutor_management_admin.html', context)


@require_http_methods(["POST"])
def confirm_apex_teacher(request):
    """API to confirm/unconfirm a teacher and manage premium access"""
    if not request.session.get('already_registered', False):
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
    import json
    from datetime import timedelta
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        confirmed = data.get('confirmed', True)
        premium_days = data.get('premium_days', 0)
        
        apex_user = ApexUsers.objects.get(id=user_id)
        apex_user.confirmed_teacher = confirmed
        apex_user.save()
        
        # Handle premium access
        if premium_days > 0:
            # Calculate subscription end date
            subscription_end = timezone.now() + timedelta(days=premium_days)
            
            # Create or update Premium_Members entry using ApexUsers customer_id
            premium_member, created = Premium_Members.objects.get_or_create(
                customer_id=apex_user.customer_id,
                defaults={
                    'stripe_customer_id': 'FREE',
                    'first_name': apex_user.first_name,
                    'last_name': apex_user.last_name,
                    'email': apex_user.email,
                    'subscribed': 'Yes',
                    'subscription_type': 'apex_teacher',
                    'subscription_end_date': subscription_end,
                }
            )
            
            if not created:
                premium_member.subscribed = 'Yes'
                premium_member.subscription_type = 'apex_teacher'
                premium_member.subscription_end_date = subscription_end
                premium_member.save()
        
        return JsonResponse({'success': True})
    except ApexUsers.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def bulk_confirm_apex_teachers(request):
    """API to bulk confirm teachers and grant premium access"""
    if not request.session.get('already_registered', False):
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
    import json
    from datetime import timedelta
    
    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        confirmed = data.get('confirmed', True)
        premium_days = data.get('premium_days', 0)
        
        # Update confirmed status
        ApexUsers.objects.filter(id__in=user_ids).update(confirmed_teacher=confirmed)
        
        # Grant premium access if days specified
        if premium_days > 0:
            subscription_end = timezone.now() + timedelta(days=premium_days)
            
            for apex_user in ApexUsers.objects.filter(id__in=user_ids):
                premium_member, created = Premium_Members.objects.get_or_create(
                    customer_id=apex_user.customer_id,
                    defaults={
                        'stripe_customer_id': 'FREE',
                        'first_name': apex_user.first_name,
                        'last_name': apex_user.last_name,
                        'email': apex_user.email,
                        'subscribed': 'Yes',
                        'subscription_type': 'apex_teacher',
                        'subscription_end_date': subscription_end,
                    }
                )
                
                if not created:
                    premium_member.subscribed = 'Yes'
                    premium_member.subscription_type = 'apex_teacher'
                    premium_member.subscription_end_date = subscription_end
                    premium_member.save()
        
        return JsonResponse({'success': True, 'updated_count': len(user_ids)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def bulk_delete_apex_teachers(request):
    """API to bulk delete Apex teachers"""
    if not request.session.get('already_registered', False):
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
    import json
    from django.contrib.auth.models import User
    
    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        
        for apex_user in ApexUsers.objects.filter(id__in=user_ids):
            # Delete from Premium_Members
            Premium_Members.objects.filter(customer_id=apex_user.customer_id).delete()
            # Delete Django auth user
            User.objects.filter(email=apex_user.email).delete()
            # Delete ApexUsers entry
            apex_user.delete()
        
        return JsonResponse({'success': True, 'deleted_count': len(user_ids)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def delete_apex_teacher(request):
    """API to delete an Apex teacher"""
    if not request.session.get('already_registered', False):
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
    import json
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        
        apex_user = ApexUsers.objects.get(id=user_id)
        
        # Also delete from Premium_Members if they have an entry
        Premium_Members.objects.filter(customer_id=apex_user.customer_id).delete()
        
        # Delete the Django auth user
        from django.contrib.auth.models import User
        User.objects.filter(email=apex_user.email).delete()
        
        # Delete the ApexUsers entry
        apex_user.delete()
        
        return JsonResponse({'success': True})
    except ApexUsers.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@track_user_journey
def tutor_admin(request):
    """Tutor admin panel view"""
    # Check if user is logged in
    if not request.session.get('already_registered', False):
        return redirect('login')
    
    # Get user email from session
    user_email = request.session.get('email', '')
    
    try:
        # Get user data
        user_data = Users.objects.get(email=user_email)
        
        # Check if user is a tutor or admin
        if user_data.occupation not in ['Tutor', 'Admin']:
            messages.error(request, 'Access denied. Only tutors and admins can access this page.')
            return redirect('home')
            
    except Users.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('login')
    
    # Handle POST request (adding new session or updating existing)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Handle session update
        if action == 'update_session':
            session_id = request.POST.get('session_id')
            try:
                session = TutorSession.objects.get(id=session_id)
                
                # Check if user has permission to edit this session
                if user_data.occupation != 'Admin' and session.tutor != user_data:
                    messages.error(request, 'You can only edit your own sessions.')
                    return redirect('tutor-admin')
                
                # Update session fields
                session.session_time = request.POST.get('session_time')
                session.topic = request.POST.get('topic')
                session.subject = request.POST.get('subject')
                session.status = request.POST.get('status')
                session.notes = request.POST.get('notes', '')
                session.hours_taught = float(request.POST.get('hours_taught', 0)) if request.POST.get('hours_taught') else None
                session.homework_comments = request.POST.get('homework_comments', '')
                
                # Handle PDF update if new file is uploaded
                if request.FILES.get('session_pdf'):
                    session.session_pdf = request.FILES.get('session_pdf')

                # Handle transcript upload if provided
                new_transcript = request.FILES.get('session_transcript')
                if new_transcript:
                    session.session_transcript = new_transcript

                session.save()
                messages.success(request, 'Session updated successfully!')
                if new_transcript:
                    return redirect(f"{reverse('tutor-admin')}?review_session={session.id}")
                return redirect('tutor-admin')
                
            except TutorSession.DoesNotExist:
                messages.error(request, 'Session not found.')
                return redirect('tutor-admin')
            except Exception as e:
                messages.error(request, f'Error updating session: {str(e)}')
                return redirect('tutor-admin')
        
        # Handle new session creation
        student_id = request.POST.get('student_id')
        tutor_id = request.POST.get('tutor_id')  # For admin users
        session_time = request.POST.get('session_time')
        topic = request.POST.get('topic')
        subject = request.POST.get('subject')
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        hours_taught = request.POST.get('hours_taught', '')
        homework_comments = request.POST.get('homework_comments', '')
        session_pdf = request.FILES.get('session_pdf')
        session_transcript = request.FILES.get('session_transcript')
        
        try:
            # Determine which tutor to use
            if user_data.occupation == 'Admin' and tutor_id:
                # Admin selected a specific tutor (can be tutor or admin)
                selected_tutor = Users.objects.get(id=tutor_id, occupation__in=['Tutor', 'Admin'])
            else:
                # Use current user as tutor (for regular tutors or admin without selection)
                selected_tutor = user_data
            
            # Handle both managed students and regular students
            managed_student = None
            student_first_name_override = None
            student_last_name_override = None
            
            if student_id.startswith('managed_'):
                # This is a managed student
                managed_student_id = student_id.replace('managed_', '')
                managed_student = StudentManagement.objects.get(id=managed_student_id)
                
                # Use linked user if available, otherwise we'll use the tutor as FK but override names
                if managed_student.linked_user:
                    student = managed_student.linked_user
                else:
                    # No linked user - use tutor as FK placeholder but override the names
                    student = user_data  # Use the tutor as FK (required for database)
                    student_first_name_override = managed_student.student_first_name
                    student_last_name_override = managed_student.student_last_name
                
            else:
                # This is a regular platform student
                student = Users.objects.get(id=student_id)
            
            # Get student email for the session record
            if managed_student and not managed_student.linked_user:
                # For managed students without linked accounts, use the email from StudentManagement
                session_student_email = managed_student.student_email
            else:
                # For students with linked accounts, use the linked user's email
                session_student_email = student.email

            # Create new tutor session
            session = TutorSession.objects.create(
                tutor=selected_tutor,
                student=student,
                tutor_first_name=selected_tutor.first_name,
                tutor_last_name=selected_tutor.last_name,
                student_first_name=student_first_name_override or student.first_name,
                student_last_name=student_last_name_override or student.last_name,
                student_email=session_student_email,
                session_time=session_time,
                topic=topic,
                subject=subject,
                status=status,
                notes=notes,
                hours_taught=float(hours_taught) if hours_taught else None,
                homework_comments=homework_comments,
                session_pdf=session_pdf,
                session_transcript=session_transcript if session_transcript else None,
            )
            
            # Use the correct student name for the message
            display_name = f"{student_first_name_override or student.first_name} {student_last_name_override or student.last_name}"
            tutor_name = f"{selected_tutor.first_name} {selected_tutor.last_name}"
            messages.success(request, f'Session added successfully for {display_name} with tutor {tutor_name}!')
            if session_transcript:
                return redirect(f"{reverse('tutor-admin')}?review_session={session.id}")
            return redirect('tutor-admin')
            
        except Users.DoesNotExist:
            messages.error(request, 'Selected student not found.')
        except Exception as e:
            messages.error(request, f'Error creating session: {str(e)}')
    
    # Get managed students based on user role
    if user_data.occupation == 'Admin':
        # Admins can see all managed students
        managed_students = StudentManagement.objects.filter(
            status='Active'
        ).order_by('student_first_name', 'student_last_name')
    else:
        # Tutors only see students assigned to them
        managed_students = StudentManagement.objects.filter(
            assigned_tutor=user_data, 
            status='Active'
        ).order_by('student_first_name', 'student_last_name')
    
    # Get sessions - admins see all sessions, tutors see only their own
    if user_data.occupation == 'Admin':
        sessions = TutorSession.objects.all().order_by('-session_time')
    else:
        sessions = TutorSession.objects.filter(tutor=user_data).order_by('-session_time')
    
    # Get tutors list for admin users (both tutors and admins can be tutors)
    tutors = []
    if user_data.occupation == 'Admin':
        tutors = Users.objects.filter(occupation__in=['Tutor', 'Admin']).order_by('first_name', 'last_name')
    
    context = {
        'managed_students': managed_students,
        'sessions': sessions,
        'tutors': tutors,
        'tutor_name': f'{user_data.first_name} {user_data.last_name}',
        'user_role': user_data.occupation,
        'is_admin': user_data.occupation == 'Admin',
        'user_id': user_data.id,
        'review_session_id': request.GET.get('review_session', ''),
    }

    return render(request, 'tutor_admin.html', context)


def student_admin(request, _template='student_admin.html'):
    """Student admin panel view - shows their tutoring sessions"""
    # Check if user is logged in
    if not request.session.get('already_registered', False):
        return redirect('login')
    
    # Get user email from session
    user_email = request.session.get('email', '')
    
    try:
        # Get user data
        user_data = Users.objects.get(email=user_email)
        
        # Check if user is a student
        if not user_data.occupation.lower().startswith('student'):
            messages.error(request, 'Access denied. Only students can access this page.')
            return redirect('home')
            
    except Users.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('login')
    
    sessions = TutorSession.objects.filter(student_email=user_email).order_by('-session_time')

    
    # Calculate statistics
    from datetime import datetime
    from django.db.models import Sum
    
    # Total sessions (all time, all statuses)
    total_sessions_count = sessions.count()
    
    # Completed sessions (all time)
    completed_sessions = sessions.filter(status='Completed')
    
    # Upcoming/scheduled sessions
    upcoming_sessions = sessions.filter(status='Upcoming')
    
    # Total hours (sum of all hours_taught)
    total_hours_data = sessions.aggregate(total=Sum('hours_taught'))
    total_hours = total_hours_data['total'] or 0
    
    # Get available months from sessions
    from django.db.models import Q
    from collections import OrderedDict
    from django.db.models.functions import TruncMonth
    
    # Get unique months from sessions
    available_months = []
    if sessions.exists():
        # Get all unique year-month combinations from sessions using PostgreSQL-compatible syntax
        month_data = sessions.annotate(
            year_month=TruncMonth('session_time')
        ).values_list('year_month', flat=True).distinct().order_by('-year_month')
        
        # Convert to readable format
        month_names = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        
        for date_obj in month_data:
            year = date_obj.year
            month = date_obj.month
            year_month = f"{year}-{month:02d}"
            month_name = month_names.get(month, str(month))
            available_months.append({
                'value': year_month,
                'label': f'{month_name} {year}'
            })
    
    # Check if rules have been accepted by STUDENT
    rules_accepted = False
    try:
        # Use filter().first() to handle multiple records with same email
        student_mgmt = StudentManagement.objects.filter(student_email=user_email).first()
        if student_mgmt:
            rules_accepted = student_mgmt.student_rules_accepted
    except Exception as e:
        pass
    
    context = {
        'sessions': sessions,
        'student_name': f'{user_data.first_name} {user_data.last_name}',
        'has_sessions': sessions.exists(),
        'available_months': available_months,
        # Statistics for dashboard
        'total_sessions': total_sessions_count,
        'completed_sessions': completed_sessions.count(),
        'total_hours': total_hours,
        'upcoming_sessions': upcoming_sessions.count(),
        'rules_accepted': rules_accepted,
    }
    
    return render(request, _template, context)


def student_admin_v2(request):
    """Student admin v2 — redesigned table with Learn More popup."""
    return student_admin(request, _template='student_admin_v2.html')


@track_user_journey
def logistics_dashboard(request):
    return render(request, 'logistics_dashboard.html')


# ---------------------------------------------------------------------------
# Question Bank Export (PDF-ready print page)
# ---------------------------------------------------------------------------

_QB_SUBJECT_MAP = {
    'math_ai_sl': ('Math AI SL',  'Math_AI_SL_Questionbank'),
    'math_ai_hl': ('Math AI HL',  'Math_AI_HL_Questionbank'),
    'math_aa_sl': ('Math AA SL',  'Math_AA_SL_Questionbank'),
    'math_aa_hl': ('Math AA HL',  'Math_AA_HL_Questionbank'),
    'bio_sl':     ('Biology SL',  'Biology_SL_Questionbank'),
    'bio_hl':     ('Biology HL',  'Biology_HL_Questionbank'),
    'phy_sl':     ('Physics SL',  'Physics_SL_Questionbank'),
    'phy_hl':     ('Physics HL',  'Physics_HL_Questionbank'),
    'chem_sl':    ('Chemistry SL','Chemistry_SL_Questionbank'),
    'chem_hl':    ('Chemistry HL','Chemistry_HL_Questionbank'),
    'hist_sl':    ('History SL',  'History_SL_Questionbank'),
    'cs_sl':      ('Computer Science SL', 'Comp_Sci_SL_Questionbank'),
}

def _get_qb_model(subject_key):
    from website import models as _m
    entry = _QB_SUBJECT_MAP.get(subject_key)
    if not entry:
        return None, None
    label, model_name = entry
    return label, getattr(_m, model_name, None)


def export_questions(request):
    """Selection page for question bank export."""
    if not request.session.get('already_registered', False):
        return redirect('login')

    subjects = [(k, v[0]) for k, v in _QB_SUBJECT_MAP.items()]

    # Build chapter map {subject_key: [(value, display), ...]}
    chapter_map = {}
    for key in _QB_SUBJECT_MAP:
        _, model = _get_qb_model(key)
        if model:
            chapter_map[key] = [
                (v, d) for v, d in model.CHAPTERS if v not in ('', 'null')
            ]

    return render(request, 'export_questions/select.html', {
        'already_registered': True,
        'subjects': subjects,
        'chapter_map': chapter_map,
    })


def export_questions_print(request):
    """Print-ready page with all questions for a subject+chapter."""
    if not request.session.get('already_registered', False):
        return redirect('login')

    subject_key = request.GET.get('subject', '')
    chapter_val = request.GET.get('chapter', '')

    subject_label, model = _get_qb_model(subject_key)
    if not model or not chapter_val:
        return redirect('export-questions')

    # Chapter display name
    chapter_label = next(
        (d for v, d in model.CHAPTERS if v == chapter_val), chapter_val
    )

    # Fetch questions (chapter, chapter2, or chapter3 match)
    from django.db.models import Q as _Q
    qs = model.objects.filter(
        _Q(chapter=chapter_val) | _Q(chapter2=chapter_val) | _Q(chapter3=chapter_val)
    ).order_by('id')

    # Attach revision tags — currently only available for Math AI SL
    from website.models import Math_AI_SL_Questionbank as _MAISLQB
    has_tags = (model == _MAISLQB)

    questions_with_tags = []
    for q in qs:
        tags = (
            QuestionSkillTag.objects
            .filter(question_id=q.id)
            .select_related('skill__topic__chapter')
            if has_tags else []
        )
        questions_with_tags.append({
            'obj': q,
            'tags': tags,
        })

    return render(request, 'export_questions/print.html', {
        'already_registered': True,
        'subject_label': subject_label,
        'chapter_label': chapter_label,
        'questions': questions_with_tags,
        'total': len(questions_with_tags),
    })


# ---------------------------------------------------------------------------
# Transcript Analysis Feature
# ---------------------------------------------------------------------------

import json as _json_mod

def _build_analysis_prompt(session, student, transcript_text, skills_with_mastery):
    skill_lines = '\n'.join(
        f'  - {s["slug"]}: "{s["name"]}" (current mastery: {s["mastery"]:.2f})'
        for s in skills_with_mastery
    )
    mastery_json = {s['slug']: s['mastery'] for s in skills_with_mastery}

    return f"""You are an expert IB Mathematics tutor analysing a one-to-one tutoring session transcript.

SESSION INFO:
- Student: {student.first_name} {student.last_name}
- Date: {session.session_time.strftime('%Y-%m-%d')}
- Subject: {session.get_subject_display()}
- Topic: {session.topic}

AVAILABLE SKILL KEYS (you MUST only use these exact slugs):
{skill_lines}

CURRENT MASTERY SCORES (0.0–1.0):
{_json_mod.dumps(mastery_json, indent=2)}

TRANSCRIPT:
{transcript_text[:12000]}

Return ONLY a valid JSON object. No markdown, no explanation, no preamble. Exactly this structure:
{{
  "lesson_summary": "2-4 sentence summary of what was covered",
  "student_overall_understanding": "1-2 sentence assessment of student understanding",
  "covered_skills": [
    {{
      "skill_key": "<one of the slugs above>",
      "current_mastery": <float from current mastery scores>,
      "suggested_mastery_change": <float between -0.10 and +0.10>,
      "suggested_new_mastery": <current + change, clamped 0.05–0.95>,
      "confidence": <float 0.0–1.0 how confident you are>,
      "evidence_level": "<none|weak|moderate|strong>",
      "evidence_from_transcript": ["1-2 sentence plain-English summary of what was discussed or done in the session related to this skill — do NOT copy raw transcript text, write it as a clean readable observation"],
      "misconceptions": ["any misconception observed, or empty list"],
      "recommended_next_actions": ["specific action for tutor/student"],
      "applied": false
    }}
  ],
  "recommended_revision_set": [
    {{
      "skill_key": "<slug>",
      "reason": "why this needs revision"
    }}
  ],
  "tutor_notes": ["any notes for the tutor"]
}}

IMPORTANT — coverage rules:
- Be INCLUSIVE. Include every skill that was touched on, discussed, explained, practised, or even briefly mentioned during the session — not just skills with strong direct evidence.
- If the tutor explained a concept, a student asked about it, or a homework question involved it, that skill is covered.
- A skill can have evidence_level "weak" or "none" and still appear in covered_skills — it signals the topic came up and the student's mastery should be acknowledged.
- Only OMIT a skill if there is genuinely zero connection to the transcript.
- suggested_mastery_change must be between -0.10 and +0.10. Use small positive values (0.01–0.04) for skills that were only briefly touched, larger values (0.05–0.10) for skills that were actively practised with correct understanding.
- Transcript evidence carries less weight than graded question attempts, so keep changes modest.
- applied must always be false in your response.
- Only use skill keys from the list above.
"""


def transcript_analysis(request, session_id):
    """Main view for /revision-engine/class-transcript-analysis/<session_id>/"""
    if not request.session.get('already_registered', False):
        return redirect('login')

    user_email = request.session.get('email', '')
    try:
        current_user = Users.objects.get(email=user_email)
    except Users.DoesNotExist:
        return redirect('login')

    try:
        session = TutorSession.objects.select_related('student', 'tutor').get(id=session_id)
    except TutorSession.DoesNotExist:
        return render(request, 'revision_engine/transcript_analysis.html', {
            'error': 'Session not found.',
            'already_registered': True,
        })

    # Only the student of the session or staff can view
    student = session.student
    is_staff = current_user.occupation in ('Admin', 'AdminExternal', 'Tutor')
    if not is_staff and current_user.email != student.email:
        return render(request, 'revision_engine/transcript_analysis.html', {
            'error': 'You do not have permission to view this analysis.',
            'already_registered': True,
        })

    # Check transcript exists
    has_transcript = bool(session.session_transcript)

    # Load all skills with current mastery
    all_skills = RevisionSkill.objects.select_related('topic__chapter').order_by('topic__chapter__order', 'topic__order', 'order')
    mastery_map = {
        m.skill_id: m.mastery_score
        for m in StudentSkillMastery.objects.filter(user=student)
    }
    skills_with_mastery = [
        {
            'slug': s.slug,
            'name': s.display_name,
            'mastery': mastery_map.get(s.id, 0.3),
            'topic': s.topic.display_name,
            'chapter': s.topic.chapter.display_name,
        }
        for s in all_skills
    ]

    # Load existing analysis if any
    existing = ClassTranscriptAnalysis.objects.filter(class_session=session).first()

    # One-time migrate: tutor-approved analyses were stored as 'analysed' until the student clicked Apply.
    # Mastery suggestions are applied automatically now; finalize status for any legacy rows.
    if existing and existing.status == 'analysed':
        _apply_mastery_updates(existing, student, select_all=True)
        ClassTranscriptAnalysis.objects.filter(pk=existing.pk).update(status='applied')
        existing.refresh_from_db()

    # ── POST: analyse ──────────────────────────────────────────────────────
    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'analyze':
            # Students cannot trigger or overwrite an analysis — only staff can
            if not is_staff:
                return redirect('transcript-analysis', session_id=session_id)
            if not has_transcript:
                return render(request, 'revision_engine/transcript_analysis.html', {
                    'error': 'This session has no transcript uploaded.',
                    'session': session, 'already_registered': True,
                })

            # Read transcript text
            try:
                with open(session.session_transcript.path, 'r', encoding='utf-8') as f:
                    transcript_text = f.read()
            except Exception as e:
                return render(request, 'revision_engine/transcript_analysis.html', {
                    'error': f'Could not read transcript: {e}',
                    'session': session, 'already_registered': True,
                })

            prompt = _build_analysis_prompt(session, student, transcript_text, skills_with_mastery)

            headers = {
                'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                'Content-Type': 'application/json',
            }
            payload = {
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': 'You are an expert IB tutor. Return only valid JSON, no markdown or explanation.'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.3,
                'response_format': {'type': 'json_object'},
            }

            try:
                resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                raw = resp.json()['choices'][0]['message']['content']
                ai_data = _json_mod.loads(raw)
            except requests.exceptions.RequestException as e:
                return render(request, 'revision_engine/transcript_analysis.html', {
                    'error': f'OpenAI request failed: {e}',
                    'session': session, 'already_registered': True,
                    'existing': existing, 'skills_with_mastery': skills_with_mastery,
                    'has_transcript': has_transcript,
                })
            except (_json_mod.JSONDecodeError, KeyError) as e:
                return render(request, 'revision_engine/transcript_analysis.html', {
                    'error': f'Invalid response from AI: {e}',
                    'session': session, 'already_registered': True,
                    'existing': existing, 'skills_with_mastery': skills_with_mastery,
                    'has_transcript': has_transcript,
                })

            # Validate skill keys
            valid_slugs = {s['slug'] for s in skills_with_mastery}
            for skill_item in ai_data.get('covered_skills', []):
                if skill_item.get('skill_key') not in valid_slugs:
                    skill_item['skill_key'] = None  # flag unknown

            _sync_recommended_revision_to_covered(ai_data)

            # Save / overwrite analysis
            if existing:
                existing.ai_json = ai_data
                existing.status = 'analysed'
                existing.analysed_by = current_user
                existing.save()
                analysis = existing
            else:
                analysis = ClassTranscriptAnalysis.objects.create(
                    class_session=session,
                    student=student,
                    analysed_by=current_user,
                    ai_json=ai_data,
                    status='analysed',
                )

            _apply_mastery_updates(analysis, student, select_all=True)
            ClassTranscriptAnalysis.objects.filter(pk=analysis.pk).update(status='applied')
            return redirect('transcript-analysis', session_id=session_id)

    # ── GET ────────────────────────────────────────────────────────────────
    # Enrich covered_skills with skill metadata
    skill_meta = {s['slug']: s for s in skills_with_mastery}
    enriched_skills = []

    def _human_evidence_level(raw_ev):
        r = str(raw_ev or '').strip().lower()
        mapping = {'none': 'None', 'weak': 'Weak', 'moderate': 'Moderate', 'strong': 'Strong'}
        return mapping.get(r, raw_ev.capitalize() if raw_ev else '')

    def _format_delta_percentage(change_val):
        try:
            p = round(float(change_val or 0) * 100, 4)
        except (TypeError, ValueError):
            p = 0.0
        if abs(p) < 0.005:
            return '0%'
        if abs(p - round(p)) < 1e-4:
            return f'{int(round(p))}%'
        return f'{round(p, 1)}%'

    if existing and existing.ai_json:
        for s in existing.ai_json.get('covered_skills', []):
            meta = skill_meta.get(s.get('skill_key', ''), {})
            cur  = float(s.get('current_mastery', 0))
            new  = float(s.get('suggested_new_mastery', cur))
            enriched_skills.append({
                **s,
                'display_name':    meta.get('name', s.get('skill_key', '')),
                'topic':           meta.get('topic', ''),
                'chapter':         meta.get('chapter', ''),
                'mastery_pct':     round(cur * 100),
                'new_mastery_pct': round(new * 100),
                'tutor_evidence_label': _human_evidence_level(s.get('evidence_level')),
                'tutor_delta_display':   _format_delta_percentage(s.get('suggested_mastery_change')),
            })

    # Enrich recommended revision (only skills still in covered_skills)
    covered_slugs = {x['skill_key'] for x in enriched_skills if x.get('skill_key')}
    raw_revision = (existing.ai_json or {}).get('recommended_revision_set', []) if existing else []
    recommended_revision = [
        {
            **r,
            'display_name': skill_meta.get(r.get('skill_key', ''), {}).get('name', r.get('skill_key', '')),
        }
        for r in raw_revision
        if r.get('skill_key') in covered_slugs
    ]

    return render(request, 'revision_engine/transcript_analysis.html', {
        'already_registered': True,
        'session': session,
        'student': student,
        'has_transcript': has_transcript,
        'existing': existing,
        'enriched_skills': enriched_skills,
        'skills_with_mastery': skills_with_mastery,
        'recommended_revision': recommended_revision,
        'lesson_summary': (existing.ai_json or {}).get('lesson_summary', '') if existing else '',
        'is_staff': is_staff,
    })


def _run_session_ai_analysis(session, student):
    """
    Run OpenAI transcript analysis for a TutorSession.
    Returns (ai_json dict, None) on success or (None, error_string) on failure.
    """
    if not session.session_transcript:
        return None, 'No transcript uploaded for this session.'

    try:
        with open(session.session_transcript.path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
    except Exception as e:
        return None, f'Could not read transcript: {e}'

    all_skills = RevisionSkill.objects.select_related('topic__chapter').order_by(
        'topic__chapter__order', 'topic__order', 'order'
    )
    mastery_map = {
        m.skill_id: m.mastery_score
        for m in StudentSkillMastery.objects.filter(user=student)
    }
    skills_with_mastery = [
        {
            'slug': s.slug,
            'name': s.display_name,
            'mastery': mastery_map.get(s.id, 0.3),
            'topic': s.topic.display_name,
            'chapter': s.topic.chapter.display_name,
        }
        for s in all_skills
    ]

    prompt = _build_analysis_prompt(session, student, transcript_text, skills_with_mastery)

    headers = {
        'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': 'gpt-4o-mini',
        'messages': [
            {'role': 'system', 'content': 'You are an expert IB tutor. Return only valid JSON, no markdown or explanation.'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.3,
        'response_format': {'type': 'json_object'},
    }

    try:
        resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        raw = resp.json()['choices'][0]['message']['content']
        ai_data = _json_mod.loads(raw)
    except requests.exceptions.RequestException as e:
        return None, f'OpenAI request failed: {e}'
    except (_json_mod.JSONDecodeError, KeyError) as e:
        return None, f'Invalid AI response: {e}'

    # Strip any unknown skill keys
    valid_slugs = {s['slug'] for s in skills_with_mastery}
    for item in ai_data.get('covered_skills', []):
        if item.get('skill_key') not in valid_slugs:
            item['skill_key'] = None

    return ai_data, None


def tutor_run_analysis(request):
    """AJAX POST: run AI analysis on a session transcript. Returns raw ai_json for tutor review."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data = _json_mod.loads(request.body)
    session_id = int(data['session_id'])

    try:
        session = TutorSession.objects.select_related('student', 'tutor').get(id=session_id)
    except TutorSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    ai_json, error = _run_session_ai_analysis(session, session.student)
    if error:
        return JsonResponse({'error': error}, status=400)

    # Return all skills for the edit UI
    all_skills = list(
        RevisionSkill.objects.select_related('topic__chapter').order_by(
            'topic__chapter__order', 'topic__order', 'order'
        ).values('slug', 'display_name', 'topic__display_name', 'topic__chapter__display_name')
    )
    # Attach display_name to each covered skill for easy rendering
    skill_name_map = {s['slug']: s['display_name'] for s in all_skills}
    for item in ai_json.get('covered_skills', []):
        item['display_name'] = skill_name_map.get(item.get('skill_key', ''), item.get('skill_key', ''))

    session_time = session.session_time
    return JsonResponse({
        'success':    True,
        'ai_json':    ai_json,
        'all_skills': all_skills,
        'session_info': {
            'id':           session.id,
            'student_name': f'{session.student.first_name} {session.student.last_name}',
            'date':         session_time.strftime('%d %b %Y') if session_time else '',
            'subject':      session.get_subject_display(),
        },
    })


def tutor_save_analysis(request):
    """AJAX POST: save tutor-reviewed ai_json and apply mastery updates (status=applied)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    user_email = request.session.get('email', '')
    try:
        current_user = Users.objects.get(email=user_email)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    data = _json_mod.loads(request.body)
    session_id = int(data['session_id'])
    ai_json    = data['ai_json']

    try:
        session = TutorSession.objects.select_related('student').get(id=session_id)
    except TutorSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    _sync_recommended_revision_to_covered(ai_json)

    existing = ClassTranscriptAnalysis.objects.filter(class_session=session).first()
    if existing:
        existing.ai_json     = ai_json
        existing.analysed_by = current_user
        existing.save()
        analysis_obj = existing
    else:
        analysis_obj = ClassTranscriptAnalysis.objects.create(
            class_session=session,
            student=session.student,
            analysed_by=current_user,
            ai_json=ai_json,
        )

    _apply_mastery_updates(analysis_obj, session.student, select_all=True)
    ClassTranscriptAnalysis.objects.filter(pk=analysis_obj.pk).update(status='applied')

    return JsonResponse({'success': True})


def _sync_recommended_revision_to_covered(ai_json):
    """
    Keep only recommended_revision_set rows whose skill_key still appears in covered_skills.
    The tutor UI edits covered_skills; without this, removed skills linger in recommendations
    and still appear on Transcript Analysis + Learning Path.
    """
    if not ai_json or not isinstance(ai_json, dict):
        return
    covered_slugs = {
        s.get('skill_key')
        for s in (ai_json.get('covered_skills') or [])
        if s.get('skill_key')
    }
    raw = ai_json.get('recommended_revision_set')
    if not raw:
        ai_json['recommended_revision_set'] = []
        return
    ai_json['recommended_revision_set'] = [
        r for r in raw
        if isinstance(r, dict) and r.get('skill_key') in covered_slugs
    ]


def _apply_mastery_updates(analysis, student, select_all=True, selected_slugs=None):
    """Apply suggested mastery score changes to StudentSkillMastery records."""
    if not analysis.ai_json:
        return
    covered = analysis.ai_json.get('covered_skills', [])
    for skill_item in covered:
        slug = skill_item.get('skill_key')
        if not slug:
            continue
        if not select_all and slug not in (selected_slugs or []):
            continue
        if skill_item.get('applied'):
            continue
        try:
            skill = RevisionSkill.objects.get(slug=slug)
            mastery, _ = StudentSkillMastery.objects.get_or_create(user=student, skill=skill)
            new_score = float(skill_item.get('suggested_new_mastery', mastery.mastery_score))
            mastery.mastery_score = max(0.05, min(0.95, new_score))
            mastery.save()
            skill_item['applied'] = True
        except RevisionSkill.DoesNotExist:
            continue
    analysis.ai_json['covered_skills'] = covered
    analysis.save(update_fields=['ai_json', 'updated_at'])


def _build_path_from_analysis(analysis):
    """
    Build a ranked list of skill cards from a ClassTranscriptAnalysis.
    Only skills explicitly mentioned in this transcript are included.
    Returns a list of dicts sorted by priority score (highest first).
    """
    if not analysis or not analysis.ai_json:
        return []

    ai = analysis.ai_json
    covered = {s['skill_key']: s for s in ai.get('covered_skills', []) if s.get('skill_key')}
    rec_set = {}
    for r in (ai.get('recommended_revision_set') or []):
        sk = r.get('skill_key') if isinstance(r, dict) else None
        if sk and sk in covered:
            rec_set[sk] = r

    # Learning path follows covered skills only; recommended flags/skips must not resurrect removed topics
    all_slugs = set(covered.keys())

    if not all_slugs:
        return []

    student = analysis.student
    mastery_map = {
        m.skill_id: m
        for m in StudentSkillMastery.objects.filter(user=student)
    }
    skill_map = {
        s.slug: s
        for s in RevisionSkill.objects.select_related('topic__chapter').filter(slug__in=all_slugs)
    }

    # Bulk MCQ counts for these skills (single query)
    sq_counts = dict(
        RevisionSubQuestion.objects
        .filter(skills__slug__in=all_slugs)
        .values('skills__slug')
        .annotate(cnt=Count('id'))
        .values_list('skills__slug', 'cnt')
    )

    # Bulk homework questions: prefer those with video, fallback to any
    hw_map = {}
    tags = QuestionSkillTag.objects.filter(skill__slug__in=all_slugs).select_related('question', 'skill')
    for t in tags:
        slug = t.skill.slug
        q = t.question
        if slug not in hw_map:
            hw_map[slug] = q
        elif not hw_map[slug].video and q.video:
            hw_map[slug] = q

    path = []
    for slug in all_slugs:
        skill = skill_map.get(slug)
        if not skill:
            continue
        mastery = mastery_map.get(skill.id)
        score   = mastery.mastery_score if mastery else 0.3

        # Priority score
        priority = 1.0 - score
        if slug in rec_set:
            priority += 0.15
        ev_level = covered.get(slug, {}).get('evidence_level', '')
        if ev_level == 'strong':
            priority += 0.10
        elif ev_level == 'moderate':
            priority += 0.05

        # Reason text: prefer recommended_revision reason, fallback to evidence summary
        reason = rec_set.get(slug, {}).get('reason', '')
        if not reason:
            ev = covered.get(slug, {}).get('evidence_from_transcript', [])
            reason = ev[0] if ev else ''

        mcq_count = sq_counts.get(slug, 0)
        hw_q = hw_map.get(slug)

        path.append({
            'skill':            skill,
            'mastery':          mastery,
            'score':            score,
            'percent':          round(score * 100),
            'color':            re_service.get_mastery_color(score),
            'label':            mastery.mastery_label if mastery else 'Not started',
            'mcq_count':        mcq_count,
            'reason':           reason,
            'misconceptions':   covered.get(slug, {}).get('misconceptions', []),
            'homework_question':hw_q,
            'hw_has_video':     bool(hw_q and hw_q.video),
            'priority':         priority,
            'in_recommended':   slug in rec_set,
        })

    path.sort(key=lambda x: x['priority'], reverse=True)
    return path


def learning_path(request, analysis_id):
    """Per-transcript learning path for a student."""
    if not request.session.get('already_registered', False):
        return redirect('login')

    user_email = request.session.get('email', '')
    try:
        current_user = Users.objects.get(email=user_email)
    except Users.DoesNotExist:
        return redirect('login')

    try:
        analysis = ClassTranscriptAnalysis.objects.select_related(
            'class_session__tutor', 'student'
        ).get(id=analysis_id)
    except ClassTranscriptAnalysis.DoesNotExist:
        return render(request, 'learning_path/learning_path.html', {
            'error': 'Learning path not found.',
            'already_registered': True,
        })

    # Access: student of this analysis or staff
    is_staff = current_user.occupation in ('Admin', 'AdminExternal', 'Tutor')
    if not is_staff and current_user.email != analysis.student.email:
        return render(request, 'learning_path/learning_path.html', {
            'error': 'You do not have permission to view this learning path.',
            'already_registered': True,
        })

    if analysis.status not in ('analysed', 'applied'):
        return render(request, 'learning_path/learning_path.html', {
            'error': 'This transcript has not been analysed yet.',
            'already_registered': True,
            'analysis': analysis,
            'session': analysis.class_session,
        })

    skill_path = _build_path_from_analysis(analysis)

    # Skills the student has already completed for this analysis (from DB)
    done_slugs = set(
        LearningPathProgress.objects
        .filter(student=analysis.student, analysis=analysis)
        .values_list('skill__slug', flat=True)
    )

    return render(request, 'learning_path/learning_path.html', {
        'already_registered': True,
        'analysis':        analysis,
        'session':         analysis.class_session,
        'student':         analysis.student,
        'skill_path':      skill_path,
        'done_slugs':      done_slugs,
    })


def _select_lp_questions(skill, mastery_score):
    """
    Pick a curated list of question IDs for the learning-path practice session.
    Rules:
      - Struggling  (< 0.30): 3 questions, Easy → Medium → Hard, video priority
      - Learning    (< 0.50): 3 questions, Easy → Medium → Hard, video priority
      - Developing  (< 0.75): 2 questions, Medium → Hard → Easy, video priority
      - Mastered    (≥ 0.75): 2 questions, Hard → Medium → Easy, video priority
      - Minimum always 2
    """
    import random as _rand

    if mastery_score < 0.30:
        count, diff_pref = 3, ['Easy', 'Medium', 'Hard']
    elif mastery_score < 0.50:
        count, diff_pref = 3, ['Easy', 'Medium', 'Hard']
    elif mastery_score < 0.75:
        count, diff_pref = 2, ['Medium', 'Hard', 'Easy']
    else:
        count, diff_pref = 2, ['Hard', 'Medium', 'Easy']

    diff_rank = {d: i for i, d in enumerate(diff_pref)}

    # Resolve tagged question IDs (subquestion-level first, then question-level)
    sq_ids = set(
        RevisionSubQuestion.objects.filter(skills=skill)
        .values_list('question_id', flat=True).distinct()
    )
    if sq_ids:
        tagged_ids = list(sq_ids)
    else:
        tagged_ids = list(
            QuestionSkillTag.objects.filter(skill=skill)
            .filter(question__subquestions__isnull=False)
            .values_list('question_id', flat=True).distinct()
        )

    if not tagged_ids:
        return []

    questions = list(Math_AI_SL_Questionbank.objects.filter(id__in=tagged_ids))

    def q_score(q):
        has_video = 0 if (q.video and q.video.strip() and q.video.strip().lower() != 'none') else 1
        diff      = diff_rank.get(q.difficulty, 99)
        return (has_video, diff, _rand.random())

    questions.sort(key=q_score)
    return [q.id for q in questions[:max(2, count)]]


def learning_path_practice(request, skill_slug):
    """Practice view launched from the learning path — curated question set based on mastery."""
    user = _get_revision_user(request)
    if not user:
        return redirect('login')

    try:
        skill = RevisionSkill.objects.select_related('topic__chapter').get(slug=skill_slug)
    except RevisionSkill.DoesNotExist:
        return redirect('revision-engine')

    mastery_obj   = StudentSkillMastery.objects.filter(user=user, skill=skill).first()
    mastery_score = mastery_obj.mastery_score if mastery_obj else 0.3

    ids_param   = request.GET.get('ids', '')
    pos         = int(request.GET.get('pos', 0))
    back        = request.GET.get('back', '')

    # First hit — select the question set, then redirect with ids in the URL
    if not ids_param:
        selected_ids = _select_lp_questions(skill, mastery_score)
        if not selected_ids:
            return render(request, 'revision_engine/practice.html', {
                'already_registered': True,
                'skill': skill,
                'question': None,
                'no_questions': True,
            })
        ids_str = ','.join(str(i) for i in selected_ids)
        from django.urls import reverse as _rev
        base = _rev('learning-path-practice', kwargs={'skill_slug': skill_slug})
        return redirect(f'{base}?ids={ids_str}&pos=0&back={back}')

    # Parse IDs
    try:
        ids = [int(x) for x in ids_param.split(',') if x.strip()]
    except ValueError:
        return redirect('revision-engine')

    from django.urls import reverse as _rev
    back_url = _rev('learning-path', kwargs={'analysis_id': int(back)}) if back.isdigit() else _rev('revision-engine')

    # Completed all questions in the set
    if pos >= len(ids):
        # Mark this skill as completed in the database
        if back.isdigit():
            try:
                analysis_obj = ClassTranscriptAnalysis.objects.get(id=int(back))
                LearningPathProgress.objects.get_or_create(
                    student=user,
                    analysis=analysis_obj,
                    skill=skill,
                )
            except ClassTranscriptAnalysis.DoesNotExist:
                pass

        return render(request, 'revision_engine/practice.html', {
            'already_registered': True,
            'skill': skill,
            'question': None,
            'no_questions': False,
            'lp_complete': True,
            'lp_total': len(ids),
            'back_url': back_url,
            'mastery': mastery_obj,
            'mastery_percent': round(mastery_score * 100),
            'mastery_color': re_service.get_mastery_color(mastery_score),
        })

    question = Math_AI_SL_Questionbank.objects.get(id=ids[pos])

    next_pos  = pos + 1
    base      = _rev('learning-path-practice', kwargs={'skill_slug': skill_slug})
    next_url  = f'{base}?ids={ids_param}&pos={next_pos}&back={back}'

    subquestions_data = []
    for sq in question.subquestions.prefetch_related('options', 'skills').order_by('order', 'id'):
        subquestions_data.append({
            'id': sq.id,
            'part_label': sq.part_label,
            'question_text': sq.question_text,
            'options': [
                {'label': o.label, 'text': o.option_text, 'is_correct': o.is_correct}
                for o in sq.options.all()
            ],
        })

    import json as _json2
    return render(request, 'revision_engine/practice.html', {
        'already_registered': True,
        'user_type':       request.session.get('user_type', 'free'),
        'skill':           skill,
        'question':        question,
        'mastery':         mastery_obj,
        'mastery_percent': round(mastery_score * 100),
        'mastery_color':   re_service.get_mastery_color(mastery_score),
        'total_tagged':    len(ids),
        'no_questions':    False,
        'subquestions_json': _json2.dumps(subquestions_data),
        'has_mcq':         len(subquestions_data) > 0,
        'answer_json':     _json2.dumps(question.answer or ''),
        # LP-specific
        'next_url':   next_url,
        'back_url':   back_url,
        'lp_pos':     pos + 1,
        'lp_total':   len(ids),
        'lp_complete': False,
    })


def parent_admin(request):
    """Parent admin panel view - shows their child's tutoring sessions filtered by parent email"""
    # Check if user is logged in
    if not request.session.get('already_registered', False):
        return redirect('login')
    
    # Get user email from session
    user_email = request.session.get('email', '')
    
    try:
        # Get user data
        user_data = Users.objects.get(email=user_email)
        
        # Check if user is a parent
        if user_data.occupation != 'Parent':
            messages.error(request, 'Access denied. Only parents can access this page.')
            return redirect('home')
            
    except Users.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('login')
    
    # Get all students managed by this parent
    managed_students = StudentManagement.objects.filter(parent_email=user_email)
    
    # If no students are managed by this parent, return empty sessions
    if not managed_students.exists():
        sessions = TutorSession.objects.none()
    else:
        # Get all student emails for this parent
        student_emails = []
        
        for student in managed_students:
            # Use linked_user email if available, otherwise use student_email
            if student.linked_user:
                student_emails.append(student.linked_user.email)
            elif student.student_email:
                student_emails.append(student.student_email)
        
        # Get sessions for all students of this parent by email
        if student_emails:
            sessions = TutorSession.objects.filter(student_email__in=student_emails).order_by('-session_time')
        else:
            sessions = TutorSession.objects.none()
    
    # Add hourly rate information to each session
    for session in sessions:
        # Find the corresponding StudentManagement record to get pricing for this specific tutor
        session.hourly_rate = None
        
        for student_mgmt in managed_students:
            # Match by email if available AND by tutor
            if (session.student_email and student_mgmt.student_email and 
                session.student_email == student_mgmt.student_email and
                session.tutor == student_mgmt.assigned_tutor):
                session.hourly_rate = student_mgmt.price_charged_display
                break
            # Match by name if no email match AND by tutor
            elif (session.student_first_name == student_mgmt.student_first_name and 
                  session.student_last_name == student_mgmt.student_last_name and
                  session.tutor == student_mgmt.assigned_tutor):
                session.hourly_rate = student_mgmt.price_charged_display
                break
    
    # Calculate statistics
    from datetime import datetime
    from django.db.models import Sum
    from decimal import Decimal
    
    # Total sessions (all time, all statuses)
    total_sessions_count = sessions.count()
    
    # Completed sessions (all time)
    completed_sessions = sessions.filter(status='Completed')
    
    # Total hours (sum of all hours_taught)
    total_hours_data = sessions.aggregate(total=Sum('hours_taught'))
    total_hours = total_hours_data['total'] or 0
    
    # Calculate total payment (hourly rate × hours for each session)
    total_payment = Decimal('0.00')
    payment_currency = 'EUR'  # Default currency
    
    for session in sessions:
        # Only count completed and missed classes for payment
        if session.status in ['Completed', 'Missed'] and session.hours_taught and session.hourly_rate:
            try:
                # Find the corresponding StudentManagement record to get raw price and currency for this specific tutor
                for student_mgmt in managed_students:
                    if ((session.student_email and student_mgmt.student_email and 
                         session.student_email == student_mgmt.student_email and
                         session.tutor == student_mgmt.assigned_tutor) or
                        (session.student_first_name == student_mgmt.student_first_name and 
                         session.student_last_name == student_mgmt.student_last_name and
                         session.tutor == student_mgmt.assigned_tutor)):
                        session_cost = student_mgmt.price_charged_to_parents * Decimal(str(session.hours_taught))
                        total_payment += session_cost
                        # Use the currency from the first session found
                        if payment_currency == 'EUR':  # Only set once
                            payment_currency = student_mgmt.price_charged_currency
                        break
            except (ValueError, TypeError):
                continue
    
    # Format total payment with correct currency symbol
    currency_symbols = {
        'EUR': '€',
        'GBP': '£',
        'USD': '$',
        'PLN': 'zł',
    }
    currency_symbol = currency_symbols.get(payment_currency, payment_currency)
    formatted_total_payment = f"{total_payment:.2f} ({currency_symbol})"
    
    # Get available months from sessions
    from django.db.models import Q
    from collections import OrderedDict
    from django.db.models.functions import TruncMonth
    
    # Get unique months from sessions
    available_months = []
    if sessions.exists():
        # Get all unique year-month combinations from sessions using PostgreSQL-compatible syntax
        month_data = sessions.annotate(
            year_month=TruncMonth('session_time')
        ).values_list('year_month', flat=True).distinct().order_by('-year_month')
        
        # Convert to readable format
        month_names = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        
        for date_obj in month_data:
            year = date_obj.year
            month = date_obj.month
            year_month = f"{year}-{month:02d}"
            month_name = month_names.get(month, str(month))
            available_months.append({
                'value': year_month,
                'label': f'{month_name} {year}'
            })
    
    # Check if rules have been accepted by PARENT
    rules_accepted = False
    try:
        # Use filter().first() to handle multiple records with same email
        student_mgmt = StudentManagement.objects.filter(parent_email=user_email).first()
        if student_mgmt:
            rules_accepted = student_mgmt.parent_rules_accepted
    except Exception as e:
        pass
    
    context = {
        'sessions': sessions,
        'parent_name': f'{user_data.first_name} {user_data.last_name}',
        'has_sessions': sessions.exists(),
        'available_months': available_months,
        'payment_currency': payment_currency,
        'currency_symbol': currency_symbol,
        # Statistics for dashboard
        'total_sessions': total_sessions_count,
        'completed_sessions': completed_sessions.count(),
        'total_hours': total_hours,
        'total_payment': formatted_total_payment,
        'rules_accepted': rules_accepted,
    }
    
    return render(request, 'parent_admin.html', context)


def admin_student_management(request):
    """Admin panel for managing students with pricing and tutor assignment"""
    # Check if user is logged in
    if not request.session.get('already_registered', False):
        return redirect('login')
    
    # Get user email from session
    user_email = request.session.get('email', '')
    
    try:
        # Get user data
        user_data = Users.objects.get(email=user_email)
        
        # Check if user is admin (you can customize this logic)
        # For now, allowing all logged-in users, but you can restrict to specific emails or add an admin role
        # if user_data.occupation != 'Admin':
        #     messages.error(request, 'Access denied. Only admins can access this page.')
        #     return redirect('home')
            
    except Users.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('login')
    
    # Handle POST request (adding or editing student)
    if request.method == 'POST':
        try:
            # Check if this is an edit or add operation
            edit_student_id = request.POST.get('edit_student_id', '')
            
            # Get form data
            linked_user_id = request.POST.get('linked_user', '')
            student_first_name = request.POST.get('student_first_name')
            student_last_name = request.POST.get('student_last_name')
            student_email = request.POST.get('student_email', '')
            parent_email = request.POST.get('parent_email')
            parent_phone = request.POST.get('parent_phone', '')
            address = request.POST.get('address')
            assigned_tutor_id = request.POST.get('assigned_tutor')
            price_charged = request.POST.get('price_charged_to_parents')
            price_charged_currency = request.POST.get('price_charged_currency', 'EUR')
            price_given = request.POST.get('price_given_to_tutor')
            price_given_currency = request.POST.get('price_given_currency', 'EUR')
            curriculum = request.POST.get('curriculum', '')
            subjects = request.POST.get('subjects', '')
            notes = request.POST.get('notes', '')
            
            
            # Get assigned tutor (can be Tutor or Admin)
            assigned_tutor = Users.objects.get(id=assigned_tutor_id, occupation__in=['Tutor', 'Admin'])
            
            # Get linked user if provided
            linked_user = None
            if linked_user_id:
                linked_user = Users.objects.get(id=linked_user_id, occupation='Student')
            
            if edit_student_id:
                # UPDATE existing student
                student_mgmt = StudentManagement.objects.get(id=edit_student_id)
                student_mgmt.linked_user = linked_user
                student_mgmt.student_first_name = student_first_name
                student_mgmt.student_last_name = student_last_name
                student_mgmt.student_email = student_email
                student_mgmt.parent_email = parent_email
                student_mgmt.parent_phone = parent_phone
                student_mgmt.address = address
                student_mgmt.assigned_tutor = assigned_tutor
                student_mgmt.price_charged_to_parents = float(price_charged)
                student_mgmt.price_charged_currency = price_charged_currency
                student_mgmt.price_given_to_tutor = float(price_given)
                student_mgmt.price_given_currency = price_given_currency
                student_mgmt.curriculum = curriculum
                student_mgmt.subjects = subjects
                student_mgmt.notes = notes
                student_mgmt.save()
                
                messages.success(request, f'Student {student_first_name} {student_last_name} updated successfully!')
            else:
                # CREATE new student management record
                student_mgmt = StudentManagement.objects.create(
                    linked_user=linked_user,
                    student_first_name=student_first_name,
                    student_last_name=student_last_name,
                    student_email=student_email,
                    parent_email=parent_email,
                    parent_phone=parent_phone,
                    address=address,
                    assigned_tutor=assigned_tutor,
                    price_charged_to_parents=float(price_charged),
                    price_charged_currency=price_charged_currency,
                    price_given_to_tutor=float(price_given),
                    price_given_currency=price_given_currency,
                    curriculum=curriculum,
                    subjects=subjects,
                    notes=notes
                )
                
                messages.success(request, f'Student {student_first_name} {student_last_name} added successfully!')
            
            return redirect('admin-student-management')
            
        except Users.DoesNotExist:
            messages.error(request, 'Selected tutor or linked user not found.')
        except StudentManagement.DoesNotExist:
            messages.error(request, 'Student not found for editing.')
        except Exception as e:
            messages.error(request, f'Error processing student: {str(e)}')
    
    # Get all tutors for the dropdown
    tutors = Users.objects.filter(occupation__in=['Tutor', 'Admin']).order_by('first_name', 'last_name')
    
    # Get all users for linking (admin can link to anyone)
    existing_students = Users.objects.all().order_by('first_name', 'last_name')
    
    # Get all managed students
    managed_students = StudentManagement.objects.all().order_by('-created_date')
    
    context = {
        'tutors': tutors,
        'existing_students': existing_students,
        'managed_students': managed_students,
        'admin_name': f'{user_data.first_name} {user_data.last_name}'
    }
    
    return render(request, 'admin_student_management.html', context)


def delete_managed_student(request, student_id):
    """Delete a managed student"""
    if request.method == 'POST':
        # Check if user is logged in
        if not request.session.get('already_registered', False):
            messages.error(request, 'Authentication required.')
            return redirect('login')
        
        # Get user email from session
        user_email = request.session.get('email', '')
        
        try:
            # Get user data
            user_data = Users.objects.get(email=user_email)
            
            # Check if user has permission (you can customize this logic)
            # For now, allowing all logged-in users, but you can restrict to admins
            # if user_data.occupation != 'Admin':
            #     messages.error(request, 'Access denied. Only admins can delete students.')
            #     return redirect('admin-student-management')
            
            # Get and delete the managed student
            managed_student = StudentManagement.objects.get(id=student_id)
            student_name = f"{managed_student.student_first_name} {managed_student.student_last_name}"
            managed_student.delete()
            
            messages.success(request, f'Student {student_name} has been deleted successfully.')
            
        except Users.DoesNotExist:
            messages.error(request, 'User not found.')
        except StudentManagement.DoesNotExist:
            messages.error(request, 'Student not found.')
        except Exception as e:
            messages.error(request, f'Error deleting student: {str(e)}')
    
    return redirect('admin-student-management')


def remove_users_db(request):
    """Remove users from the database"""
    # Check if user is logged in
    if not request.session.get('already_registered', False):
        return redirect('login')
    
    # Get user email from session
    user_email = request.session.get('email', '')
    
    try:
        # Get user data
        user_data = Users.objects.get(email=user_email)
        
        # Optional: Add permission check for admin-only access
        # if user_data.occupation != 'Admin':
        #     messages.error(request, 'Access denied. Only admins can access this page.')
        #     return redirect('home')
            
    except Users.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('login')
    
    # Handle POST request (deleting user)
    if request.method == 'POST':
        user_id_to_delete = request.POST.get('user_to_delete')
        
        if user_id_to_delete:
            try:
                # Get the user to delete
                user_to_delete = Users.objects.get(id=user_id_to_delete)
                user_name = f"{user_to_delete.first_name} {user_to_delete.last_name}"
                user_email_to_delete = user_to_delete.email
                
                # Prevent self-deletion
                if user_to_delete.email == user_email:
                    messages.error(request, 'You cannot delete your own account.')
                    return redirect('remove-users-db')
                
                # Try to delete the user with detailed error reporting
                try:
                    # Check what related objects would be deleted
                    related_sessions_as_tutor = TutorSession.objects.filter(tutor=user_to_delete).count()
                    related_sessions_as_student = TutorSession.objects.filter(student=user_to_delete).count()
                    related_managed_students = StudentManagement.objects.filter(assigned_tutor=user_to_delete).count()
                    related_linked_students = StudentManagement.objects.filter(linked_user=user_to_delete).count()
                    
                    # Check for corresponding Django admin user
                    django_user_deleted = False
                    try:
                        django_user = DjangoUser.objects.get(email=user_email_to_delete)
                        django_user.delete()
                        django_user_deleted = True
                    except DjangoUser.DoesNotExist:
                        pass  # No corresponding Django user found
                    except Exception as django_error:
                        messages.warning(request, f'Warning: Could not delete Django admin user: {str(django_error)}')
                    
                    # Delete the custom user
                    user_to_delete.delete()
                    
                    deletion_info = []
                    if related_sessions_as_tutor > 0:
                        deletion_info.append(f"{related_sessions_as_tutor} tutor sessions")
                    if related_sessions_as_student > 0:
                        deletion_info.append(f"{related_sessions_as_student} student sessions")
                    if related_managed_students > 0:
                        deletion_info.append(f"{related_managed_students} managed student records")
                    if related_linked_students > 0:
                        deletion_info.append(f"{related_linked_students} linked student records (set to null)")
                    if django_user_deleted:
                        deletion_info.append("Django admin user")
                    
                    success_msg = f'User {user_name} ({user_email_to_delete}) has been deleted successfully from both systems.'
                    if deletion_info:
                        success_msg += f' Also removed: {", ".join(deletion_info)}.'
                    
                    messages.success(request, success_msg)
                    return redirect('remove-users-db')
                    
                except Exception as delete_error:
                    messages.error(request, f'Failed to delete user {user_name}: {str(delete_error)}')
                    return redirect('remove-users-db')
                
            except Users.DoesNotExist:
                messages.error(request, 'Selected user not found.')
            except Exception as e:
                messages.error(request, f'Error deleting user: {str(e)}')
        else:
            messages.error(request, 'Please select a user to delete.')
    
    # Get all users for the dropdown (exclude current user)
    all_users = Users.objects.exclude(email=user_email).order_by('first_name', 'last_name')
    
    # Also get Django admin users (optional - for display purposes)
    django_users = DjangoUser.objects.all().order_by('first_name', 'last_name')
    
    context = {
        'all_users': all_users,
        'django_users': django_users,
        'admin_name': f'{user_data.first_name} {user_data.last_name}',
        'total_users': all_users.count(),
        'total_django_users': django_users.count()
    }
    
    return render(request, 'remove_users_db.html', context)


def delete_tutor_session(request, session_id):
    """Delete a tutor session"""
    if not request.session.get('already_registered', False):
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    user_email = request.session.get('email', '')
    
    try:
        user_data = Users.objects.get(email=user_email)
        
        if user_data.occupation not in ['Tutor', 'Admin']:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get session - admins can delete any session, tutors can only delete their own
        if user_data.occupation == 'Admin':
            session = TutorSession.objects.get(id=session_id)
        else:
            session = TutorSession.objects.get(id=session_id, tutor=user_data)
        session.delete()
        
        return JsonResponse({'success': True, 'message': 'Session deleted successfully'})
        
    except (Users.DoesNotExist, TutorSession.DoesNotExist):
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def update_session_status(request, session_id):
    """Update session status"""
    if not request.session.get('already_registered', False):
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    user_email = request.session.get('email', '')
    
    try:
        user_data = Users.objects.get(email=user_email)
        
        if user_data.occupation not in ['Tutor', 'Admin']:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get session - admins can update any session, tutors can only update their own
        if user_data.occupation == 'Admin':
            session = TutorSession.objects.get(id=session_id)
        else:
            session = TutorSession.objects.get(id=session_id, tutor=user_data)
        
        new_status = request.POST.get('status')
        if new_status in ['Scheduled', 'Completed', 'Cancelled']:
            session.status = new_status
            session.save()
            return JsonResponse({'success': True, 'message': f'Session marked as {new_status}'})
        else:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
    except (Users.DoesNotExist, TutorSession.DoesNotExist):
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def student_preview_ajax(request, student_id):
    """AJAX endpoint to get student sessions for preview - simplified version"""
    from django.http import JsonResponse
    from django.db.models import Sum
    
    # Simple test first
    if student_id == 0:
        return JsonResponse({'success': True, 'message': 'Test endpoint working', 'student_id': student_id})
    
    try:
        # Get the managed student
        managed_student = StudentManagement.objects.get(id=student_id)
        
        # Get student email (either from linked user or student_email field)
        student_email = None
        if managed_student.linked_user:
            student_email = managed_student.linked_user.email
        elif managed_student.student_email:
            student_email = managed_student.student_email
        
        if not student_email:
            return JsonResponse({
                'success': False, 
                'message': 'No email found for this student. Please link a user account or add an email.'
            })
        
        # Get sessions for this student by email
        sessions = TutorSession.objects.filter(student_email=student_email).order_by('-session_time')
        
        # Calculate statistics (same as student_admin)
        total_sessions_count = sessions.count()
        completed_sessions = sessions.filter(status='Completed')
        upcoming_sessions = sessions.filter(status='Upcoming')
        
        # Total hours (sum of all hours_taught)
        total_hours_data = sessions.aggregate(total=Sum('hours_taught'))
        total_hours = total_hours_data['total'] or 0
        
        # Format sessions for JSON response
        sessions_data = []
        for session in sessions:
            session_data = {
                'student_first_name': session.student_first_name,
                'student_last_name': session.student_last_name,
                'session_date': session.session_time.strftime('%b %d, %Y'),
                'session_time': session.session_time.strftime('%H:%M'),
                'subject': session.get_subject_display(),
                'topic': session.topic,
                'tutor_first_name': session.tutor_first_name,
                'tutor_last_name': session.tutor_last_name,
                'curriculum': session.student.curriculum if session.student else None,
                'hours_taught': session.hours_taught,
                'status': session.status,
                'homework_comments': session.homework_comments,
                'has_pdf': bool(session.session_pdf),
                'session_pdf_url': session.session_pdf.url if session.session_pdf else None
            }
            sessions_data.append(session_data)
        
        # Prepare response data
        response_data = {
            'success': True,
            'student_name': f"{managed_student.student_first_name} {managed_student.student_last_name}",
            'sessions': sessions_data,
            'stats': {
                'total_sessions': total_sessions_count,
                'completed_sessions': completed_sessions.count(),
                'total_hours': total_hours,
                'upcoming_sessions': upcoming_sessions.count()
            }
        }
        
        return JsonResponse(response_data)
        
    except StudentManagement.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Student not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error loading student data: {str(e)}'})


def add_premium_members(request):
    """Add premium membership to users"""
    # Check if user is logged in
    if not request.session.get('already_registered', False):
        return redirect('login')
    
    # Get user email from session
    user_email = request.session.get('email', '')
    
    try:
        # Get user data
        user_data = Users.objects.get(email=user_email)
        
        # Check if user is an admin
        if user_data.occupation != 'Admin':
            messages.error(request, 'Access denied. Only admins can access this page.')
            return redirect('home')
            
    except Users.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('login')
    
    # Handle POST request (adding premium membership)
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        days = request.POST.get('days')
        
        try:
            # Get the user to add premium to
            target_user = Users.objects.get(id=user_id)
            
            # Calculate subscription end date
            from datetime import datetime, timedelta
            from django.utils import timezone
            today = timezone.now()
            end_date = today + timedelta(days=int(days))
            
            # Check if user already has premium membership
            existing_premium = Premium_Members.objects.filter(customer_id=target_user.customer_id).first()
            
            if existing_premium:
                # Update existing membership
                existing_premium.subscription_end_date = end_date
                existing_premium.subscribed = "Yes"
                existing_premium.first_name = target_user.first_name
                existing_premium.last_name = target_user.last_name
                existing_premium.email = target_user.email
                existing_premium.save()
                messages.success(request, f'Premium membership updated for {target_user.first_name} {target_user.last_name} until {end_date.strftime("%Y-%m-%d")}')
            else:
                # Create new premium membership
                Premium_Members.objects.create(
                    customer_id=target_user.customer_id,
                    stripe_customer_id="FREE",
                    first_name=target_user.first_name,
                    last_name=target_user.last_name,
                    email=target_user.email,
                    subscribed="Yes",
                    subscription_end_date=end_date
                )
                messages.success(request, f'Premium membership added for {target_user.first_name} {target_user.last_name} until {end_date.strftime("%Y-%m-%d")}')
            
            return redirect('add-premium-members')
            
        except Users.DoesNotExist:
            messages.error(request, 'Selected user not found.')
        except ValueError:
            messages.error(request, 'Please enter a valid number of days.')
        except Exception as e:
            messages.error(request, f'Error adding premium membership: {str(e)}')
    
    # Get all users for the dropdown
    all_users = Users.objects.all().order_by('first_name', 'last_name')
    
    # Get current premium members
    premium_members = Premium_Members.objects.filter(subscribed="Yes")
    
    context = {
        'all_users': all_users,
        'premium_members': premium_members,
        'admin_name': f'{user_data.first_name} {user_data.last_name}'
    }
    
    return render(request, 'add_premium_members.html', context)


@csrf_exempt
def accept_tutoring_rules(request):
    """API endpoint to save tutoring rules acceptance"""
    if request.method == 'POST':
        import json
        from django.utils import timezone
        
        # Check if user is logged in
        if not request.session.get('already_registered', False):
            return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
        
        user_email = request.session.get('email', '')
        
        try:
            # Determine if user is student or parent
            user_data = Users.objects.get(email=user_email)
            is_parent = user_data.occupation == 'Parent'
            
            # Find records and update the appropriate field
            if is_parent:
                # Parent accepting rules
                student_mgmt_records = StudentManagement.objects.filter(parent_email=user_email)
                if not student_mgmt_records.exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Parent management record not found'
                    }, status=404)
                
                updated_count = student_mgmt_records.update(
                    parent_rules_accepted=True,
                    parent_rules_accepted_date=timezone.now()
                )
            else:
                # Student accepting rules
                student_mgmt_records = StudentManagement.objects.filter(student_email=user_email)
                if not student_mgmt_records.exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Student management record not found'
                    }, status=404)
                
                updated_count = student_mgmt_records.update(
                    student_rules_accepted=True,
                    student_rules_accepted_date=timezone.now()
                )
            
            return JsonResponse({
                'success': True,
                'message': f'Rules accepted successfully for {updated_count} record(s)'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@csrf_exempt
def generate_similar_question_api(request):
    """
    API endpoint to generate a similar IB Math question using RAG.
    
    POST /api/generate-similar-question/
    Body: {
        "question": "Original question HTML",
        "answer": "Original answer/explanation HTML",
        "topic": "Optional topic hint"
    }
    
    Returns: {
        "success": true/false,
        "question": "Generated question HTML",
        "error": "Error message if failed"
    }
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    # Check if user is logged in and premium
    user_type = request.session.get('user_type', 'none')
    if user_type != 'premium':
        return JsonResponse({
            'success': False, 
            'error': 'Premium subscription required to generate questions'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        original_question = data.get('question', '')
        original_answer = data.get('answer', '')
        subject = data.get('subject', '')
        topic = data.get('topic', '')
        temperature = data.get('temperature', 0.9)  # Default to 0.9
        custom_instructions = data.get('customInstructions', '')
        
        # Validate temperature
        try:
            temperature = float(temperature)
            temperature = max(0.0, min(2.0, temperature))  # Clamp between 0 and 2
        except (ValueError, TypeError):
            temperature = 0.9
        
        if not original_question:
            return JsonResponse({
                'success': False,
                'error': 'Question content is required'
            }, status=400)
        
        # Import and use the RAG question generator
        import sys
        from pathlib import Path
        
        # Add the scripts directory to path
        scripts_path = Path(__file__).parent.parent / 'scripts' / 'rag_pipeline'
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))
        
        from question_generator import generate_similar_question
        
        result = generate_similar_question(
            original_question=original_question,
            original_answer=original_answer,
            subject=subject,
            topic=topic,
            temperature=temperature,
            custom_instructions=custom_instructions
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error generating similar question: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error generating question: {str(e)}'
        }, status=500)


def ai_question_generator(request):
    """
    Dedicated AI Question Generator page.
    Allows users to select a subject, topic, and question to generate similar questions.
    """
    # Check if user is logged in
    if not request.session.get('already_registered', False):
        messages.warning(request, 'Please log in to access the AI Question Generator.')
        return redirect('login')
    
    # Get user type
    user_type = request.session.get('user_type', 'none')
    
    context = {
        'user_type': user_type,
    }
    
    return render(request, 'ai_question_generator.html', context)


def ai_question_generator_2(request):
    """
    AI Question Generator page for Past Papers.
    Allows users to select questions from IB past paper PDFs.
    """
    # Check if user is logged in
    if not request.session.get('already_registered', False):
        messages.warning(request, 'Please log in to access the AI Question Generator.')
        return redirect('login')
    
    # Get user type
    user_type = request.session.get('user_type', 'none')
    
    # Get available past papers
    import sys
    from pathlib import Path
    
    # Add the scripts directory to path
    scripts_path = Path(__file__).parent.parent / 'scripts' / 'rag_pipeline'
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    
    try:
        from latex_question_parser import get_available_papers
        
        # Path to past papers directory
        past_papers_dir = Path(__file__).parent.parent / 'static' / 'website' / 'images' / 'pdfs' / 'past_papers'
        available_papers = get_available_papers(str(past_papers_dir))
    except Exception as e:
        logger.error(f"Error loading past papers: {str(e)}")
        available_papers = []
    
    context = {
        'user_type': user_type,
        'available_papers': available_papers,
    }
    
    return render(request, 'ai_question_generator_2.html', context)


def get_topics_api(request):
    """
    API endpoint to get topics for a given subject.
    GET /api/get-topics/?subject=math_aa_hl
    """
    subject = request.GET.get('subject', '')
    
    if not subject:
        return JsonResponse({'success': False, 'error': 'Subject parameter required'}, status=400)
    
    try:
        # Import the appropriate model based on subject
        from .models import (
            MathAASL, MathAAHL, MathAISL, MathAIHL,
            PhysicsSL, PhysicsHL, ChemistrySL, ChemistryHL,
            BiologySL, BiologyHL, CompSciSL, CompSciHL
        )
        
        # Map subject codes to models
        subject_models = {
            'math_aa_sl': MathAASL,
            'math_aa_hl': MathAAHL,
            'math_ai_sl': MathAISL,
            'math_ai_hl': MathAIHL,
            'physics_sl': PhysicsSL,
            'physics_hl': PhysicsHL,
            'chemistry_sl': ChemistrySL,
            'chemistry_hl': ChemistryHL,
            'biology_sl': BiologySL,
            'biology_hl': BiologyHL,
            'comp_sci_sl': CompSciSL,
            'comp_sci_hl': CompSciHL,
        }
        
        model = subject_models.get(subject)
        if not model:
            return JsonResponse({'success': False, 'error': 'Invalid subject'}, status=400)
        
        # Get distinct topics from the model
        topics = model.objects.values_list('topic', flat=True).distinct().order_by('topic')
        topics_list = [topic for topic in topics if topic]  # Filter out None/empty values
        
        return JsonResponse({
            'success': True,
            'topics': topics_list
        })
        
    except Exception as e:
        logger.error(f"Error fetching topics: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_questions_api(request):
    """
    API endpoint to get questions for a given subject and topic.
    GET /api/get-questions/?subject=math_aa_hl&topic=Calculus
    """
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    
    if not subject or not topic:
        return JsonResponse({'success': False, 'error': 'Subject and topic parameters required'}, status=400)
    
    try:
        # Import the appropriate model based on subject
        from .models import (
            MathAASL, MathAAHL, MathAISL, MathAIHL,
            PhysicsSL, PhysicsHL, ChemistrySL, ChemistryHL,
            BiologySL, BiologyHL, CompSciSL, CompSciHL
        )
        
        # Map subject codes to models
        subject_models = {
            'math_aa_sl': MathAASL,
            'math_aa_hl': MathAAHL,
            'math_ai_sl': MathAISL,
            'math_ai_hl': MathAIHL,
            'physics_sl': PhysicsSL,
            'physics_hl': PhysicsHL,
            'chemistry_sl': ChemistrySL,
            'chemistry_hl': ChemistryHL,
            'biology_sl': BiologySL,
            'biology_hl': BiologyHL,
            'comp_sci_sl': CompSciSL,
            'comp_sci_hl': CompSciHL,
        }
        
        model = subject_models.get(subject)
        if not model:
            return JsonResponse({'success': False, 'error': 'Invalid subject'}, status=400)
        
        # Get questions for the topic (limit to 50 for performance)
        questions = model.objects.filter(topic=topic)[:50]
        
        questions_list = []
        for q in questions:
            questions_list.append({
                'id': q.id,
                'question': q.question if hasattr(q, 'question') else '',
                'answer': q.answer if hasattr(q, 'answer') else '',
                'topic': q.topic if hasattr(q, 'topic') else '',
            })
        
        return JsonResponse({
            'success': True,
            'questions': questions_list
        })
        
    except Exception as e:
        logger.error(f"Error fetching questions: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_pdf_questions_api(request):
    """
    API endpoint to get questions from a specific past paper (LaTeX or PDF).
    
    GET /api/pdf-questions/?paper=math_ai_sl/may23tz1/paper1_questions
    
    Returns: {
        "success": true/false,
        "questions": [...],
        "error": "Error message if failed"
    }
    """
    paper = request.GET.get('paper', '')
    
    if not paper:
        return JsonResponse({'success': False, 'error': 'Paper parameter required'}, status=400)
    
    try:
        import sys
        from pathlib import Path
        
        # Add the scripts directory to path
        scripts_path = Path(__file__).parent.parent / 'scripts' / 'rag_pipeline'
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))
        
        # Build path to file (try LaTeX first, then PDF)
        past_papers_dir = Path(__file__).parent.parent / 'static' / 'website' / 'images' / 'pdfs' / 'past_papers'
        tex_path = past_papers_dir / f"{paper}.tex"
        pdf_path = past_papers_dir / f"{paper}.pdf"
        
        if tex_path.exists():
            # Use LaTeX parser
            from latex_question_parser import parse_past_paper_latex
            questions = parse_past_paper_latex(str(tex_path))
        elif pdf_path.exists():
            # Fall back to PDF parser
            from pdf_question_parser import parse_past_paper_pdf
            questions = parse_past_paper_pdf(str(pdf_path))
        else:
            return JsonResponse({
                'success': False,
                'error': f'Paper file not found: {paper}'
            }, status=404)
        
        return JsonResponse({
            'success': True,
            'questions': questions,
            'paper': paper
        })
        
    except Exception as e:
        logger.error(f"Error parsing paper questions: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error parsing paper: {str(e)}'
        }, status=500)


def generate_explanation_api(request):
    """
    API endpoint to generate an explanation/answer for a given question using AI.
    
    POST /api/generate-explanation/
    Body: {
        "question": "Question HTML",
        "subject": "Subject name",
        "topic": "Topic name"
    }
    
    Returns: {
        "success": true/false,
        "explanation": "Generated explanation HTML",
        "error": "Error message if failed"
    }
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    # Check if user is logged in and premium
    user_type = request.session.get('user_type', 'none')
    if user_type != 'premium':
        return JsonResponse({
            'success': False, 
            'error': 'Premium subscription required to generate explanations'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        question = data.get('question', '')
        subject = data.get('subject', '')
        topic = data.get('topic', '')
        
        if not question:
            return JsonResponse({
                'success': False,
                'error': 'Question content is required'
            }, status=400)
        
        # Import and use the RAG explanation generator
        import sys
        from pathlib import Path
        
        # Add the scripts directory to path
        scripts_path = Path(__file__).parent.parent / 'scripts' / 'rag_pipeline'
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))
        
        from question_generator import generate_explanation
        
        result = generate_explanation(
            question=question,
            subject=subject,
            topic=topic
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error generating explanation: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error generating explanation: {str(e)}'
        }, status=500)


########################################################
# HISTORY SL QUESTIONBANK
########################################################

class HistorySLQuestionsListAPIView(BaseQuestionBankListAPIView):
    serializer_class = History_SL_QuestionbankSerializer

    def get_queryset(self):
        queryset = History_SL_Questionbank.objects.all()
        paper = self.request.GET.get('paper')
        difficulty = self.request.GET.get('difficulty')
        chapter = self.request.GET.get('chapter')

        papers = self.request.GET.getlist('papers[]')
        if papers:
            queryset = queryset.filter(paper__in=papers)
        elif paper:
            queryset = queryset.filter(paper=paper)

        difficulties = self.request.GET.getlist('difficulties[]')
        if difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)
        elif difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if chapter:
            queryset = queryset.filter(chapter=chapter)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        available_papers = list(queryset.values_list('paper', flat=True).distinct())
        available_difficulties = list(queryset.values_list('difficulty', flat=True).distinct())
        
        serializer = self.get_serializer(queryset, many=True)
        questions_data = serializer.data
        
        return Response({
            'questions': questions_data,
            'metadata': {
                'available_papers': available_papers,
                'available_difficulties': available_difficulties
            }
        })

@track_user_journey
def history_sl(request):
    return render(request, 'questionbank/history/sl/history_sl.html')

@track_user_journey
def emergence_democratic_states_sl(request):
    return render_math_topic(request, 'questionbank/history/sl/emergence_democratic_states_sl.html', 'emergence_democratic_states', 'Emergence and Development of Democratic States', 'History SL', 'history-sl-questions', 'none.pdf')

@track_user_journey
def authoritarian_states_sl(request):
    return render_math_topic(request, 'questionbank/history/sl/authoritarian_states_sl.html', 'authoritarian_states', 'Authoritarian States', 'History SL', 'history-sl-questions', 'none.pdf')

@track_user_journey
def causes_effects_wars_sl(request):
    return render_math_topic(request, 'questionbank/history/sl/causes_effects_wars_sl.html', 'causes_effects_wars', 'Causes and Effects of 20th Century Wars', 'History SL', 'history-sl-questions', 'none.pdf')

@track_user_journey
def cold_war_sl(request):
    return render_math_topic(request, 'questionbank/history/sl/cold_war_sl.html', 'cold_war', 'The Cold War: Superpower Tensions and Rivalries', 'History SL', 'history-sl-questions', 'none.pdf')

@track_user_journey
def rights_protest_sl(request):
    return render_math_topic(request, 'questionbank/history/sl/rights_protest_sl.html', 'rights_protest', 'Rights and Protest', 'History SL', 'history-sl-questions', 'none.pdf')

@track_user_journey
def move_global_war_sl(request):
    return render_math_topic(request, 'questionbank/history/sl/move_global_war_sl.html', 'move_global_war', 'The Move to Global War', 'History SL', 'history-sl-questions', 'none.pdf')

@track_user_journey
def conflict_intervention_sl(request):
    return render_math_topic(request, 'questionbank/history/sl/conflict_intervention_sl.html', 'conflict_intervention', 'Conflict and Intervention', 'History SL', 'history-sl-questions', 'none.pdf')

@track_user_journey
def independence_movements_sl(request):
    return render_math_topic(request, 'questionbank/history/sl/independence_movements_sl.html', 'independence_movements', 'Independence Movements', 'History SL', 'history-sl-questions', 'none.pdf')


########################################################
# HISTORY HL QUESTIONBANK
########################################################

@track_user_journey
def history_hl(request):
    return render(request, 'questionbank/history/hl/history_hl.html')


########################################################
# HISTORY QUESTION EDITOR
########################################################

def edit_history_questions(request):
    """View for editing history questions with rich text editor"""
    # Check if user is logged in (add stricter admin check later if needed)
    if not request.session.get('already_registered', False):
        return redirect('home')
    
    # Get all history questions for both SL and HL
    sl_questions = History_SL_Questionbank.objects.all().order_by('chapter', 'id')
    hl_questions = History_HL_Questionbank.objects.all().order_by('chapter', 'id')
    
    context = {
        'sl_questions': sl_questions,
        'hl_questions': hl_questions,
    }
    return render(request, 'questionbank/history/edit_history_questions.html', context)


@require_http_methods(["GET"])
def get_history_question(request, question_id):
    """API to get a single history question"""
    if not request.session.get('already_registered', False):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    level = request.GET.get('level', 'sl')
    
    try:
        if level == 'hl':
            question = History_HL_Questionbank.objects.get(id=question_id)
        else:
            question = History_SL_Questionbank.objects.get(id=question_id)
        
        return JsonResponse({
            'id': question.id,
            'title': question.title,
            'command_term': question.command_term,
            'explanation': question.explanation,
            'intro': question.intro,
            'body': question.body,
            'conclusion': question.conclusion or '',
            'paper': question.paper,
            'chapter': question.chapter,
            'difficulty': question.difficulty,
            'marks': question.marks,
            'type': question.type,
        })
    except (History_SL_Questionbank.DoesNotExist, History_HL_Questionbank.DoesNotExist):
        return JsonResponse({'error': 'Question not found'}, status=404)


@require_http_methods(["POST"])
def update_history_question(request, question_id):
    """API to update a history question"""
    if not request.session.get('already_registered', False):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        level = data.get('level', 'sl')
        
        if level == 'hl':
            question = History_HL_Questionbank.objects.get(id=question_id)
        else:
            question = History_SL_Questionbank.objects.get(id=question_id)
        
        # Update fields
        question.title = data.get('title', question.title)
        question.command_term = data.get('command_term', question.command_term)
        question.explanation = data.get('explanation', question.explanation)
        question.intro = data.get('intro', question.intro)
        question.body = data.get('body', question.body)
        question.conclusion = data.get('conclusion', question.conclusion)
        question.paper = data.get('paper', question.paper)
        question.chapter = data.get('chapter', question.chapter)
        question.difficulty = data.get('difficulty', question.difficulty)
        question.marks = data.get('marks', question.marks)
        question.type = data.get('type', question.type)
        
        question.save()
        
        return JsonResponse({'success': True, 'message': 'Question updated successfully'})
    except (History_SL_Questionbank.DoesNotExist, History_HL_Questionbank.DoesNotExist):
        return JsonResponse({'error': 'Question not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ---------------------------------------------------------------------------
# Revision Engine Views
# ---------------------------------------------------------------------------

def _get_revision_user(request):
    """Return the Users instance for the current session, or None."""
    if not request.session.get('already_registered', False):
        return None
    email = request.session.get('email', '')
    try:
        return Users.objects.get(email=email)
    except Users.DoesNotExist:
        return None


def _has_class(user):
    """Return True for all logged-in users."""
    return user is not None


@track_user_journey
def ib_paper_may2023_preview(request):
    """Rough one-by-one preview of exported IB Math AI SL Paper 1 (May 2023). For authoring / QA only."""
    if not request.session.get('already_registered', False):
        return redirect('login')
    from website.ib_paper_may2023_preview_data import PAPER_META, PAPER_QUESTIONS
    return render(request, 'revision_engine/ib_paper_preview.html', {
        'already_registered': True,
        'paper_meta': PAPER_META,
        'questions': PAPER_QUESTIONS,
        'upload_mode': False,
        'ib_paper_save_html_url': '',
    })


IB_PAPER_UPLOAD_SUBDIR = 'ib_paper_uploads'
IB_PAPER_UPLOAD_MAX_TOTAL = 80 * 1024 * 1024


def _ib_upload_safe_rel_parts(name: str):
    name = (name or '').replace('\\', '/').strip().strip('/')
    if not name:
        return None
    parts = []
    for seg in name.split('/'):
        if seg in ('', '.', '..'):
            return None
        parts.append(seg)
    return parts or None


def _ib_unpack_zip_bytes(raw: bytes, dest: Path) -> None:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            parts = _ib_upload_safe_rel_parts(info.filename)
            if not parts:
                continue
            target = dest.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, 'wb') as out:
                shutil.copyfileobj(src, out)


def _ib_save_multipart_files(files, dest: Path) -> int:
    total = 0
    for uf in files:
        parts = _ib_upload_safe_rel_parts(uf.name)
        if not parts:
            continue
        target = dest.joinpath(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'wb') as out:
            for chunk in uf.chunks():
                total += len(chunk)
                if total > IB_PAPER_UPLOAD_MAX_TOTAL:
                    raise ValueError('Upload exceeds the size limit (80 MB).')
                out.write(chunk)
    return total


@track_user_journey
def ib_paper_upload(request):
    """
    Upload a ZIP of a paper folder (or pick a local folder) and view it in the
    IB paper HTML preview. Expects a .tex file plus an images/ directory (or
    embedded paths) like Digitary exports.
    """
    if not request.session.get('already_registered', False):
        return redirect('login')

    if request.method == 'GET':
        return render(request, 'revision_engine/ib_paper_upload.html', {
            'already_registered': True,
        })

    pack_root = None
    uid = None
    try:
        uid = uuid.uuid4()
        pack_rel_str = str(Path(IB_PAPER_UPLOAD_SUBDIR) / str(uid))
        pack_root = Path(settings.MEDIA_ROOT).joinpath(*pack_rel_str.split('/'))
        pack_root.mkdir(parents=True, exist_ok=True)

        nbytes_total = 0
        zf = request.FILES.get('paper_zip')
        arts = request.FILES.getlist('artifacts')

        if zf:
            if not zf.name.lower().endswith('.zip'):
                raise ValueError('Please upload a .zip archive.')
            buf = io.BytesIO()
            nbytes_total = 0
            for chunk in zf.chunks():
                nbytes_total += len(chunk)
                if nbytes_total > IB_PAPER_UPLOAD_MAX_TOTAL:
                    raise ValueError('ZIP exceeds the size limit (80 MB).')
                buf.write(chunk)
            _ib_unpack_zip_bytes(buf.getvalue(), pack_root)

        elif arts:
            _ib_save_multipart_files(arts, pack_root)

        else:
            messages.error(
                request,
                'Attach a ZIP file or choose a folder (Chrome / Edge folder picker).',
            )
            shutil.rmtree(pack_root, ignore_errors=True)
            return redirect('ib-paper-upload')

        tex_files = sorted(
            pack_root.rglob('*.tex'),
            key=lambda p: (
                len(p.relative_to(pack_root).parts),
                len(str(p.relative_to(pack_root))),
            ),
        )
        if not tex_files:
            raise ValueError(
                'No .tex file found after upload. ZIP the folder so the '
                'structure is preserved (e.g. paper.tex + images/).',
            )

        tex_path = tex_files[0]
        tex_text = tex_path.read_text(encoding='utf-8', errors='replace')
        meta, qs = parse_tex_bundle(
            tex_text,
            pack_root_resolved=pack_root,
            upload_rel=pack_rel_str,
        )
        write_manifest(pack_root, meta, qs)

    except ValueError as e:
        messages.error(request, str(e))
        if pack_root and pack_root.is_dir():
            shutil.rmtree(pack_root, ignore_errors=True)
        return redirect('ib-paper-upload')
    except zipfile.BadZipFile:
        messages.error(request, 'The ZIP archive could not be read.')
        if pack_root and pack_root.is_dir():
            shutil.rmtree(pack_root, ignore_errors=True)
        return redirect('ib-paper-upload')
    except Exception:
        logger.exception('ib_paper_upload failed')
        messages.error(request, 'Could not process this upload.')
        if pack_root and pack_root.is_dir():
            shutil.rmtree(pack_root, ignore_errors=True)
        return redirect('ib-paper-upload')

    return redirect('ib-paper-upload-view', upload_id=str(uid))


@track_user_journey
def ib_paper_upload_view(request, upload_id):
    """Serve a previously uploaded / parsed paper from manifest.json under MEDIA."""
    if not request.session.get('already_registered', False):
        return redirect('login')
    try:
        uid = uuid.UUID(str(upload_id))
    except ValueError:
        return HttpResponseNotFound('Not found')

    pack_root = Path(settings.MEDIA_ROOT) / IB_PAPER_UPLOAD_SUBDIR / str(uid)
    mf = read_manifest(pack_root)
    if not mf:
        return HttpResponseNotFound('Not found or expired.')

    qs_out = []
    for q in mf['questions']:
        qs_out.append({
            'num': q['num'],
            'marks': q['marks'],
            'image': q.get('image'),
            'image_url': q.get('image_url'),
            'body': q['body_html'],
        })

    return render(request, 'revision_engine/ib_paper_preview.html', {
        'already_registered': True,
        'paper_meta': mf['paper_meta'],
        'questions': qs_out,
        'upload_mode': True,
        'upload_id': str(uid),
        'ib_paper_save_html_url': reverse(
            'ib-paper-upload-save-html',
            kwargs={'upload_id': str(uid)},
        ),
    })


MAX_IB_PAPER_EDIT_HTML_BYTES = 900_000


@require_POST
@track_user_journey
def ib_paper_upload_save_question_html(request, upload_id):
    """
    Persist edited question HTML body into manifest.json for an uploaded preview.
    """
    if not request.session.get('already_registered', False):
        return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=403)
    try:
        uid = uuid.UUID(str(upload_id))
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Invalid id'}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        qidx = int(payload.get('question_index'))
        body_html = payload.get('body_html')
        if body_html is None:
            raise ValueError('body_html missing')
        if not isinstance(body_html, str):
            raise ValueError('body_html invalid')
        if len(body_html.encode('utf-8')) > MAX_IB_PAPER_EDIT_HTML_BYTES:
            return JsonResponse({'ok': False, 'error': 'Too large'}, status=400)
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Bad request'}, status=400)

    pack_root = Path(settings.MEDIA_ROOT) / IB_PAPER_UPLOAD_SUBDIR / str(uid)
    mf = read_manifest(pack_root)
    if not mf:
        return JsonResponse({'ok': False, 'error': 'Not found'}, status=404)

    qs = mf.get('questions')
    if not isinstance(qs, list) or qidx < 0 or qidx >= len(qs):
        return JsonResponse({'ok': False, 'error': 'Bad index'}, status=400)

    qs[qidx]['body_html'] = body_html
    meta = mf.get('paper_meta') or {}
    write_manifest(pack_root, meta, qs)
    return JsonResponse({'ok': True})


_IB_PAPER_AI_CLEANUP_REFERENCE = r"""Example A — short stem (may use \( ... \), <br/><br/> between paragraphs):
<p>Let f be ... Show that \( \lim ... \).</p>

Example B — part label (latin):
<p class="question"><strong>(a)</strong> Find the value ...</p>

Example C — subpart label (roman):
<p class="sub-question"><strong>(iv)</strong> Hence state ...</p>

Example D — diagram inside a part:
<div class="question mb-2"><strong>(c)</strong> <img class="medium_question" src="/media/example.png" alt="figure"/></div>

Example E — rich intro:
<div class="qb-intro mb-3"><p>Diagram not to scale.</p></div>

Example F — inline vs display delimiters for this viewer (always backslash-forms, not dollar signs):
Inline (math within the SAME line as neighbouring words/symbols): <p>Then \( \lim_{n\to\infty} a_n = 5 \).</p>
Display/block (whole equation logically on its OWN line — use line breaks inside the HTML paragraph or split paragraphs):
<p>\[ \int_{0}^{1} x^2\, dx = \frac{1}{3} \]</p>
You may combine: <p>Consider \( u = \sin \theta \). Then</p>
<p>\[ \textbf{(a)} \quad u^2 + u - 6 = 0 \]</p>

Example G — shared stem / preamble is NOT a part: use plain <p> (no class="question"). Only the line that starts each part label gets question:
<p>A curve is given by \(y=f(x)\). The following results may be used.</p>
<p>\[ f''(x)+2f'(x)=0 \]</p>
<p class="question"><strong>(a)</strong> Prove that ...</p>
<p>For the rest of the question, assume \(f(0)=3\). The next part does not start here — keep this as a normal paragraph without class="question".</p>
<p class="question"><strong>(b)</strong> Find the value of ...</p>

Example H — OCR/mark-scheme bleed at END of HTML — delete this tail junk (prioritise the last ~25% of CURRENT_HTML when checking):
BAD (real question stops before junk): hence \(k\) is maximal.<br/><br/>[0pt]<br/>8.</p>
GOOD: hence \(k\) is maximal.</p>
Also strip: meaningless [N pt], [N marks], empty [], lone exam numbers like “8.” or “9.” after a run of <br>, duplicated page/exam tails, pointless extra <br> chains before closing tags — unless they obviously belong to wording.

Example I — NEVER let one part’s block swallow BRIDGING prose before the NEXT lettered part (common after <br><br>):
BAD (all stuck inside (a)’s paragraph):
<p class="question"><strong>(a)</strong> … Give your answer correct to two decimal places.<br/><br/>Instead of investing the money, Angel decides to buy … data for part (b) …</p>
<p class="question"><strong>(b)</strong> Calculate the annual depreciation …</p>

GOOD (split: (a) stops at end of its instruction; bridge is plain <p>; (b) stays its own question opener):
<p class="question"><strong>(a)</strong> … Give your answer correct to two decimal places.</p>
<p>Instead of investing the money, Angel decides to buy … constant.</p>
<p class="question"><strong>(b)</strong> Calculate the annual depreciation …</p>"""

# Narrow reference for PASS 2: class placement only (kept short so rules are not drowned out).
_IB_PAPER_AI_CLASS_ONLY_REFERENCE = r"""CORRECT EXAMPLES:
Stem / setup paragraphs have NO question class:
<p>Let \(f\) be differentiable on \(\mathbb{R}\).</p>

Part openers MUST have class="question" (possibly with Bootstrap extras like mb-2):
<p class="question"><strong>(a)</strong> Show that ...</p>
<div class="question mb-2"><strong>(c)</strong> <img class="medium_question" src="..." alt="..."/></div>

Preamble BETWEEN parts stays plain — NOT question:
<p>Assume \(f(0)=0\) for parts (c) onwards.</p>
<p class="question"><strong>(c)</strong> Find ...</p>

Roman labels use sub-question ONLY on those openers:
<p class="sub-question"><strong>(ii)</strong> Hence ...</p>

Split merged parts (letters (a)(b)…) — NEVER keep bridging setup inside the previous part’s question paragraph:
<p class="question"><strong>(a)</strong> … end of (a) instruction only.</p>
<p>Instead of / Alternatively / Now … bridging context for the following part …</p>
<p class="question"><strong>(b)</strong> …</p>

WRONG: one <p class="question"> wrapping (a) wording AND the whole “Instead…” paragraph before (b)."""


def _ib_paper_openai_chat_completion(system: str, user_content: str):
    """One OpenAI chat completion; returns assistant message content (may include markdown fences)."""
    headers = {
        'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': 'gpt-4o',
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user_content},
        ],
        'temperature': 0.08,
        'max_tokens': 8192,
    }
    resp = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers=headers,
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']


def _strip_known_trailing_rubric_markup(html: str) -> str:
    """
    Deterministic tails often missed by OCR/LLM: bracket marks / lone Q numbers before </p>.

    Typical bleed: <br/><br/>[0pt]<br/>8.</p>
    """
    if not isinstance(html, str) or not html.strip():
        return html

    bracket_tail = re.compile(
        r'(?is)'
        r'(?:<br\s*/?>\s*){2,}'
        r'\[\s*[0-9]+\s*(?:pt|marks?)?\]\s*'
        r'(?:\s*(?:<br\s*/?>)\s*)*'
        r'(?:\b(?:[1-9]|10|11|12)\.\s*)?'
        r'(?=</p>)'
    )
    lone_number_tail = re.compile(
        r'(?is)'
        r'(?:<br\s*/?>\s*){3,}'
        r'(?:\b(?:[1-9]|10|11|12)\.\s*)(?=</p>)'
    )
    empty_bracket_tail = re.compile(
        r'(?is)(?:<br\s*/?>\s*){2,}\[\s*\]\s*(?:\s*(?:<br\s*/?>)\s*)?(?=</p>)'
    )

    s = html
    prev = None
    while prev != s:
        prev = s
        s = bracket_tail.sub('', s)
        s = lone_number_tail.sub('', s)
        s = empty_bracket_tail.sub('', s)
    return s


def _strip_openai_html_fenced_block(text):
    """If the model wraps HTML in markdown fences, remove them."""
    raw = (text or '').strip()
    if not raw.startswith('```'):
        return raw
    lines = raw.split('\n')
    if lines and lines[0].strip().startswith('```'):
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]
    while lines and not lines[-1].strip():
        lines.pop()
    return '\n'.join(lines).strip()


@require_POST
@track_user_journey
def ib_paper_ai_cleanup_question_html(request):
    """
    POST JSON { "body_html": "..." }.

    Two OpenAI calls: (1) tail garbage, math delimiters, and splitting merged lettered parts
    into separate <p> blocks (pass 1 intentionally does not tune question/sub-question classes).
    (2) Class semantics for part openers vs description/bridge paragraphs; may still insert
    closing/opening <p> if bridging prose is trapped inside a prior part block. Then rubric strip.
    Requires session login and OPENAI_API_KEY.
    """
    if not request.session.get('already_registered', False):
        return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=403)
    if not getattr(settings, 'OPENAI_API_KEY', None):
        return JsonResponse(
            {'ok': False, 'error': 'AI cleanup is unavailable (missing API key).'},
            status=503,
        )

    try:
        payload = json.loads(request.body.decode('utf-8'))
        body_html = payload.get('body_html')
        if body_html is None:
            raise ValueError('body_html missing')
        if not isinstance(body_html, str):
            raise ValueError('body_html invalid')
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Bad request'}, status=400)

    if len(body_html.encode('utf-8')) > MAX_IB_PAPER_EDIT_HTML_BYTES:
        return JsonResponse({'ok': False, 'error': 'Too large'}, status=400)
    if not body_html.strip():
        return JsonResponse({'ok': False, 'error': 'Nothing to clean'}, status=400)

    system_pass1 = (
        'You revise ONE maths-question HTML fragment for Edunade (MathJax + Question Bank).\n'
        'Do NOT change real question wording beyond fixing markup / delimiters / obvious garbage.\n\n'
        '---GOOD_STRUCTURE_REFERENCE---\n'
        + _IB_PAPER_AI_CLEANUP_REFERENCE
        + '\n---END_REFERENCE---\n\n'
        'Do these in ORDER (PASS 1 only — IGNORE class=\"question\" / \"sub-question\"; a second specialised pass fixes those):\n'
        '(1) TAIL CLEANUP — spend extra attention on the LAST ~25% of CURRENT_HTML (final paragraphs/divs).\n'
        '    OCR and mark schemes almost always bleed at the END: delete leftover fragments such as meaningless\n'
        '    brackets like [0pt], [3 marks], []; runs of empty <br> before closing tags; orphaned exam/paper\n'
        '    numbering after breaks (standalone “8.”, “12.” clearly not maths); duplicate footers. Example to strip:\n'
        '    real text ending … then <br/><br/>[0pt]<br/>8.</p> → keep real text only, close </p> without junk.\n'
        '(2) MATH FORMATTING — mathematical content MUST use MathJax-style delimiters: SAME line as prose → \\( … \\); '
        'dedicated displayed / blocked equations → \\[ … \\]. Fix stray inconsistent \$ markers when obvious;\n'
        '    preserve AMS blocks when already present '
        '(e.g. \\\\begin{aligned} … \\\\end{aligned}).\n'
        '(3) SPLIT MERGED PART PARAGRAPHS — if one <p> spans <strong>(a)</strong> instructions AND later prose that clearly '
        'sets up a DIFFERENT scenario before <strong>(b)</strong> / <strong>(c)</strong> (often after blank <br/> lines; '
        'starters such as “Instead …”, “Alternatively …”, “Now suppose …”, new cost/story context), close the first <p> '
        'right after the true end of (a)’s wording, put the bridging text into a NEW plain <p> (no class=\"question\"), '
        'and keep the next labelled part in its own opener. See Example I in the reference.\n\n'
        '- Leave every existing tag class list AS-IS (do not purposely add/remove \"question\" / \"sub-question\" '
        'yet—pass 2 fixes that). New <p> tags you create for bridging text must have NO question/sub-question classes.\n'
        '- Otherwise: remove OCR noise; trim pointless empty wrappers; preserve <img>, <table>, lists.\n\n'
        'If something could be rubric litter OR real content, REMOVE only when it matches the rubbish patterns '
        '(bracket-only marks lines, orphaned small integers after breaks, pointless <br/> chains).\n\n'
        'Respond with NOTHING except cleaned raw HTML. No markdown fences, no prose before/after.'
    )
    system_pass2_class = (
        'PASS 2 — fix class=\"question\" and class=\"sub-question\", and (only if still needed) SPLIT paragraphs so '
        'bridging text between lettered parts is never inside the previous part’s question wrapper.\n'
        'Preserve all visible wording, LaTeX, and <img> URLs; do not paraphrase.\n\n'
        '---REFERENCE---\n'
        + _IB_PAPER_AI_CLASS_ONLY_REFERENCE
        + '\n---END_REFERENCE---\n\n'
        '- FIRST check Example I style issues: if ONE element with class=\"question\" still contains BOTH <strong>(n)</strong>… '
        'for that letter AND later sentences that belong to setup for the NEXT letter, insert </p><p> splits so the bridge '
        'is a plain <p> … </p>.\n'
        '- Every block that BEGINS a latin letter PART MUST have class=\"question\" on THAT opening element. '
        'Preserve utility classes (mb-2 etc.): class=\"question mb-2\" is fine.\n'
        '- Stems, bridging <p> between (a) and (b), and other descriptions MUST NOT carry class=\"question\".\n'
        '- Roman-labelled subparts: class=\"sub-question\" ONLY on <strong>(i)</strong>-style openers.\n'
        '- Aggressively strip misplaced \"question\" / \"sub-question\" classes after any split.\n\n'
        'Output raw HTML only — no markdown fences, no commentary.'
    )
    try:
        raw1 = _ib_paper_openai_chat_completion(
            system_pass1,
            f'CURRENT_HTML:\n{body_html}',
        )
    except requests.exceptions.RequestException as e:
        logger.warning('ib_paper_ai_cleanup_question_html OpenAI pass1 error: %s', e)
        return JsonResponse(
            {'ok': False, 'error': 'AI request failed — try again or edit manually.'},
            status=502,
        )
    except (KeyError, IndexError, TypeError, AttributeError):
        logger.exception('ib_paper_ai_cleanup_question_html bad OpenAI payload (pass 1)')
        return JsonResponse({'ok': False, 'error': 'Invalid AI response'}, status=502)

    cleaned_mid = _strip_openai_html_fenced_block(raw1)
    if len(cleaned_mid.encode('utf-8')) > MAX_IB_PAPER_EDIT_HTML_BYTES:
        return JsonResponse({'ok': False, 'error': 'Cleaned HTML too large'}, status=502)

    try:
        raw2 = _ib_paper_openai_chat_completion(
            system_pass2_class,
            f'CURRENT_HTML:\n{cleaned_mid}',
        )
    except requests.exceptions.RequestException as e:
        logger.warning('ib_paper_ai_cleanup_question_html OpenAI pass2 error: %s', e)
        return JsonResponse(
            {'ok': False, 'error': 'AI pass 2 (classes) failed — try again.'},
            status=502,
        )
    except (KeyError, IndexError, TypeError, AttributeError):
        logger.exception('ib_paper_ai_cleanup_question_html bad OpenAI payload (pass 2)')
        return JsonResponse({'ok': False, 'error': 'Invalid AI response (pass 2)'}, status=502)

    cleaned = _strip_openai_html_fenced_block(raw2)
    cleaned = _strip_known_trailing_rubric_markup(cleaned)
    if len(cleaned.encode('utf-8')) > MAX_IB_PAPER_EDIT_HTML_BYTES:
        return JsonResponse({'ok': False, 'error': 'Cleaned HTML too large'}, status=502)

    return JsonResponse({'ok': True, 'body_html': cleaned})


@track_user_journey
def revision_engine_home(request):
    user = _get_revision_user(request)
    has_access = _has_class(user)

    context = {
        'already_registered': request.session.get('already_registered', False),
        'user_type': request.session.get('user_type', 'free'),
        'has_access': has_access,
        'topics': [],
    }

    if has_access:
        mastery_map = {
            m.skill_id: m
            for m in StudentSkillMastery.objects.filter(user=user)
        } if user else {}

        # Bulk-fetch subquestion counts per skill (2 queries total, not N)
        sq_counts = dict(
            RevisionSubQuestion.objects
            .filter(skills__isnull=False)
            .values('skills')
            .annotate(cnt=Count('id'))
            .values_list('skills', 'cnt')
        )
        # Fallback: question-level tags for skills that have no subquestion-level tags
        qt_counts = dict(
            QuestionSkillTag.objects
            .filter(question__subquestions__isnull=False)
            .values('skill_id')
            .annotate(cnt=Count('question_id', distinct=True))
            .values_list('skill_id', 'cnt')
        )

        chapters_data = []
        for chapter in RevisionChapter.objects.prefetch_related('topics__skills').order_by('order'):
            topics_data = []
            for topic in chapter.topics.all():
                skills_data = []
                for skill in topic.skills.all():
                    mastery = mastery_map.get(skill.id)
                    score = mastery.mastery_score if mastery else 0.3
                    mcq_count = sq_counts.get(skill.id) or qt_counts.get(skill.id, 0)
                    skills_data.append({
                        'skill': skill,
                        'mastery': mastery,
                        'score': score,
                        'percent': round(score * 100),
                        'color': re_service.get_mastery_color(score),
                        'label': mastery.mastery_label if mastery else 'Not started',
                        'tagged_count': mcq_count,
                    })
                topics_data.append({'topic': topic, 'skills': skills_data})
            chapters_data.append({
                'chapter': chapter,
                'topics': topics_data,
                'skill_count': sum(len(td['skills']) for td in topics_data),
            })

        context['chapters'] = chapters_data
        # keep legacy 'topics' pointing at first chapter for any other template that uses it
        if chapters_data:
            context['topics'] = chapters_data[0]['topics']
            context['chapter'] = chapters_data[0]['chapter']

    return render(request, 'revision_engine/revision_engine.html', context)


@track_user_journey
def revision_engine_practice(request, skill_slug):
    user = _get_revision_user(request)
    if not _has_class(user):
        return render(request, 'revision_engine/revision_engine.html', {
            'already_registered': request.session.get('already_registered', False),
            'has_access': False,
            'topics': [],
        })

    try:
        skill = RevisionSkill.objects.select_related('topic__chapter').get(slug=skill_slug)
    except RevisionSkill.DoesNotExist:
        return render(request, 'revision_engine/revision_engine.html', {
            'already_registered': request.session.get('already_registered', False),
            'has_access': True,
            'error': 'Skill not found.',
            'topics': [],
        })

    # Use per-subquestion skills if available, otherwise fall back to question-level tags
    sq_ids = set(
        RevisionSubQuestion.objects.filter(skills=skill)
        .values_list('question_id', flat=True).distinct()
    )
    if sq_ids:
        tagged_ids = list(sq_ids)
    else:
        tagged_ids = list(
            QuestionSkillTag.objects.filter(skill=skill)
            .filter(question__subquestions__isnull=False)
            .values_list('question_id', flat=True).distinct()
        )

    if not tagged_ids:
        return render(request, 'revision_engine/practice.html', {
            'already_registered': request.session.get('already_registered', False),
            'skill': skill,
            'question': None,
            'no_questions': True,
        })

    # Avoid recently answered questions (last 5 stored in session)
    session_key = f're_recent_{skill_slug}'
    recent_ids = request.session.get(session_key, [])
    candidate_ids = [qid for qid in tagged_ids if qid not in recent_ids]
    if not candidate_ids:
        # All seen recently — reset and use all
        candidate_ids = tagged_ids
        request.session[session_key] = []

    import random
    question_id = random.choice(candidate_ids)
    question = Math_AI_SL_Questionbank.objects.get(id=question_id)

    # Update recency list
    recent = request.session.get(session_key, [])
    recent.append(question_id)
    request.session[session_key] = recent[-5:]

    mastery = StudentSkillMastery.objects.filter(user=user, skill=skill).first()

    # Show ALL subquestions of the question — each part updates its own skill's mastery score
    subquestions_data = []
    for sq in question.subquestions.prefetch_related('options', 'skills').order_by('order', 'id'):
        subquestions_data.append({
            'id': sq.id,
            'part_label': sq.part_label,
            'question_text': sq.question_text,
            'options': [
                {'label': o.label, 'text': o.option_text, 'is_correct': o.is_correct}
                for o in sq.options.all()
            ],
        })

    import json as _json
    context = {
        'already_registered': request.session.get('already_registered', False),
        'user_type': request.session.get('user_type', 'free'),
        'skill': skill,
        'question': question,
        'mastery': mastery,
        'mastery_percent': round((mastery.mastery_score if mastery else 0.3) * 100),
        'mastery_color': re_service.get_mastery_color(mastery.mastery_score if mastery else 0.3),
        'total_tagged': len(tagged_ids),
        'no_questions': False,
        'subquestions_json': _json.dumps(subquestions_data),
        'has_mcq': len(subquestions_data) > 0,
        'answer_json': _json.dumps(question.answer or ''),
    }
    return render(request, 'revision_engine/practice.html', context)


@track_user_journey
def revision_engine_tag_questions(request):
    """Simple internal UI for tagging Math AI SL questions to revision skills."""
    if False:
        return JsonResponse({'error': 'Staff only'}, status=403)

    chapter_filter = request.GET.get('chapter', 'seq_series')

    from django.db.models import Q as DQ, Case, When, Value, IntegerField as _IF2
    questions = Math_AI_SL_Questionbank.objects.filter(
        DQ(chapter=chapter_filter) | DQ(chapter2=chapter_filter) | DQ(chapter3=chapter_filter)
    ).distinct().annotate(
        _diff_order=Case(
            When(difficulty='Easy',   then=Value(1)),
            When(difficulty='Medium', then=Value(2)),
            When(difficulty='Hard',   then=Value(3)),
            default=Value(4),
            output_field=_IF2(),
        )
    ).order_by('_diff_order', 'id').prefetch_related('skill_tags__skill')

    # All skills grouped by topic
    all_skills = RevisionSkill.objects.select_related('topic').order_by('topic__order', 'order')

    # Build {question_id: {skill_id: weight}} map for pre-ticking checkboxes
    tags_by_question = {}
    for q in questions:
        tags_by_question[q.id] = {t.skill_id: t.weight for t in q.skill_tags.all()}

    chapters = Math_AI_SL_Questionbank.CHAPTERS

    # Build JSON-safe dict {question_id: [skill_id, ...]} for JS pre-ticking
    import json as _json
    tags_json = {qid: list(skills.keys()) for qid, skills in tags_by_question.items()}

    context = {
        'questions': questions,
        'all_skills': all_skills,
        'tags_by_question': tags_by_question,
        'tags_json': _json.dumps(tags_json),
        'chapters': chapters,
        'chapter_filter': chapter_filter,
    }
    return render(request, 'revision_engine/tag_questions.html', context)


def revision_engine_save_tags(request):
    """AJAX POST: save skill tags for a single question."""
    if False:
        return JsonResponse({'error': 'Staff only'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    import json as _json
    data = _json.loads(request.body)
    question_id = int(data['question_id'])
    # list of {skill_id, weight}
    skill_entries = data.get('skills', [])

    try:
        question = Math_AI_SL_Questionbank.objects.get(id=question_id)
    except Math_AI_SL_Questionbank.DoesNotExist:
        return JsonResponse({'error': 'Question not found'}, status=404)

    incoming_skill_ids = set()
    for entry in skill_entries:
        skill_id = int(entry['skill_id'])
        weight = float(entry.get('weight', 1.0))
        QuestionSkillTag.objects.update_or_create(
            question=question,
            skill_id=skill_id,
            defaults={'weight': weight},
        )
        incoming_skill_ids.add(skill_id)

    # Remove tags that were unchecked
    QuestionSkillTag.objects.filter(question=question).exclude(skill_id__in=incoming_skill_ids).delete()

    return JsonResponse({'success': True, 'tagged': len(incoming_skill_ids)})


def revision_engine_tag_subquestions(request):
    """Internal UI for editing per-subquestion skill tags."""
    chapter_filter = request.GET.get('chapter', 'differentiation')

    from django.db.models import Q as DQ, Case, When, Value, IntegerField as _IF
    questions = Math_AI_SL_Questionbank.objects.filter(
        DQ(chapter=chapter_filter) | DQ(chapter2=chapter_filter) | DQ(chapter3=chapter_filter)
    ).distinct().annotate(
        _diff_order=Case(
            When(difficulty='Easy',   then=Value(1)),
            When(difficulty='Medium', then=Value(2)),
            When(difficulty='Hard',   then=Value(3)),
            default=Value(4),
            output_field=_IF(),
        )
    ).order_by('_diff_order', 'id').prefetch_related('subquestions__skills', 'subquestions__options')

    all_skills = RevisionSkill.objects.select_related('topic__chapter').order_by(
        'topic__chapter__order', 'topic__order', 'order'
    )

    import json as _json
    # Build JS-safe map {subquestion_id: [skill_id, ...]}
    sq_tags = {}
    for q in questions:
        for sq in q.subquestions.all():
            sq_tags[sq.id] = [s.id for s in sq.skills.all()]

    context = {
        'already_registered': True,
        'questions': questions,
        'all_skills': all_skills,
        'sq_tags_json': _json.dumps(sq_tags),
        'chapters': Math_AI_SL_Questionbank.CHAPTERS,
        'chapter_filter': chapter_filter,
    }
    return render(request, 'revision_engine/tag_subquestions.html', context)


def revision_engine_save_subquestion_tags(request):
    """AJAX POST: save skill tags for a single subquestion."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    import json as _json
    data = _json.loads(request.body)
    sq_id     = int(data['subquestion_id'])
    skill_ids = [int(x) for x in data.get('skill_ids', [])]

    try:
        sq = RevisionSubQuestion.objects.get(id=sq_id)
    except RevisionSubQuestion.DoesNotExist:
        return JsonResponse({'error': 'Subquestion not found'}, status=404)

    sq.skills.set(skill_ids)
    return JsonResponse({'success': True, 'skill_count': len(skill_ids)})


def revision_engine_submit(request):
    """AJAX POST: record an attempt and update mastery."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    user = _get_revision_user(request)
    if not _has_class(user):
        return JsonResponse({'error': 'Access denied'}, status=403)

    try:
        import json as _json
        data = _json.loads(request.body)
        question_id = int(data['question_id'])
        skill_slug = data['skill_slug']
        is_correct = bool(data['is_correct'])
        hint_viewed = bool(data.get('hint_viewed', False))
        explanation_viewed = bool(data.get('explanation_viewed', False))
        video_viewed = bool(data.get('video_viewed', False))
        time_spent = data.get('time_spent')
        if time_spent is not None:
            time_spent = int(time_spent)
    except (KeyError, ValueError, TypeError) as e:
        return JsonResponse({'error': f'Invalid payload: {e}'}, status=400)

    try:
        skill = RevisionSkill.objects.get(slug=skill_slug)
        question = Math_AI_SL_Questionbank.objects.get(id=question_id)
    except (RevisionSkill.DoesNotExist, Math_AI_SL_Questionbank.DoesNotExist):
        return JsonResponse({'error': 'Skill or question not found'}, status=404)

    RevisionAttempt.objects.create(
        user=user,
        question=question,
        skill=skill,
        is_correct=is_correct,
        hint_viewed=hint_viewed,
        explanation_viewed=explanation_viewed,
        video_viewed=video_viewed,
        time_spent=time_spent,
    )

    mastery = re_service.update_mastery(
        user=user,
        skill=skill,
        is_correct=is_correct,
        difficulty=question.difficulty,
        hint_viewed=hint_viewed,
        explanation_viewed=explanation_viewed,
        video_viewed=video_viewed,
    )

    return JsonResponse({
        'success': True,
        'new_mastery': round(mastery.mastery_score, 4),
        'new_mastery_percent': mastery.mastery_percent,
        'mastery_label': mastery.mastery_label,
        'mastery_color': re_service.get_mastery_color(mastery.mastery_score),
        'attempts_count': mastery.attempts_count,
        'correct_count': mastery.correct_count,
    })


# ---------------------------------------------------------------------------
# Revision Engine – MCQ Editor
# ---------------------------------------------------------------------------

@track_user_journey
def revision_engine_edit_mcq(request, question_id):
    """Editor UI: add/edit sub-questions and MCQ options for a question."""
    try:
        question = Math_AI_SL_Questionbank.objects.get(id=question_id)
    except Math_AI_SL_Questionbank.DoesNotExist:
        return JsonResponse({'error': 'Question not found'}, status=404)

    subquestions = (
        question.subquestions.prefetch_related('options').order_by('order', 'id')
    )

    context = {
        'already_registered': request.session.get('already_registered', False),
        'question': question,
        'subquestions': subquestions,
    }
    return render(request, 'revision_engine/edit_mcq.html', context)


def revision_engine_mcq_review(request):
    """Chapter-level MCQ health overview — highlights questions with missing/broken MCQ data."""
    from django.db.models import Q as DQ, Case, When, Value, IntegerField as _IFR
    from django.db.models import Prefetch as _Prefetch

    chapter_filter = request.GET.get('chapter', 'differentiation')

    # Prefetch MUST order by question_id first — otherwise batches for many questions mix rows
    # that share the same numeric `order` value.
    sq_prefetch = _Prefetch(
        'subquestions',
        queryset=RevisionSubQuestion.objects.prefetch_related('options').order_by(
            'question_id', 'order', 'id'
        ),
    )

    questions = Math_AI_SL_Questionbank.objects.filter(
        DQ(chapter=chapter_filter) | DQ(chapter2=chapter_filter) | DQ(chapter3=chapter_filter)
    ).distinct().annotate(
        _diff_order=Case(
            When(difficulty='Easy',   then=Value(1)),
            When(difficulty='Medium', then=Value(2)),
            When(difficulty='Hard',   then=Value(3)),
            default=Value(4),
            output_field=_IFR(),
        )
    ).order_by('_diff_order', 'id').prefetch_related(sq_prefetch)

    reviewed = []
    for q in questions:
        sqs = list(q.subquestions.all())
        issues = []

        if not sqs:
            issues.append({'level': 'danger', 'text': 'No subquestions / MCQ not set up'})
        else:
            for sq in sqs:
                opts = list(sq.options.all())
                label = f'Part {sq.part_label.upper()}' if sq.part_label else 'Single'
                missing = 4 - len(opts)
                if missing > 0:
                    issues.append({'level': 'warning', 'text': f'{label}: only {len(opts)}/4 options'})
                correct_count = sum(1 for o in opts if o.is_correct)
                if correct_count == 0 and opts:
                    issues.append({'level': 'danger', 'text': f'{label}: no correct answer marked'})
                elif correct_count > 1:
                    issues.append({'level': 'warning', 'text': f'{label}: {correct_count} options marked correct'})

        status = 'ok' if not issues else ('danger' if any(i['level'] == 'danger' for i in issues) else 'warning')
        reviewed.append({
            'question': q,
            'subquestions': sqs,
            'issues': issues,
            'status': status,
            'sq_count': len(sqs),
        })

    ok_count      = sum(1 for r in reviewed if r['status'] == 'ok')
    warning_count = sum(1 for r in reviewed if r['status'] == 'warning')
    danger_count  = sum(1 for r in reviewed if r['status'] == 'danger')

    show_only = request.GET.get('show', 'all')  # all / issues / ok
    if show_only == 'issues':
        reviewed = [r for r in reviewed if r['status'] != 'ok']
    elif show_only == 'ok':
        reviewed = [r for r in reviewed if r['status'] == 'ok']

    return render(request, 'revision_engine/mcq_review.html', {
        'already_registered': True,
        'reviewed':       reviewed,
        'chapters':       Math_AI_SL_Questionbank.CHAPTERS,
        'chapter_filter': chapter_filter,
        'show_only':      show_only,
        'ok_count':       ok_count,
        'warning_count':  warning_count,
        'danger_count':   danger_count,
        'total':          ok_count + warning_count + danger_count,
    })


def revision_engine_save_subquestion(request):
    """AJAX POST: create or update a sub-question and its 4 options."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    import json as _json
    from django.db.models import Max
    data = _json.loads(request.body)

    question_id    = int(data['question_id'])
    subquestion_id = data.get('subquestion_id')  # None = create new
    part_label     = data.get('part_label', '').strip()
    question_text  = data.get('question_text', '').strip()
    options        = data.get('options', [])  # [{label, text, is_correct}]

    try:
        question = Math_AI_SL_Questionbank.objects.get(id=question_id)
    except Math_AI_SL_Questionbank.DoesNotExist:
        return JsonResponse({'error': 'Question not found'}, status=404)

    if subquestion_id:
        sq = RevisionSubQuestion.objects.get(id=subquestion_id, question=question)
        sq.part_label = part_label
        sq.question_text = question_text
        # Never reset order here — frontend always sends 0 on save; use ▲▼ / drag reorder only.
        sq.save()
    else:
        mx = RevisionSubQuestion.objects.filter(question=question).aggregate(mx=Max('order'))['mx']
        next_order = (mx if mx is not None else -1) + 1
        sq = RevisionSubQuestion.objects.create(
            question=question,
            part_label=part_label,
            question_text=question_text,
            order=next_order,
        )

    # Upsert each option
    for opt in options:
        RevisionMCQOption.objects.update_or_create(
            subquestion=sq,
            label=opt['label'],
            defaults={
                'option_text': opt['text'],
                'is_correct': opt.get('is_correct', False),
            }
        )

    return JsonResponse({'success': True, 'subquestion_id': sq.id})


def revision_engine_delete_subquestion(request):
    """AJAX POST: delete a sub-question (and its options via cascade)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json as _json
    data = _json.loads(request.body)
    try:
        sq = RevisionSubQuestion.objects.get(id=int(data['subquestion_id']))
        sq.delete()
        return JsonResponse({'success': True})
    except RevisionSubQuestion.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


def revision_engine_reorder_subquestions(request):
    """AJAX POST: bulk-save new order for subquestions. Body: {ordered_ids: [id, ...]}"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json as _json
    data = _json.loads(request.body)
    ordered_ids = [int(x) for x in data.get('ordered_ids', [])]
    for new_order, sq_id in enumerate(ordered_ids):
        RevisionSubQuestion.objects.filter(id=sq_id).update(order=new_order)
    return JsonResponse({'success': True})


# ---------------------------------------------------------------------------
# Revision Engine – MCQ Submit
# ---------------------------------------------------------------------------

def revision_engine_submit_mcq(request):
    """AJAX POST: record a sub-question MCQ attempt and update mastery."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    user = _get_revision_user(request)
    if user is None:
        return JsonResponse({'error': 'Not logged in'}, status=403)

    import json as _json
    data = _json.loads(request.body)

    try:
        subquestion_id     = int(data['subquestion_id'])
        selected_label     = data['selected_label']
        explanation_viewed = bool(data.get('explanation_viewed', False))
        video_viewed       = bool(data.get('video_viewed', False))
        time_spent         = data.get('time_spent')
        if time_spent is not None:
            time_spent = int(time_spent)
    except (KeyError, ValueError) as e:
        return JsonResponse({'error': f'Invalid payload: {e}'}, status=400)

    try:
        sq = RevisionSubQuestion.objects.select_related('question').prefetch_related('skills').get(id=subquestion_id)
    except RevisionSubQuestion.DoesNotExist:
        return JsonResponse({'error': 'Sub-question not found'}, status=404)

    correct_option = sq.options.filter(is_correct=True).first()
    correct_label  = correct_option.label if correct_option else None
    is_correct     = (selected_label == correct_label)

    # Determine skills to update:
    # 1. Prefer skills on the subquestion itself (per-part tags)
    # 2. Fall back to the parent question's QuestionSkillTag if subquestion has none
    sq_skills = list(sq.skills.all())
    if not sq_skills:
        sq_skills = [
            tag.skill for tag in
            QuestionSkillTag.objects.filter(question=sq.question).select_related('skill')
        ]

    # Update mastery for each skill and record attempts
    mastery_data = {}
    for skill in sq_skills:
        old_score = (
            StudentSkillMastery.objects.filter(user=user, skill=skill)
            .values_list('mastery_score', flat=True).first() or 0.3
        )
        mastery = re_service.update_mastery(
            user=user,
            skill=skill,
            is_correct=is_correct,
            difficulty=sq.question.difficulty,
            explanation_viewed=explanation_viewed,
            video_viewed=video_viewed,
            time_spent=time_spent,
        )
        delta = mastery.mastery_score - old_score
        print(
            f"[RE] {user.email} | Q{sq.question_id}({sq.part_label or '-'}) | "
            f"skill={skill.slug} | {'✓' if is_correct else '✗'} | "
            f"{old_score:.3f} → {mastery.mastery_score:.3f} ({delta:+.3f}) | "
            f"diff={sq.question.difficulty}"
            + (f" | time={time_spent}s" if time_spent else "")
            + (" | expl" if explanation_viewed else "")
            + (" | video" if video_viewed else "")
        )
        # Return mastery info for the first (primary) skill
        if not mastery_data:
            mastery_data = {
                'new_mastery_percent': mastery.mastery_percent,
                'mastery_label': mastery.mastery_label,
                'mastery_color': re_service.get_mastery_color(mastery.mastery_score),
            }
        RevisionAttempt.objects.create(
            user=user,
            question=sq.question,
            subquestion=sq,
            skill=skill,
            selected_label=selected_label,
            is_correct=is_correct,
            explanation_viewed=explanation_viewed,
            video_viewed=video_viewed,
            time_spent=time_spent,
        )

    return JsonResponse({
        'success': True,
        'is_correct': is_correct,
        'correct_label': correct_label,
        **mastery_data,
    })


# ---------------------------------------------------------------------------
# User impersonation (staff only)
# ---------------------------------------------------------------------------

IMPERSONATE_ALLOWED_EMAILS = {"prem@gmail.com", "mateusz.kostrz@edunade.com"}


def _set_user_session(request, user):
    """Populate session with a Users record the same way the login view does."""
    try:
        Premium_Members.objects.get(customer_id=user.customer_id)
        user_type = "premium"
    except Premium_Members.DoesNotExist:
        user_type = "free"

    request.session['user_name'] = user.first_name
    request.session['last_name'] = user.last_name
    request.session['school_name'] = user.school_name
    request.session['curriculum'] = user.curriculum
    request.session['occupation'] = user.occupation
    request.session['email'] = user.email
    request.session['avatar'] = user.avatar
    request.session['user_type'] = user_type
    request.session['is_apex_user'] = False
    request.session['already_registered'] = True


def impersonate_user(request, user_id):
    current_email = request.session.get('email', '')
    if current_email not in IMPERSONATE_ALLOWED_EMAILS:
        return HttpResponseForbidden("Staff only.")
    try:
        target = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return HttpResponseNotFound("User not found.")
    # Save original admin session so we can restore it
    request.session['impersonator_email'] = current_email
    _set_user_session(request, target)
    return redirect('/')


def stop_impersonating(request):
    original_email = request.session.pop('impersonator_email', None)
    if original_email:
        try:
            original_user = Users.objects.get(email=original_email)
            _set_user_session(request, original_user)
        except Users.DoesNotExist:
            pass
    return redirect('/')
