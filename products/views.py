import json # Standard library
# Third-party libraries
import google.generativeai as genai
# ... other imports ...
from django.shortcuts import render, redirect, get_object_or_404
from .models import Address
from .forms import AddressForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from django_daraja.mpesa.core import MpesaClient
import os

# Import all models from one place
from .models import (
    Product, Category, Cart, CartItem, Order,
    Wishlist, County, Town, Address
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


def generate_description(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.description and len(product.description) > 10:
        messages.info(request, "Description already exists!")
    else:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            messages.error(request, "API Key not configured.")
        else:
            try:
                # 1. Configure the SDK
                genai.configure(api_key=api_key)
                # 2. Select the model
                model = genai.GenerativeModel('gemini-1.5-flash')

                # 3. Generate content
                response = model.generate_content(
                    f"Write a catchy 2-sentence shop description for {product.name}."
                )

                if response.text:
                    product.description = response.text.strip()
                    product.save()
                    messages.success(request, "AI description generated!")
            except Exception as e:
                messages.error(request, f"AI Error: {str(e)}")

    return redirect('products:index')

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

@login_required
def add_to_cart(request, product_id):
    cart = get_user_cart(request.user)
    product = get_object_or_404(Product, id=product_id)

    # Get or create the item
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    # If it already existed, increment the quantity
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    # If it was 'created', it already has quantity=1 (your default),
    # but we should ensure it's saved to the DB
    else:
        cart_item.save()

    messages.success(request, f"{product.name} added!")
    return redirect(request.META.get('HTTP_REFERER', 'products:index')) # Redirect to view_cart so you can verify immediately

@login_required
def increase_cart(request, product_id):
    cart = get_user_cart(request.user)
    item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    item.quantity += 1
    item.save()
    return redirect('products:view_cart')

@login_required
def decrease_cart(request, product_id):
    cart = get_user_cart(request.user)
    item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()
    return redirect('products:view_cart')

@login_required
def remove_from_cart(request, product_id):
    cart = get_user_cart(request.user)
    CartItem.objects.filter(cart=cart, product_id=product_id).delete()
    return redirect('products:view_cart')


# --- AUTH VIEWS ---

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('products:index')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('products:index')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    auth_logout(request)
    return redirect('products:index')


# --- MAIN SHOP VIEWS ---

@login_required
def view_cart(request):
    # 1. Get or create the cart so it's never None
    cart, created = Cart.objects.get_or_create(user=request.user)

    # 2. Get all items
    cart_items = cart.items.all()

    # 3. Calculate total quantity from the database
    total_quantity = cart_items.aggregate(total=Sum('quantity'))['total'] or 0

    # 4. Use the model's property for price
    total_price = cart.total_price

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_quantity': total_quantity
    })


# --- CHECKOUT & MPESA CALLBACK ---
@login_required
def checkout(request):
    cart = get_user_cart(request.user)
    items = cart.items.all()
    # Import these at the top of your file
    from .models import Order, County, Town

    if not items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('products:index')

    total_price = cart.total_price
    product_names = ", ".join([item.product.name for item in items])

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        phone = request.POST.get('phone_number')

        # Capture the new location data
        county_id = request.POST.get('county')
        town_id = request.POST.get('town')
        street_address = request.POST.get('address')

        if county_id and town_id:
            try:
                county = County.objects.get(id=county_id).name
                town = Town.objects.get(id=town_id).name
                full_address = f"{street_address}, {town}, {county} County"
            except (County.DoesNotExist, Town.DoesNotExist):
                messages.error(request, "Invalid location selected.")
                return redirect('products:checkout')
        else:
            messages.error(request, "Please select both a County and a Town.")
            return redirect('products:checkout')
        # 1. Handle M-Pesa
        if payment_method == 'mpesa':
            if not phone:
                messages.error(request, "Please enter your M-Pesa phone number.")
                return redirect('products:checkout')

            # ... (keep your existing MpesaClient logic here) ...
            # Inside the success block, use full_address for the Order record
            Order.objects.create(
                user=request.user,
                product_names=product_names,
                total_price=total_price,
                phone_number=phone,
                payment_method='M-Pesa',
                status='Pending',
                # Add these if you updated your model
                # address=full_address
            )

        # 2. Handle Delivery
        elif payment_method == 'delivery':
            Order.objects.create(
                user=request.user,
                product_names=product_names,
                total_price=total_price,
                phone_number=phone,
                payment_method='Pay on Delivery',
                status='Pending'
                # address=full_address
            )
            items.delete()
            messages.success(request, "Order placed! We will collect payment upon delivery.")
            return redirect('products:my_orders')

    # Send counties to the template
    return render(request, 'checkout.html', {
        'total_price': total_price,
        'cart_items': items,
        'counties': County.objects.all()
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
    return render(request, 'product_detail.html', {'product': product, 'related_products': related})


from django.shortcuts import render, redirect
from .forms import AddressForm # You will create this form file


@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            # The 'town' is saved from the form, which implies the county
            address.save()
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
        return redirect('products:address_book')

    return render(request, 'confirm_delete.html', {'address': address})


def edit_address(request, id):
    # Fetch the specific address or return a 404 error if not found
    address = get_object_or_404(Address, id=id, user=request.user)

    if request.method == 'POST':
        # Pass the instance so the form knows it's an update, not a new entry
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect('products:address_book')
    else:
        # Populate the form with the existing address data
        form = AddressForm(instance=address)

    return render(request, 'add_address.html', {'form': form})