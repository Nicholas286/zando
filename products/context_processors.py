from django.db.models import Sum
from .models import Cart, OrderNotification, CartItem, Product

def cart_contents(request):
    """
    Returns total quantity of items in cart. 
    This is what the red badge in the Navbar reads on page refresh.
    """
    try:
        count = 0
        if hasattr(request, 'user') and request.user.is_authenticated:
            # 1. LOGGED IN: Sum directly from the CartItem table for this user
            # This is much faster and more reliable than fetching the cart object first
            result = CartItem.objects.filter(cart__user=request.user).aggregate(total=Sum('quantity'))
            count = result['total'] or 0
        else:
            # 2. GUEST: Sum from session
            session_cart = request.session.get('cart', {})
            if isinstance(session_cart, dict):
                # Ensure we handle values that might be strings or None
                count = sum(int(qty) for qty in session_cart.values() if qty)
        
        return {'global_cart_count': count}
    except Exception as e:
        # Log the error if you have logging, or print for debugging
        # print(f"Context Processor Error: {e}")
        return {'global_cart_count': 0}

def cart_quantities(request):
    """
    Map of product_id -> quantity for the [ - 1 + ] buttons.
    """
    try:
        if hasattr(request, 'user') and request.user.is_authenticated:
            items = CartItem.objects.filter(cart__user=request.user).values_list('product_id', 'quantity')
            return {'cart_quantities': {pid: qty for pid, qty in items}}
        
        # For Guest: Handle string keys from JSON session
        session_cart = request.session.get('cart', {})
        if isinstance(session_cart, dict):
            return {'cart_quantities': {int(pid): int(qty) for pid, qty in session_cart.items() if qty}}
            
        return {'cart_quantities': {}}
    except Exception:
        return {'cart_quantities': {}}

def recently_viewed_processor(request):
    try:
        recent_ids = request.session.get('recently_viewed', [])
        if not recent_ids:
            return {'global_recently_viewed': []}

        items_dict = Product.objects.in_bulk(recent_ids)
        # Limit to 10 items as requested earlier
        recently_viewed_products = [items_dict[pk] for pk in recent_ids if pk in items_dict][:10]
        
        return {'global_recently_viewed': recently_viewed_products}
    except Exception:
        return {'global_recently_viewed': []}

def inbox_unread_count(request):
    try:
        if hasattr(request, 'user') and request.user.is_authenticated:
            unread = OrderNotification.objects.filter(user=request.user, is_read=False).count()
            return {'inbox_unread_count': unread}
        return {'inbox_unread_count': 0}
    except Exception:
        return {'inbox_unread_count': 0}