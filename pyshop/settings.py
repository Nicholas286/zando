import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Detect if we're running on Render / PythonAnywhere
IS_RENDER = 'RENDER' in os.environ
PYTHONANYWHERE_DOMAIN = os.environ.get('PYTHONANYWHERE_DOMAIN') or os.environ.get('PYTHONANYWHERE_SITE')
IS_PYTHONANYWHERE = bool(PYTHONANYWHERE_DOMAIN) or ('PYTHONANYWHERE' in os.environ)

# 1. Use Environment Variables for sensitive data
SECRET_KEY = os.environ.get('SECRET_KEY', 'a-safe-fallback-for-local-only')

# 2. DEBUG defaults to True locally, False on Render/PythonAnywhere (override via env var)
DEBUG = os.environ.get('DEBUG', 'True' if not (IS_RENDER or IS_PYTHONANYWHERE) else 'False') == 'True'

# 3. Allowed hosts
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

# TEMPLATES configuration
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

# Environment-aware Database configuration:
# - Use SQLite locally
# - Use PostgreSQL only when running on Render
if IS_RENDER:
    # Render provides DATABASE_URL for the managed PostgreSQL instance
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    # Local development uses SQLite (no sslmode issues)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# 4. Configure Static and Media properly
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

# FIXED: Set this to Nairobi to match your local time
TIME_ZONE = 'Africa/Nairobi'

USE_I18N = True

# Keep this as True so Django handles daylight savings and UTC internally
USE_TZ = True


# 5. M-Pesa Settings
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

# Email settings for order notifications
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'admin@zando.com')

# Use SMTP only when credentials are configured; otherwise print emails to console locally.
if IS_RENDER or (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Only force Secure cookies on Render/PythonAnywhere (HTTPS deployments).
# When running locally over http://, Secure cookies break CSRF validation.
SESSION_COOKIE_SECURE = IS_RENDER or IS_PYTHONANYWHERE
CSRF_COOKIE_SECURE = IS_RENDER or IS_PYTHONANYWHERE

# SMTP (Gmail) defaults; keep credentials in env vars (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD)
