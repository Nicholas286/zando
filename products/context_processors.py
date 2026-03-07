from pathlib import Path
import os
from .models import Product

def cart_contents(request):
    """Provides cart data globally to all templates."""
    cart = request.session.get('cart', {})
    item_count = sum(cart.values()) if isinstance(cart, dict) else 0
    return {
        'global_cart_count': item_count
    }

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-uqu%i=%%36d@&v6hp1r(2!1vcxljou(yl4f-n-2n!5-dm5rze3'
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.ngrok-free.dev', '.ngrok-free.app', '*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'products.apps.ProductsConfig',
    'django_daraja',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pyshop.urls'

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
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# --- MPESA SETTINGS ---
MPESA_ENVIRONMENT = 'sandbox'
MPESA_CONSUMER_KEY = 'your_key'
MPESA_CONSUMER_SECRET = 'your_secret'
MPESA_SHORTCODE = '174379'
MPESA_PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'

# Fixed the SyntaxError by properly closing the list
CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.dev',
    'https://*.ngrok-free.app'
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'