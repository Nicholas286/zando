import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Use Environment Variables for sensitive data
SECRET_KEY = os.environ.get('SECRET_KEY', 'a-safe-fallback-for-local-only')

# 2. DEBUG should only be True if you explicitly set it to 'True'
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# 3. Only allow your production domain
ALLOWED_HOSTS = ['zando-online-shopping.onrender.com', 'localhost', '127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # Add for WhiteNoise
    'django.contrib.staticfiles',
    'products.apps.ProductsConfig',
    'django_daraja',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Add for WhiteNoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 4. Configure Static and Media properly
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 5. M-Pesa Settings (Pull from Environment Variables)
MPESA_ENVIRONMENT = os.environ.get('MPESA_ENVIRONMENT', 'sandbox')
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY')

CSRF_TRUSTED_ORIGINS = ['https://zando-online-shopping.onrender.com']


# settings.py
LOGIN_REDIRECT_URL = 'products:product_list' # Replace with your actual product list URL name
LOGOUT_REDIRECT_URL = 'products:product_list'

# In pyshop/settings.py

ROOT_URLCONF = 'pyshop.urls'