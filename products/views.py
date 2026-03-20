import json
import os
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Avg, Q
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django_daraja.mpesa.core import MpesaClient
from decimal import Decimal

# Import all models
from .models import (
    Product, Category, Cart, CartItem, Order, OrderItem,
    Wishlist, County, Town, Address, Review, OrderNotification,
    ProductImage, ProductVariant, Coupon, OrderTracking
)
from .forms import AddressForm, CustomUserCreationForm

# --- 1. UTILITIES & HELPERS ---

def get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart

def add_business_days(start_date, days):
    """Calculates delivery dates skipping weekends."""
    d = start_date
    remaining = int(days)
    while remaining > 0:
        d = d + timedelta(days=1)
        if d.weekday() < 5:  # Monday to Friday
            remaining -= 1
    return d

# --- 2. MAIN SHOP & SEARCH ---

from django.utils import timezone  # Ensure this is imported at the top

from django.shortcuts import render
from django.utils import timezone
from .models import Product, Category, PromotionStrip # Ensure PromotionStrip is imported

def index(request):
    """The master shop view handling search, categories, and Jumia-style strips."""
    products = Product.objects.all()
    categories = Category.objects.all()
    active_category = None
    now = timezone.now()

    # 1. --- FLASH SALES ---
    flash_sales = Product.objects.filter(
        flash_sale__is_active=True,
        flash_sale__start_time__lte=now,
        flash_sale__end_time__gte=now
    ).select_related('flash_sale').order_by('?')[:10]

    # 2. --- RECENTLY VIEWED (MATCHING base.html NAME) ---
    recent_ids = request.session.get('recently_viewed', [])
    global_recently_viewed = []
    if recent_ids:
        items_dict = Product.objects.in_bulk(recent_ids)
        global_recently_viewed = [items_dict[pk] for pk in recent_ids if pk in items_dict]

    # 3. --- RECOMMENDED FOR YOU ---
    recommended = []
    if recent_ids:
        viewed_cat_ids = Product.objects.filter(id__in=recent_ids).values_list('category', flat=True)
        recommended = Product.objects.filter(
            category__in=viewed_cat_ids,
            stock__gt=0
        ).exclude(id__in=recent_ids).distinct().order_by('?')[:12]
    
    if not recommended:
        recommended = Product.objects.filter(stock__gt=0).order_by('-id')[:12]

    # 4. --- NEW: DYNAMIC PROMOTION STRIPS (Jumia Style) ---
    # Fetch all active strips and prefetch products to save database hits
    promo_strips = PromotionStrip.objects.filter(is_active=True).prefetch_related('products').order_by('order')

    # 5. --- FILTERS ---
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)

    cat_id = request.GET.get('category')
    if cat_id:
        products = products.filter(category_id=cat_id)
        active_category = Category.objects.filter(id=cat_id).first()

    # Price Filters
    min_p = request.GET.get('min_price')
    max_p = request.GET.get('max_price')
    if min_p: products = products.filter(price__gte=min_p)
    if max_p: products = products.filter(price__lte=max_p)

    # Sorting
    sort = request.GET.get('sort')
    if sort == 'price_low': products = products.order_by('price')
    elif sort == 'price_high': products = products.order_by('-price')
    elif sort == 'newest': products = products.order_by('-id')

    # 6. --- CONTEXT ---
    return render(request, 'index.html', {
        'products': products,
        'categories': categories,
        'active_category': active_category,
        'flash_sales': flash_sales,
        'recommended': recommended,
        'promo_strips': promo_strips, # Pass the new strips to index.html
        'global_recently_viewed': global_recently_viewed[:6] 
    })
            
def search_suggestions(request):
    query = request.GET.get('q', '')
    suggestions = []
    if query:
        products = Product.objects.filter(name__icontains=query)[:5]
        for product in products:
            suggestions.append({'id': product.id, 'name': product.name})
    return JsonResponse(suggestions, safe=False)

