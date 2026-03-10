from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from products.sitemaps import ProductSitemap, CategorySitemap
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('products/', include('products.urls', namespace='products')),

    # Custom login/logout paths - no need to include the default auth.urls
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('', lambda request: redirect('products:index')),
    path('sitemap.xml', sitemap, {'sitemaps': {'products': ProductSitemap, 'categories': CategorySitemap}}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
