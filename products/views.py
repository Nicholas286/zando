import json # Standard library
# ... other imports ...
from django.shortcuts import render, redirect, get_object_or_404
from .models import Address
from .forms import AddressForm, CustomUserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from django_daraja.mpesa.core import MpesaClient
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
import os
from django.utils import timezone
from datetime import timedelta
from django.db import transaction

# Import all models from one place
from .models import (
    Product, Category, Cart, CartItem, Order,
    Wishlist, County, Town, Address, Review, OrderNotification
)
# In products/views.py

def get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def search_suggestions(request):
    query = request.GET.get('q', '')
    suggestions = []
    if query:
        # Get the top 5 matching product names
        products = Product.objects.filter(name__icontains=query)[:5]
        for product in products:
            suggestions.append({
                'id': product.id,
                'name': product.name
            })
    return JsonResponse(suggestions, safe=False)


@login_required
def account_settings(request):
    """Renders the user profile settings page."""
    return render(request, 'account.html', {'user': request.user})


@login_required
# In views.py
def address_book(request):
    # 'select_related' joins the user and town/county tables for faster loading
    addresses = Address.objects.filter(user=request.user).select_related('user', 'town__county')
    return render(request, 'address_book.html', {'addresses': addresses})

@login_required
def my_orders(request):
    """Displays the user's past and pending orders."""
    orders = Order.objects.filter(user=request.user).order_by('-id')
    return render(request, 'my_orders.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    """Displays detailed information for a specific order."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})


# --- WISHLIST VIEWS ---

@login_required
def view_wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})


@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, f"{product.name} added to wishlist.")
    return redirect('products:index')


@login_required
def remove_from_wishlist(request, product_id):
    Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
    messages.success(request, "Item removed from wishlist.")
    return redirect('products:view_wishlist')