# --- PRODUCT DETAIL VIEW ---
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # --- RECORD RECENTLY VIEWED ---
    recent_ids = request.session.get('recently_viewed', [])
    if product.id in recent_ids:
        recent_ids.remove(product.id)
    recent_ids.insert(0, product.id)
    request.session['recently_viewed'] = recent_ids[:10]
    request.session.modified = True 

    gallery = product.gallery.all()
    variants = product.variants.all()
    
    # --- DYNAMIC RELATED PRODUCTS ---
    related = product.related_products.all()
    if not related.exists():
        related = Product.objects.filter(category=product.category).exclude(id=product.id).order_by('?')[:5]
    else:
        related = related[:5]

    flash_sale = None
    if hasattr(product, 'flash_sale') and product.flash_sale.is_currently_active:
        flash_sale = product.flash_sale

    reviews = product.get_reviews() 
    pending_item = None
    if request.user.is_authenticated:
        pending_item = OrderItem.objects.filter(
            order__user=request.user,
            product=product,
            order__status='Delivered',
            review__isnull=True 
        ).order_by('-order__created_at').first()

    return render(request, 'product_detail.html', {
        'product': product,
        'gallery': gallery,
        'variants': variants,
        'related_products': related,
        'reviews': reviews,
        'pending_item': pending_item,
        'flash_sale': flash_sale,
    })    
    # --- 3. VERIFIED REVIEWS & PENDING TAB ---

@login_required
def pending_reviews_view(request):
    """Displays delivered items that the user hasn't reviewed yet."""
    items = OrderItem.objects.filter(
        order__user=request.user, 
        order__status='Delivered', 
        review__isnull=True 
    ).select_related('product', 'order')
    return render(request, 'pending_reviews.html', {'items': items})

@login_required
def submit_review(request, order_item_id):
    # Ensure the order item belongs to the user and is delivered
    order_item = get_object_or_404(OrderItem, id=order_item_id, order__user=request.user)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not rating:
            messages.error(request, "Please provide a rating.")
            return redirect('products:product_detail', product_id=order_item.product.id)

        # update_or_create linked to the unique order_item
        # Because the model uses OneToOneField, it is impossible to have two reviews for one purchase.
        Review.objects.update_or_create(
            order_item=order_item,
            user=request.user,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )
        
        messages.success(request, "Thank you! Your verified review has been submitted.")
        
        # After redirecting, the 'product_detail' view runs again.
        # The 'pending_item' query will now find that this order_item HAS a review,
        # so it will return None, and the form will be hidden.
        return redirect('products:product_detail', product_id=order_item.product.id)
    
    return redirect('products:product_detail', product_id=order_item.product.id)

# --- 4. CART MANAGEMENT (STANDARD & AJAX) ---

@login_required
def account_settings(request):
    return render(request, 'account.html', {'user': request.user})


