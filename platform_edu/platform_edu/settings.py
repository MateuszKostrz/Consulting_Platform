from pathlib import Path
import os
from django.utils import timezone
from dotenv import load_dotenv





# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-srfe9!+4tinmt_)q$%eoq&jpp(c3w860l7lai*x3no&-65+3s-'

# SECURITY WARNING: don't run with debug turned on in production!

# Default to True for local development, False in production
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'



ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '3.11.241.110', 'www.academy.edunade.com', 'academy.edunade.com', 'MateuszKostrz.pythonanywhere.com' ,'test.edunade.com','www.test.edunade.com', 'example.edunade.com', 'www.example.edunade.com', 'iboost.edunade.com', 'www.iboost.edunade.com', 'apextuitionaustralia.edunade.com', 'www.apextuitionaustralia.edunade.com', 'topibtutors.edunade.com', 'www.topibtutors.edunade.com']



STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY_LIVE')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY_LIVE')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Google reCAPTCHA Settings
RECAPTCHA_SITE_KEY = os.getenv('RECAPTCHA_SITE_KEY', '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI')  # Default is test key
RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY', '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe')  # Default is test key
RECAPTCHA_VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'
RECAPTCHA_ENABLED = os.getenv('RECAPTCHA_ENABLED', 'True').lower() == 'true'  # Set to False to disable

# Meta Pixel (tutoring landing page) — set META_PIXEL_ID in .env when ready
META_PIXEL_ID = os.getenv('META_PIXEL_ID', 'YOUR_PIXEL_ID')


# STRIPE_SECRET_KEY = "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"
# STRIPE_PUBLISHABLE_KEY = "pk_live_51O2D0KHskuYAkbd6QqaN3tm3wwavrhPFBOS4tgxaLA9hKrxthGfuZKJJyhdc17RXAWT46S7XmoEI0iTMHixZ81hX00aev8uSHp"
# STRIPE_SECRET_KEY = "sk_test_51O2D0KHskuYAkbd6YIsWRR4IR0dLwUmvr3oC1N8B8NmROamAYy0ozMPcCcxky3r6vBkWAMRzl1hbEs64oXKtkNVU00Ef7UqGpr"
# STRIPE_PUBLISHABLE_KEY = "pk_test_51O2D0KHskuYAkbd6JDNnMFpbP01lq69bvuLhRruFPlTVg2GIpmLQX1ZIprQZJt6KHp51TVtb01MM1QkjGrjd8rgB00sifJCnQz"
# STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY_TEST')
# STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY_TEST')





# Application definition

SITE_ID = 2


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.messages',
    'ckeditor',
    'ckeditor_uploader',
    # 'platform_edu.apps.PaymentsConfig'
    # 'django.contrib.staticfiles',
    'website',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

]


SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'website.domain_theme_middleware.DomainThemeMiddleware',
    'website.middleware.UpdatePremiumStatusMiddleware',
]

ROOT_URLCONF = 'platform_edu.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
         'DIRS': [os.path.join(BASE_DIR, 'templates'),
                  os.path.join(BASE_DIR, 'website', 'templates', 'past_papers', 'math'),
                  os.path.join(BASE_DIR, 'website', 'templates', 'past_papers', 'econ'),
                  os.path.join(BASE_DIR, 'website', 'templates', 'past_papers', 'bio'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers', 'chem'),
                os.path.join(BASE_DIR, 'website', 'templates', 'exam_notes', 'bio'),
                os.path.join(BASE_DIR, 'website', 'templates', 'exam_notes', 'chem'),
                os.path.join(BASE_DIR, 'website', 'templates', 'exam_notes', 'econ'),
                os.path.join(BASE_DIR, 'website', 'templates', 'exam_notes', 'phys'),
                os.path.join(BASE_DIR, 'website', 'templates', 'exam_notes', 'math'),
                os.path.join(BASE_DIR, 'website', 'templates', 'exam_notes', 'hist'),
                os.path.join(BASE_DIR, 'website', 'templates', 'exam_notes', 'bus'),
                os.path.join(BASE_DIR, 'website', 'templates', 'uni_reports', 'personal_statements'),
                os.path.join(BASE_DIR, 'website', 'templates', 'uni_reports', 'cover_letters'),
                os.path.join(BASE_DIR, 'website', 'templates', 'uni_reports', 'reports'),
                os.path.join(BASE_DIR, 'website', 'templates', 'uni_reports', 'reference_letters'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'math'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'math', 'ai_sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'math', 'aa_sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'math', 'ai_hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'math', 'aa_hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'history'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'biology'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'physics'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'computer_science'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'computer_science', 'sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'computer_science', 'hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'physics', 'sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'physics', 'hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'chemistry', 'sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'chemistry', 'hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'biology', 'sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'questionbank', 'biology', 'hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'webinars'),
                os.path.join(BASE_DIR, 'website', 'templates', 'popups'),
                os.path.join(BASE_DIR, 'website', 'templates', 'old_stuffs'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_videos', 'math_ai_sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_videos', 'math_aa_sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_videos', 'math_aa_hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_videos', 'math_ai_hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_videos', 'physics_sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_videos', 'physics_hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_videos', 'chem_sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_videos', 'chem_hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_videos', 'comp_sci_sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_topics', 'math_ai_sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_topics', 'math_ai_hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_topics', 'math_aa_sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_topics', 'math_aa_hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_topics', 'physics_sl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'past_papers_topics', 'physics_hl'),
                os.path.join(BASE_DIR, 'website', 'templates', 'subscription_stats'),

                ],
                
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'website.context_processors.current_url_name',
            ],
        },
    },
]

WSGI_APPLICATION = 'platform_edu.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'demo_1',
        'USER': 'mateuszkostrz',
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': '5432',
        'CONN_MAX_AGE': 60,  # reuse DB connections for 60s instead of reconnecting every request
    },
    
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Warsaw'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    ]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'email-smtp.us-east-1.amazonaws.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_ADDRESS')
QUESTION_REPORT_RECIPIENTS = [
    email.strip()
    for email in os.getenv('QUESTION_REPORT_RECIPIENTS', 'contact@edunade.com').split(',')
    if email.strip()
]





# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
            'formatter': 'simple',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'website.views': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 300,
        'width': '100%',
    },
}

# Session Configuration for Persistent Login
SESSION_COOKIE_AGE = 30 * 24 * 60 * 60  # 30 days in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Don't expire when browser closes
SESSION_SAVE_EVERY_REQUEST = True  # Update session on every request
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_REDIRECT_URL = '/home/'
LOGOUT_REDIRECT_URL = '/'

# Allauth settings
ACCOUNT_EMAIL_VERIFICATION = 'none'  # Skip email verification for Google users
SOCIALACCOUNT_AUTO_SIGNUP = True     # Automatically create account on first Google login
ACCOUNT_EMAIL_REQUIRED = True        # Email is required
ACCOUNT_UNIQUE_EMAIL = True          # Email must be unique
SOCIALACCOUNT_LOGIN_ON_GET = True    # Skip the intermediate confirmation page
ACCOUNT_LOGOUT_ON_GET = True         # Allow logout via GET request
SOCIALACCOUNT_QUERY_EMAIL = True     # Query email from social provider
SOCIALACCOUNT_STORE_TOKENS = False   # Don't store OAuth tokens (simpler flow)
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True  # Automatically connect accounts with same email
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True  # Auto-connect without asking
ACCOUNT_USERNAME_REQUIRED = False    # Don't require a separate username
SOCIALACCOUNT_ADAPTER = 'website.adapters.SocialAccountAdapter'  # Use email as username

