import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Detect environments
IS_RENDER = 'RENDER' in os.environ
PYTHONANYWHERE_DOMAIN = os.environ.get('PYTHONANYWHERE_DOMAIN') or os.environ.get('PYTHONANYWHERE_SITE')
IS_PYTHONANYWHERE = bool(PYTHONANYWHERE_DOMAIN) or ('PYTHONANYWHERE' in os.environ)

SECRET_KEY = os.environ.get('SECRET_KEY', 'a-safe-fallback-for-local-only')

DEBUG = os.environ.get('DEBUG', 'True' if not (IS_RENDER or IS_PYTHONANYWHERE) else 'False') == 'True'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'zando-online-shopping.onrender.com', '.onrender.com', '.vercel.app', '.pythonanywhere.com']
if PYTHONANYWHERE_DOMAIN:
    ALLOWED_HOSTS.append(PYTHONANYWHERE_DOMAIN)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
    'products.apps.ProductsConfig',
    'django_daraja',
    'import_export',
    'auditlog',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# TEMPLATES (Context Processors ensure variables like global_cart_count work on ALL pages)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'products.context_processors.cart_contents',
                'products.context_processors.inbox_unread_count',
                'products.context_processors.cart_quantities',
                'products.context_processors.recently_viewed_processor',
            ],
        },
    },
]

# Database configuration
if IS_RENDER:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# --- STATIC & MEDIA ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- TIMEZONE & LOCALIZATION ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# --- SESSION & SECURITY (FIXES FOR MOBILE PHONE STABILITY) ---
# This forces Django to save the cart/session on every click
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 1209600 # 2 weeks (Cart stays even if they close browser)

# Fixes badge/cart visibility for mobile Safari/Chrome
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Security settings for deployment
SESSION_COOKIE_SECURE = IS_RENDER or IS_PYTHONANYWHERE
CSRF_COOKIE_SECURE = IS_RENDER or IS_PYTHONANYWHERE
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- M-PESA SETTINGS ---
MPESA_ENVIRONMENT = os.environ.get('MPESA_ENVIRONMENT', 'sandbox')
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY')

CSRF_TRUSTED_ORIGINS = ['https://zando-online-shopping.onrender.com', 'https://*.onrender.com', 'https://*.vercel.app', 'https://*.pythonanywhere.com']

LOGIN_REDIRECT_URL = 'products:index'
LOGOUT_REDIRECT_URL = 'products:index'
LOGIN_URL = 'products:login'

ROOT_URLCONF = 'pyshop.urls'
WSGI_APPLICATION = 'pyshop.wsgi.application'

# --- EMAIL SETTINGS ---
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'admin@zando.com')

if IS_RENDER or (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'