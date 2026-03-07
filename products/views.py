import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_daraja.mpesa.core import MpesaClient
from .models import Product, Order, Wishlist
from google import genai
from google.genai import types
from django.shortcuts import redirect
from django.contrib import messages
from .models import Product
from .models import Product, Category  # Add Category here!
from django.http import JsonResponse
import os
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

    # 1. Initialize the client using the environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        messages.error(request, "API Key not configured.")
        return redirect('index')

    client = genai.Client(api_key=api_key)

    try:
        # 2. Generate content using the client
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"Write a catchy 2-sentence shop description for a product named {product.name}."
        )

        # 3. Save the result
        if response.text:
            product.description = response.text
            product.save()
            messages.success(request, f"AI generated a description for {product.name}!")
        else:
            messages.warning(request, "AI returned an empty response.")

    except Exception as e:
        messages.error(request, f"AI Error: {str(e)}")
        print(f"DEBUG ERROR: {e}")

    return redirect('index')


@login_required
def account_settings(request):
    """Renders the user profile settings page."""
    return render(request, 'account.html', {'user': request.user})


@login_required
def address_book(request):
    """Handles saved shipping addresses."""
    return render(request, 'address_book.html')


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
    return redirect('index')


@login_required
def remove_from_wishlist(request, product_id):
    Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
    messages.success(request, "Item removed from wishlist.")
    return redirect('view_wishlist')


# --- CART MANAGEMENT VIEWS ---

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get('cart', {})
    p_id = str(product_id)
    cart[p_id] = cart.get(p_id, 0) + 1
    request.session['cart'] = cart
    messages.success(request, f"{product.name} added to cart.")
    return redirect('index')


def increase_cart(request, product_id):
    cart = request.session.get('cart', {})
    p_id = str(product_id)
    if p_id in cart:
        cart[p_id] += 1
    request.session['cart'] = cart
    return redirect('view_cart')


def decrease_cart(request, product_id):
    cart = request.session.get('cart', {})
    p_id = str(product_id)
    if p_id in cart:
        if cart[p_id] > 1:
            cart[p_id] -= 1
        else:
            del cart[p_id]
    request.session['cart'] = cart
    return redirect('view_cart')


def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    p_id = str(product_id)
    if p_id in cart:
        del cart[p_id]
    request.session['cart'] = cart
    return redirect('view_cart')


# --- AUTH VIEWS ---

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    auth_logout(request)
    return redirect('index')


# --- MAIN SHOP VIEWS ---


def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0
    for p_id, qty in cart.items():
        try:
            product = Product.objects.get(id=int(p_id))
            cart_items.append({'product': product, 'quantity': qty})
            total_price += product.price * qty
        except (Product.DoesNotExist, ValueError):
            continue
    return render(request, 'cart.html', {'cart_items': cart_items, 'total_price': total_price})


# --- CHECKOUT & MPESA CALLBACK ---

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('index')

    # Verify products and calculate total
    total_price = 0
    product_names_list = []
    for p_id, qty in cart.items():
        try:
            product = Product.objects.get(id=int(p_id))
            total_price += product.price * qty
            product_names_list.append(product.name)
        except (Product.DoesNotExist, ValueError):
            continue

    if request.method == 'POST':
        phone = request.POST.get('phone_number')
        cl = MpesaClient()
        callback_url = 'https://kash-shamanistic-tearlessly.ngrok-free.dev/products/mpesa/callback/'

        try:
            response = cl.stk_push(phone, int(total_price), "ZandoStore", "Payment", callback_url)

            if response.response_code == "0":
                Order.objects.create(
                    user=request.user,
                    product_names=", ".join(product_names_list),
                    total_price=total_price,
                    phone_number=phone,
                    transaction_id=response.checkout_request_id,
                    status='Pending'
                )
                request.session['cart'] = {}
                messages.success(request, "M-Pesa prompt sent! Enter your PIN.")
                return redirect('my_orders')
            else:
                messages.error(request, f"M-Pesa Error: {response.response_description}")
        except Exception as err:
            messages.error(request, f"System Error: {str(err)}")

    return render(request, 'checkout.html', {'total_price': total_price})


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
    # Get up to 4 other products in the same category
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]

    return render(request, 'product_detail.html', {
        'product': product,
        'related_products': related_products
    })


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # Fetching related items so 'related_products' isn't empty in the template
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]

    return render(request, 'product_detail.html', {
        'product': product,
        'related_products': related_products
    })


from django.shortcuts import render, redirect
from .forms import AddressForm # You will create this form file

def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('address_book') # Redirect back to your address book
    else:
        form = AddressForm()
    return render(request, 'add_address.html', {'form': form})