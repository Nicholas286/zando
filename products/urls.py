from django.urls import path
from . import views

app_name = 'products'
urlpatterns = [
    # --- Home & Shop ---
    path('', views.index, name='index'),

    # --- Authentication ---
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # --- Cart Logic ---
    path('cart/', views.view_cart, name='view_cart'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/increase/<int:product_id>/', views.increase_cart, name='increase_cart'),
    path('cart/decrease/<int:product_id>/', views.decrease_cart, name='decrease_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    # --- Wishlist ---
    path('wishlist/', views.view_wishlist, name='view_wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    # --- Checkout & M-Pesa ---
    path('checkout/', views.checkout, name='checkout'),
    # This URL must match what Safaricom calls (via ngrok)
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),

    # --- User Account & Orders ---
    path('account/', views.account_settings, name='account_settings'),
    path('orders/', views.my_orders, name='my_orders'),
    path('address-book/', views.address_book, name='address_book'),
    # ... your other urls
    path('orders/', views.my_orders, name='my_orders'),
path('generate-desc/<int:product_id>/', views.generate_description, name='generate_desc'),
path('api/suggestions/', views.search_suggestions, name='search_suggestions'),
path('product/<int:product_id>/', views.product_detail, name='product_detail'),
# Add this inside urlpatterns
path('add-address/', views.add_address, name='add_address'),
]