def view_cart(request):
    if request.user.is_authenticated:
        cart = get_user_cart(request.user)
        items = cart.items.all()
        
        # 1. Calculate the total quantity
        total_quantity = items.aggregate(total=Sum('quantity'))['total'] or 0
        
        # 2. Get the total price from the Cart model property
        # (This uses the discounted subtotals we fixed in models.py)
        total_price = cart.total_price 
        
        context = {
            'cart': cart, 
            'cart_items': items,
            'total_quantity': total_quantity,
            'total_price': total_price,  # <--- ADDED THIS TO FIX THE BLANK SIDEBAR
        }
    else:
        # GUEST LOGIC
        session_cart = request.session.get('cart', {})
        cart_items = []
        total_quantity = 0
        total_price = Decimal('0.00')
        
        for pid, qty in session_cart.items():
            try:
                p = Product.objects.get(id=int(pid))
                current_price = p.get_current_price()
                sub = current_price * qty
                
                analysis_data = {
                    'unit_price': current_price,
                    'raw_total': sub,
                    'discount_amount': Decimal('0.00'),
                    'final_subtotal': sub,
                    'is_discounted': False,
                    'promo_name': ""
                }
                
                cart_items.append({
                    'product': p, 
                    'quantity': qty, 
                    'price_analysis': analysis_data 
                })
                total_quantity += qty
                total_price += sub
            except Product.DoesNotExist:
                continue
        
        context = {
            'cart_items': cart_items,
            'total_price': total_price,
            'total_quantity': total_quantity,
        }
    
    return render(request, 'cart.html', context)


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if product.stock <= 0:
        messages.error(request, "Out of stock.")
        return redirect(request.META.get('HTTP_REFERER', 'products:index'))

    if request.user.is_authenticated:
        cart = get_user_cart(request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            if item.quantity + 1 > product.stock:
                messages.error(request, f"Only {product.stock} left.")
            else:
                item.quantity += 1
                item.save()
    else:
        session_cart = request.session.get('cart', {})
        current_qty = session_cart.get(str(product_id), 0)
        if current_qty + 1 > product.stock:
            messages.error(request, "Stock limit reached.")
        else:
            session_cart[str(product_id)] = current_qty + 1
            request.session['cart'] = session_cart
            request.session.modified = True
    
    messages.success(request, f"{product.name} added to cart.")
    return redirect(request.META.get('HTTP_REFERER', 'products:view_cart'))

def increase_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart = get_user_cart(request.user)
        item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
        if item.quantity + 1 <= product.stock:
            item.quantity += 1
            item.save()
        else:
            messages.error(request, "Stock limit reached.")
    else:
        session_cart = request.session.get('cart', {})
        if str(product_id) in session_cart:
            if session_cart[str(product_id)] + 1 <= product.stock:
                session_cart[str(product_id)] += 1
                request.session.modified = True
    return redirect('products:view_cart')

def decrease_cart(request, product_id):
    if request.user.is_authenticated:
        cart = get_user_cart(request.user)
        item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()
    else:
        session_cart = request.session.get('cart', {})
        if str(product_id) in session_cart:
            if session_cart[str(product_id)] > 1:
                session_cart[str(product_id)] -= 1
            else:
                session_cart.pop(str(product_id))
            request.session.modified = True
    return redirect('products:view_cart')

def remove_from_cart(request, product_id):
    if request.user.is_authenticated:
        cart = get_user_cart(request.user)
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()
    else:
        session_cart = request.session.get('cart', {})
        session_cart.pop(str(product_id), None)
        request.session.modified = True
    return redirect('products:view_cart')

def cart_adjust_api(request, product_id, action):
    """AJAX endpoint for the +/- buttons in the UI."""
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart = get_user_cart(request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if action == 'inc':
            if item.quantity + 1 > product.stock:
                return JsonResponse({'error': 'Stock limit'}, status=400)
            item.quantity += 1
        else:
            item.quantity -= 1
        
        if item.quantity <= 0: 
            item.delete(); qty = 0
        else: 
            item.save(); qty = item.quantity
        
        count = sum(i.quantity for i in cart.items.all())
        return JsonResponse({'quantity': qty, 'global_cart_count': count})
    return JsonResponse({'error': 'Unauthorized'}, status=403)

# --- 5. CHECKOUT, MPESA & EMAILS ---


@login_required
def checkout(request):
    cart = get_user_cart(request.user)
    items = cart.items.all()
    
    if not items.exists(): 
        return redirect('products:index')

    # Total price of items only (before discount and shipping)
    # This matches the {{ total_price }} variable in your template
    items_total = cart.total_price  
    
    discount = Decimal('0.00')
    coupon_code = None
    delivery_fee = Decimal('0.00')
    est_days = 3
    
    addresses = Address.objects.filter(user=request.user)
    # Priority for address selection: POST > GET > Default
    selected_addr_id = request.POST.get('selected_address') or request.GET.get('addr_id')
    
    selected_address = None
    if selected_addr_id:
        selected_address = addresses.filter(id=selected_addr_id).first()
    else:
        selected_address = addresses.filter(is_default=True).first()

    # Calculate Base Delivery Fee (Standard + Bulky Surcharge)
    if selected_address:
        town = selected_address.town
        delivery_fee = town.base_delivery_fee 
        est_days = town.estimated_days
        
        # Check for bulky items and add surcharge
        bulky_items = items.filter(product__is_bulky=True)
        if bulky_items.exists():
            max_surcharge = max(item.product.bulky_surcharge for item in bulky_items)
            delivery_fee += max_surcharge

    if request.method == 'POST':
        action = request.POST.get('action')

        # 1. APPLY COUPON LOGIC
        if action == 'apply_coupon':
            code = request.POST.get('coupon', '').strip()
            cp = Coupon.objects.filter(code__iexact=code, active=True).first()
            if cp and items_total >= cp.min_total:
                discount = Decimal(cp.compute_discount(items_total))
                coupon_code = cp.code
                messages.success(request, f"Coupon {code} applied!")
            else:
                messages.warning(request, "Invalid or ineligible coupon.")

        # 2. PLACE ORDER LOGIC
        elif action == 'place_order':
            if not selected_address:
                messages.error(request, "Please select a shipping address.")
                return redirect('products:checkout')

            pay_method = request.POST.get('payment_method')
            delivery_method = request.POST.get('delivery_method', 'standard')
            
            # Add Express surcharge if selected
            if delivery_method == 'express':
                delivery_fee += Decimal('200.00')
                est_days = 1
            
            final_total = (items_total - discount) + delivery_fee
            
            # Delivery Dates
            today = timezone.localdate()
            est_start = add_business_days(today, est_days)
            est_end = add_business_days(today, est_days + 1)

            try:
                with transaction.atomic():
                    order = Order.objects.create(
                        user=request.user,
                        total_price=final_total,
                        shipping_fee=delivery_fee,
                        address=selected_address,
                        phone_number=request.POST.get('phone_number') or selected_address.phone,
                        payment_method='M-Pesa' if pay_method == 'mpesa' else 'Pay on Delivery',
                        delivery_method=delivery_method,
                        status='Pending',
                        discount_amount=discount,
                        coupon_code=coupon_code,
                        estimated_delivery_start=est_start,
                        estimated_delivery_end=est_end
                    )
                    
                    for item in items:
                        analysis = item.price_analysis
                        # Calculate unit price after individual product promos
                        actual_price_per_unit = analysis['final_subtotal'] / item.quantity
                        
                        OrderItem.objects.create(
                            order=order,
                            product=item.product,
                            quantity=item.quantity,
                            price=actual_price_per_unit
                        )
                        
                        # Update Stock
                        item.product.stock -= item.quantity
                        item.product.save()

                    # Clear cart after successful order
                    items.delete()
                    messages.success(request, f"Order #{order.id} placed successfully!")
                    return redirect('products:my_orders')

            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")

    # Final calculation for display
    final_total = (items_total - discount) + delivery_fee

    return render(request, 'checkout.html', {
        'cart_items': items,
        'total_price': items_total,     # This fixes the "Items Total 0" issue
        'addresses': addresses,
        'selected_address': selected_address,
        'delivery_fee': delivery_fee,
        'final_total': final_total,
        'est_days': est_days,
        'discount': discount,
        'coupon_code': coupon_code,
        'counties': County.objects.all(), # Required for the Add Address Modal
        'towns': Town.objects.all(),      # Required for the Add Address Modal
    })

@csrf_exempt
def mpesa_callback(request):
    try:
        data = json.loads(request.body)
        stk = data['Body']['stkCallback']
        if stk['ResultCode'] == 0:
            order = Order.objects.filter(transaction_id=stk['CheckoutRequestID']).first()
            if order:
                order.status = 'Paid'
                order.save()
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Success"})
    except:
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Fail"}, status=400)

# --- 6. ADDRESS BOOK & GEOGRAPHY ---

@login_required
def address_book(request):
    addresses = Address.objects.filter(user=request.user).select_related('town__county')
    return render(request, 'address_book.html', {'addresses': addresses})

@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            addr = form.save(commit=False); addr.user = request.user; addr.save()
            if addr.is_default: Address.objects.filter(user=request.user).exclude(id=addr.id).update(is_default=False)
            return redirect('products:address_book')
    else: form = AddressForm()
    return render(request, 'add_address.html', {'form': form})

@login_required
def edit_address(request, id):
    addr = get_object_or_404(Address, id=id, user=request.user)
    form = AddressForm(request.POST or None, instance=addr)
    if form.is_valid():
        form.save(); return redirect('products:address_book')
    return render(request, 'add_address.html', {'form': form})

@login_required
def delete_address(request, id):
    get_object_or_404(Address, id=id, user=request.user).delete()
    return redirect('products:address_book')

def get_towns(request):
    county_id = request.GET.get('county_id')
    towns = list(Town.objects.filter(county_id=county_id).values('id', 'name'))
    return JsonResponse(towns, safe=False)

# --- 7. ORDERS & TRACKING TIMELINE ---

@login_required
def my_orders(request):
    return render(request, 'my_orders.html', {'orders': Order.objects.filter(user=request.user).order_by('-created_at')})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items__product', 'tracking_steps'), id=order_id, user=request.user)
    steps = ['Pending', 'Confirmed', 'Processing', 'Shipped', 'Ready for Pickup', 'Delivered']
    history = {t.status: t.created_at for t in order.tracking_steps.all()}
    timeline = []
    for s in steps:
        is_done = s in history or s == order.status
        timeline.append({'name': s, 'is_done': is_done, 'is_current': s == order.status, 'date': history.get(s)})

    return render(request, 'order_detail.html', {'order': order, 'timeline': timeline, 'items': order.items.all()})

# --- 8. WISHLIST, INBOX & AUTH ---

@login_required
def add_to_wishlist(request, product_id):
    Wishlist.objects.get_or_create(user=request.user, product_id=product_id)
    return redirect('products:view_wishlist')

@login_required
def remove_from_wishlist(request, product_id):
    Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
    return redirect('products:view_wishlist')

@login_required
def view_wishlist(request):
    return render(request, 'wishlist.html', {'wishlist_items': Wishlist.objects.filter(user=request.user)})

@login_required
def inbox(request):
    return render(request, 'inbox.html', {'notifications': OrderNotification.objects.filter(user=request.user).order_by('-created_at')})

@login_required
def inbox_detail(request, notification_id):
    n = get_object_or_404(OrderNotification, id=notification_id, user=request.user)
    n.is_read = True
    n.save()
    return render(request, 'inbox_detail.html', {'notification': n, 'order': n.order})

def register_view(request):
    form = CustomUserCreationForm(request.POST or None)
    if form.is_valid():
        user = form.save(); auth_login(request, user); return redirect('products:index')
    return render(request, 'register.html', {'form': form})

def login_view(request):
    form = AuthenticationForm(data=request.POST or None)
    if form.is_valid():
        auth_login(request, form.get_user()); return redirect('products:index')
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    auth_logout(request); return redirect('products:index')

def vouchers(request):
    return render(request, 'vouchers.html', {'coupons': Coupon.objects.filter(active=True)})


# Add this to views.py
@login_required
def add_address_ajax(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            
            # If set as default, unset others
            if address.is_default:
                Address.objects.filter(user=request.user).exclude(id=address.id).update(is_default=False)
            
            return JsonResponse({
                'success': True,
                'address_id': address.id,
                'full_name': f"{address.first_name} {address.last_name}",
                'street': address.street,
                'town_county': f"{address.town.name}, {address.town.county.name}",
                'phone': address.phone
            })
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


def see_all_products(request):
    section_type = request.GET.get('type')
    strip_id = request.GET.get('strip_id')
    
    products = Product.objects.all()
    title = "All Products"

    if section_type == 'flash':
        now = timezone.now()
        products = Product.objects.filter(
            flash_sale__is_active=True,
            flash_sale__start_time__lte=now,
            flash_sale__end_time__gte=now
        )
        title = "Flash Sales"

    elif section_type == 'promo' and strip_id:
        strip = get_object_or_404(PromotionStrip, id=strip_id)
        products = strip.products.all()
        title = strip.title

    elif section_type == 'recommended':
        # logic: show high rated or high stock items
        products = Product.objects.filter(stock__gt=0).order_by('-id')[:40]
        title = "Recommended For You"

    return render(request, 'see_all.html', {
        'products': products,
        'title': title
    })