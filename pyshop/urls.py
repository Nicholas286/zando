from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('admin/', admin.site.urls),
path('products/', include('products.urls', namespace='products')),
path('accounts/', include('django.contrib.auth.urls')),
path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    # Redirect root to products
    path('', lambda request: redirect('products:index')),
]

# Serve media files only during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)