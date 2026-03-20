from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('get-towns/', views.get_towns, name='get_towns'),
    # --- Home & Shop ---
    path('', views.index, name='index'),  # This is the ONLY root path

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
    path('api/cart/<int:product_id>/<str:action>/', views.cart_adjust_api, name='cart_adjust_api'),

    # --- Wishlist ---
    path('wishlist/', views.view_wishlist, name='view_wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    # --- Checkout & M-Pesa ---
    path('checkout/', views.checkout, name='checkout'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),

    # --- User Account & Orders ---
    path('account/', views.account_settings, name='account_settings'),
    path('orders/', views.my_orders, name='my_orders'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('address-book/', views.address_book, name='address_book'),
    path('add-address/', views.add_address, name='add_address'),
    path('edit-address/<int:id>/', views.edit_address, name='edit_address'),
    path('delete-address/<int:id>/', views.delete_address, name='delete_address'),

    # --- AI & Details ---
    path('api/suggestions/', views.search_suggestions, name='search_suggestions'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/review/', views.submit_review, name='submit_review'),
    path('vouchers/', views.vouchers, name='vouchers'),
    path('inbox/', views.inbox, name='inbox'),
    path('inbox/<int:notification_id>/', views.inbox_detail, name='inbox_detail'),
    path('reviews/pending/', views.pending_reviews_view, name='pending_reviews'),
path('review/submit/<int:order_item_id>/', views.submit_review, name='submit_review'),
path('address/add-ajax/', views.add_address_ajax, name='add_address_ajax'),
path('search-suggestions/', views.search_suggestions, name='search_suggestions'),
path('see-all/', views.see_all_products, name='see_all'),
]