# --- CART MANAGEMENT VIEWS ---

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if product.stock <= 0:
        messages.error(request, f"Sorry, {product.name} is out of stock.")
        return redirect(request.META.get('HTTP_REFERER', 'products:index'))
    if request.user.is_authenticated:
        cart = get_user_cart(request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            if cart_item.quantity + 1 > product.stock:
                messages.error(request, f"Only {product.stock} unit(s) left for {product.name}.")
                return redirect(request.META.get('HTTP_REFERER', 'products:view_cart'))
            cart_item.quantity += 1
            cart_item.save()
        else:
            # created with default quantity=1; ensure stock allows it
            if cart_item.quantity > product.stock:
                cart_item.delete()
                messages.error(request, f"Only {product.stock} unit(s) left for {product.name}.")
                return redirect(request.META.get('HTTP_REFERER', 'products:index'))
    else:
        session_cart = request.session.get('cart', {})
        key = str(product_id)
        current_qty = int(session_cart.get(key, 0) or 0)
        if current_qty + 1 > product.stock:
            messages.error(request, f"Only {product.stock} unit(s) left for {product.name}.")
            return redirect(request.META.get('HTTP_REFERER', 'products:view_cart'))
        session_cart[key] = current_qty + 1
        request.session['cart'] = session_cart
        request.session.modified = True
    messages.success(request, f"{product.name} added!")
    return redirect(request.META.get('HTTP_REFERER', 'products:view_cart'))

def increase_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart = get_user_cart(request.user)
        item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
        if item.quantity + 1 > product.stock:
            messages.error(request, f"Only {product.stock} unit(s) left for {product.name}.")
            return redirect('products:view_cart')
        item.quantity += 1
        item.save()
    else:
        session_cart = request.session.get('cart', {})
        key = str(product_id)
        if key in session_cart:
            current_qty = int(session_cart.get(key, 0) or 0)
            if current_qty + 1 > product.stock:
                messages.error(request, f"Only {product.stock} unit(s) left for {product.name}.")
                return redirect('products:view_cart')
            session_cart[key] = current_qty + 1
            request.session['cart'] = session_cart
            request.session.modified = True
    return redirect('products:view_cart')


def cart_adjust_api(request, product_id, action):
    """
    Adjust cart quantity for a product via JSON (inc/dec).
    Used by +/- steppers on listing/detail pages.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    product = get_object_or_404(Product, id=product_id)
    if action not in {'inc', 'dec'}:
        return JsonResponse({'error': 'Invalid action'}, status=400)

    if request.user.is_authenticated:
        cart = get_user_cart(request.user)
        cart_item = CartItem.objects.filter(cart=cart, product=product).first()

        current_qty = cart_item.quantity if cart_item else 0

        if action == 'inc':
            if product.stock <= 0:
                return JsonResponse({'error': 'Out of stock', 'quantity': current_qty, 'stock': product.stock}, status=400)
            if current_qty + 1 > product.stock:
                return JsonResponse({'error': 'Stock limit', 'quantity': current_qty, 'stock': product.stock}, status=400)
            if cart_item:
                cart_item.quantity += 1
                cart_item.save(update_fields=['quantity'])
            else:
                cart_item = CartItem.objects.create(cart=cart, product=product, quantity=1)

        else:  # dec
            if not cart_item:
                current_qty = 0
            elif cart_item.quantity <= 1:
                cart_item.delete()
                current_qty = 0
            else:
                cart_item.quantity -= 1
                cart_item.save(update_fields=['quantity'])
                current_qty = cart_item.quantity

        # compute global count
        global_count = sum(i.quantity for i in cart.items.all())
        return JsonResponse({'quantity': current_qty, 'global_cart_count': global_count, 'stock': product.stock})

    # Session cart for anonymous users
    session_cart = request.session.get('cart', {}) or {}
    key = str(product_id)
    current_qty = int(session_cart.get(key, 0) or 0)

    if action == 'inc':
        if product.stock <= 0:
            return JsonResponse({'error': 'Out of stock', 'quantity': current_qty, 'stock': product.stock}, status=400)
        if current_qty + 1 > product.stock:
            return JsonResponse({'error': 'Stock limit', 'quantity': current_qty, 'stock': product.stock}, status=400)
        session_cart[key] = current_qty + 1
        current_qty = session_cart[key]
    else:
        if current_qty <= 1:
            session_cart.pop(key, None)
            current_qty = 0
        else:
            session_cart[key] = current_qty - 1
            current_qty = session_cart[key]

    request.session['cart'] = session_cart
    request.session.modified = True
    global_count = sum(int(qty) for qty in session_cart.values())
    return JsonResponse({'quantity': current_qty, 'global_cart_count': global_count, 'stock': product.stock})

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
        key = str(product_id)
        if key in session_cart:
            if session_cart[key] > 1:
                session_cart[key] -= 1
            else:
                session_cart.pop(key)
            request.session['cart'] = session_cart
            request.session.modified = True
    return redirect('products:view_cart')

def remove_from_cart(request, product_id):
    if request.user.is_authenticated:
        cart = get_user_cart(request.user)
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()
    else:
        session_cart = request.session.get('cart', {})
        key = str(product_id)
        if key in session_cart:
            session_cart.pop(key)
            request.session['cart'] = session_cart
            request.session.modified = True
    return redirect('products:view_cart')


# --- AUTH VIEWS ---

def register_view(request):
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect(next_url or 'products:index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form, 'next': next_url})


def login_view(request):
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect(next_url or 'products:index')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form, 'next': next_url})


def logout_view(request):
    auth_logout(request)
    return redirect('products:index')


# --- MAIN SHOP VIEWS ---

def view_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        total_quantity = cart_items.aggregate(total=Sum('quantity'))['total'] or 0
        total_price = cart.total_price
        wishlist_items = Wishlist.objects.filter(user=request.user)[:5]
    else:
        session_cart = request.session.get('cart', {})
        cart_items = []
        total_quantity = 0
        total_price = 0
        for pid_str, qty in session_cart.items():
            try:
                product = Product.objects.get(id=int(pid_str))
                subtotal = product.price * qty
                cart_items.append({'product': product, 'quantity': qty, 'subtotal': subtotal})
                total_quantity += qty
                total_price += subtotal
            except Product.DoesNotExist:
                continue
        wishlist_items = []
    recently_viewed = Product.objects.all()[:5]
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'wishlist_items': wishlist_items,
        'recently_viewed': recently_viewed
    })


# --- CHECKOUT & MPESA CALLBACK ---
@login_required
def checkout(request):
    # Merge any session-based cart into the user's DB cart on checkout
    session_cart = request.session.get('cart')
    if session_cart:
        db_cart = get_user_cart(request.user)
        for pid_str, qty in session_cart.items():
            try:
                product = Product.objects.get(id=int(pid_str))
                item, created = CartItem.objects.get_or_create(cart=db_cart, product=product)
                if not created:
                    item.quantity += int(qty)
                else:
                    item.quantity = int(qty)
                item.save()
            except Product.DoesNotExist:
                continue
        request.session.pop('cart')
        request.session.modified = True
    cart = get_user_cart(request.user)
    items = cart.items.all()
    # Import these at the top of your file
    from .models import Order, County, Town, Address, OrderItem, Coupon

    if not items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('products:index')

    total_price = cart.total_price
    coupon_code = None
    discount = 0

    action = (request.POST.get('action') or '').strip() if request.method == 'POST' else ''

    # Handle coupon application without placing an order
    if request.method == 'POST' and action == 'apply_coupon':
        submitted_coupon = (request.POST.get('coupon') or '').strip()
        if submitted_coupon:
            coupon_obj = Coupon.objects.filter(code__iexact=submitted_coupon, active=True).first()
            if coupon_obj:
                now = timezone.now()
                if (not coupon_obj.starts_at or coupon_obj.starts_at <= now) and (not coupon_obj.ends_at or coupon_obj.ends_at >= now) and total_price >= coupon_obj.min_total:
                    discount = coupon_obj.compute_discount(total_price)
                    coupon_code = coupon_obj.code
                    messages.success(request, f"Coupon {coupon_code} applied.")
                else:
                    messages.warning(request, "This coupon is not valid for your order.")
            else:
                messages.warning(request, "Invalid coupon code.")
        else:
            messages.warning(request, "Enter a coupon code to apply.")
    
    # Get all user addresses for selection
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    def add_business_days(start_date, days):
        d = start_date
        remaining = int(days)
        while remaining > 0:
            d = d + timedelta(days=1)
            if d.weekday() < 5:  # Mon-Fri
                remaining -= 1
        return d

    if request.method == 'POST' and action == 'place_order':
        payment_method = request.POST.get('payment_method')
        phone = request.POST.get('phone_number')
        selected_address_id = request.POST.get('selected_address')
        delivery_method = request.POST.get('delivery_method', 'standard') or 'standard'

        # Get the selected address
        try:
            selected_address = Address.objects.get(id=selected_address_id, user=request.user)
        except Address.DoesNotExist:
            messages.error(request, "Invalid address selected.")
            return redirect('products:checkout')

        # Calculate delivery fee
        delivery_fee = 500 if delivery_method == 'express' else 0
        final_total = total_price - discount + delivery_fee

        # Get phone number - prefer M-Pesa phone if entered, otherwise use address phone
        if payment_method == 'mpesa':
            if not phone:
                messages.error(request, "Please enter your M-Pesa phone number.")
                return redirect('products:checkout')
            order_phone = phone
        else:
            order_phone = selected_address.phone

        # Estimate delivery dates (business days)
        today = timezone.localdate()
        if delivery_method == 'express':
            est_start = add_business_days(today, 1)
            est_end = est_start
        else:
            # standard / pickup defaults
            est_start = add_business_days(today, 2)
            est_end = add_business_days(today, 3)

        try:
            with transaction.atomic():
                # Create the order
                order = Order.objects.create(
                user=request.user,
                total_price=final_total,
                phone_number=order_phone,
                payment_method='M-Pesa' if payment_method == 'mpesa' else 'Pay on Delivery',
                status='Pending',
                delivery_method=delivery_method,
                estimated_delivery_start=est_start,
                estimated_delivery_end=est_end,
                address=selected_address,
                coupon_code=coupon_code,
                discount_amount=discount
                )

                # Create OrderItems + decrement stock (locks rows to prevent oversell)
                for item in items.select_related('product'):
                    product = Product.objects.select_for_update().get(pk=item.product_id)
                    if product.stock < item.quantity:
                        messages.error(request, f"Not enough stock for {product.name}. Only {product.stock} left.")
                        raise ValueError("Insufficient stock")

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item.quantity,
                        price=product.price  # capture price at purchase time
                    )
                    product.stock -= int(item.quantity)
                    product.save(update_fields=['stock'])
        except ValueError:
            return redirect('products:checkout')

        # Send order confirmation email (HTML + plain text). Do not block checkout if email fails.
        try:
            if request.user.email:
                subject = f'Order Confirmation - Zando #{order.id}'
                message = (
                    f'Hi {request.user.username}, thank you for shopping with Zando! '
                    f'Your order #{order.id} has been received.'
                )
                recipient_list = [request.user.email]
                html_message = render_to_string('emails/order_confirm.html', {
                    'username': request.user.username,
                    'order': order,
                    'items': order.items.select_related('product').all(),
                })
                send_mail(
                    subject,
                    message,
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'from@zando.com'),
                    recipient_list,
                    html_message=html_message,
                )
            else:
                messages.warning(request, "Order placed, but no email is saved on your account to send a confirmation.")
        except Exception:
            # Avoid breaking checkout flow; email errors should not block order placement.
            messages.warning(request, "Order placed, but we couldn't send the confirmation email. Check email settings.")

        # 1. Handle M-Pesa
        if payment_method == 'mpesa':
            mpesa_client = MpesaClient()
            account_reference = f"Order-{order.id}"
            transaction_desc = f"Payment for Order {order.id}"
            callback_url = request.build_absolute_uri('/products/mpesa-callback/')
            response = mpesa_client.stk_push(
                phone_number=order_phone,
                amount=int(final_total),
                account_reference=account_reference,
                transaction_desc=transaction_desc,
                callback_url=callback_url
            )
            if response.get('ResponseCode') == '0':
                order.transaction_id = response.get('CheckoutRequestID')
                order.save()
                messages.success(request, "M-Pesa payment initiated. Please complete the payment on your phone.")
            else:
                # Delete the order if STK push failed (stock was already decremented)
                # Restore stock before deleting.
                for oi in order.items.select_related('product').all():
                    p = oi.product
                    p.stock += int(oi.quantity)
                    p.save(update_fields=['stock'])
                order.delete()
                messages.error(request, "Failed to initiate M-Pesa payment. Please try again.")
                return redirect('products:checkout')

        # 2. Handle Pay on Delivery
        elif payment_method == 'delivery':
            items.delete()
            messages.success(request, f"Order placed successfully! Total: KSh {final_total} (including delivery). We will collect payment upon delivery.")
            return redirect('products:my_orders')

    # Send counties and default address to the template
    return render(request, 'checkout.html', {
        'total_price': total_price,
        'cart_items': items,
        'addresses': addresses,
        'default_address': default_address,
        'delivery_fee': 0,
        'final_total': total_price,
        'coupon_code': coupon_code,
        'discount': discount
    })


@csrf_exempt
def mpesa_callback(request):
    """Safaricom background response handler."""
    try:
        stk_data = json.loads(request.body)
        callback_content = stk_data['Body']['stkCallback']
        result_code = callback_content['ResultCode']
        checkout_id = callback_content['CheckoutRequestID']

        order = Order.objects.filter(transaction_id=checkout_id).first()

        if order:
            if result_code == 0:
                metadata = callback_content.get('CallbackMetadata', {}).get('Item', [])
                receipt = next((i['Value'] for i in metadata if i['Name'] == 'MpesaReceiptNumber'), None)
                order.status = 'Paid'
                if receipt:
                    order.transaction_id = receipt
                order.save()
                # Clear cart items after successful payment
                from .models import CartItem
                CartItem.objects.filter(cart__user=order.user).delete()
            else:
                order.status = f"Failed: {callback_content.get('ResultDesc', 'Cancelled')}"
                order.save()

        return JsonResponse({"ResultCode": 0, "ResultDesc": "Success"})

    except (KeyError, json.JSONDecodeError, TypeError) as err:
        return JsonResponse({"ResultCode": 1, "ResultDesc": f"Invalid Data: {str(err)}"}, status=400)

def index(request):
    """The master shop view handling search, categories, and price filtering."""
    products = Product.objects.all()
    categories = Category.objects.all()
    active_category = None

    # 1. Search Logic (The 'q' MUST match the name attribute in your HTML)
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)

    # 2. Category Filter
    cat_id = request.GET.get('category')
    if cat_id:
        products = products.filter(category_id=cat_id)
        active_category = Category.objects.filter(id=cat_id).first()

    # 3. Price Filters
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # 4. Sorting
    sort = request.GET.get('sort')
    if sort == 'price_low':
        products = products.order_by('price')
    elif sort == 'price_high':
        products = products.order_by('-price')
    elif sort == 'newest':
        products = products.order_by('-id')

    context = {
        'products': products,
        'categories': categories,
        'active_category': active_category
    }
    return render(request, 'index.html', context)


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    related = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    reviews = Review.objects.filter(product=product).order_by('-created_at')[:10]
    return render(request, 'product_detail.html', {'product': product, 'related_products': related, 'reviews': reviews})

@login_required
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', 0))
        except (TypeError, ValueError):
            rating = 0
        comment = (request.POST.get('comment') or '').strip()
        if 1 <= rating <= 5:
            Review.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={'rating': rating, 'comment': comment}
            )
            messages.success(request, "Thank you for your review.")
        else:
            messages.error(request, "Please select a rating between 1 and 5.")
    return redirect('products:product_detail', product_id=product.id)

def vouchers(request):
    from .models import Coupon
    now = timezone.now()
    coupons = Coupon.objects.filter(active=True).all()
    visible = []
    for c in coupons:
        if (not c.starts_at or c.starts_at <= now) and (not c.ends_at or c.ends_at >= now):
            visible.append(c)
    return render(request, 'vouchers.html', {'coupons': visible})

@login_required
def inbox(request):
    notifications = OrderNotification.objects.filter(user=request.user).select_related('order')[:50]
    return render(request, 'inbox.html', {'notifications': notifications})


@login_required
def inbox_detail(request, notification_id):
    n = get_object_or_404(
        OrderNotification.objects.select_related('order').prefetch_related('order__items__product'),
        id=notification_id,
        user=request.user,
    )
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=['is_read'])

    order = n.order
    return render(request, 'inbox_detail.html', {
        'notification': n,
        'order': order,
        'items': order.items.select_related('product').all(),
    })


from django.shortcuts import render, redirect
from .forms import AddressForm # You will create this form file


def get_towns(request):
    county_id = request.GET.get('county_id')
    if county_id:
        towns = Town.objects.filter(county_id=county_id).values('id', 'name')
        return JsonResponse(list(towns), safe=False)
    return JsonResponse([], safe=False)


@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        print(f"DEBUG: Form data: {request.POST}")
        print(f"DEBUG: Form is valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"DEBUG: Form errors: {form.errors}")
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            
            # Ensure only one default address per user
            if address.is_default:
                Address.objects.filter(user=request.user).exclude(id=address.id).update(is_default=False)
            
            messages.success(request, "Address added successfully.")
            print(f"DEBUG: Address saved: {address}")
            return redirect('products:address_book')
    else:
        form = AddressForm()

    return render(request, 'add_address.html', {'form': form})
# views.py
def get_towns(request):
    county_id = request.GET.get('county_id')
    # Use .values() to ensure we get a clean dictionary structure
    towns = Town.objects.filter(county_id=county_id).values('id', 'name')
    towns_list = list(towns)

    print(f"DEBUG: Found {len(towns_list)} towns for County {county_id}: {towns_list}")
    return JsonResponse(towns_list, safe=False)


def delete_address(request, id):
    # Ensure this query is correct
    address = get_object_or_404(Address, id=id, user=request.user)

    if request.method == 'POST':
        address.delete()
        messages.success(request, "Address deleted.")
        return redirect('products:address_book')

    return render(request, 'confirm_delete.html', {'address': address})


def edit_address(request, id):
    # Fetch the specific address or return a 404 error if not found
    address = get_object_or_404(Address, id=id, user=request.user)

    if request.method == 'POST':
        # Pass the instance so the form knows it's an update, not a new entry
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            updated_address = form.save()
            
            # Ensure only one default address per user
            if updated_address.is_default:
                Address.objects.filter(user=request.user).exclude(id=updated_address.id).update(is_default=False)
            
            messages.success(request, "Address updated.")
            return redirect('products:address_book')
    else:
        # Populate the form with the existing address data
        form = AddressForm(instance=address)

    return render(request, 'add_address.html', {'form': form})
