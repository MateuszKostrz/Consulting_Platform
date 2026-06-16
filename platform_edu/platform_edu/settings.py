from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv





# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-local-dev-only-set-secret-key-in-env'
    else:
        raise ImproperlyConfigured('SECRET_KEY environment variable is required when DEBUG is False.')


_default_allowed_hosts = [
    '127.0.0.1',
    'localhost',
    '3.11.241.110',
    'www.academy.edunade.com',
    'academy.edunade.com',
    'MateuszKostrz.pythonanywhere.com',
    'test.edunade.com',
    'www.test.edunade.com',
    'example.edunade.com',
    'www.example.edunade.com',
    'iboost.edunade.com',
    'www.iboost.edunade.com',
    'apextuitionaustralia.edunade.com',
    'www.apextuitionaustralia.edunade.com',
    'topibtutors.edunade.com',
    'www.topibtutors.edunade.com',
    'consulting.edunade.com',
    'www.consulting.edunade.com',
]
_extra_allowed_hosts = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS_EXTRA', '').split(',')
    if host.strip()
]
ALLOWED_HOSTS = _default_allowed_hosts + _extra_allowed_hosts

USE_HTTPS = os.environ.get('USE_HTTPS', 'False').lower() == 'true'
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend([
        'http://127.0.0.1:8000',
        'http://localhost:8000',
        'http://127.0.0.1',
        'http://localhost',
    ])



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
    'portal',
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
    'portal.middleware.LoginRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'platform_edu.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
         'DIRS': [
                os.path.join(BASE_DIR, 'templates'),
                ],
                
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'portal.context_processors.consulting_context',
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
        'NAME': 'consulting',
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

STATICFILES_DIRS = []

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
        'portal.views': {
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
# Secure cookies require HTTPS. In local DEBUG mode, allow cookies over http://localhost.
SESSION_COOKIE_SECURE = USE_HTTPS and not DEBUG
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
CSRF_COOKIE_SECURE = USE_HTTPS and not DEBUG

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_REDIRECT_URL = '/home/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL = '/login/'

