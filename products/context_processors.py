from .models import Cart, OrderNotification, CartItem, Product


def cart_contents(request):
    try:
        count = 0
        if getattr(request, "user", None) and request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                count = sum(item.quantity for item in cart.items.all())
        else:
            session_cart = request.session.get('cart', {}) or {}
            count = sum(int(qty) for qty in session_cart.values())
        return {'global_cart_count': count}
    except Exception:
        return {'global_cart_count': 0}


def inbox_unread_count(request):
    try:
        if getattr(request, "user", None) and request.user.is_authenticated:
            unread = OrderNotification.objects.filter(user=request.user, is_read=False).count()
            return {'inbox_unread_count': unread}
        return {'inbox_unread_count': 0}
    except Exception:
        return {'inbox_unread_count': 0}


def cart_quantities(request):
    """
    Map of product_id -> quantity currently in cart.
    Used to render +/- steppers on listing/detail pages.
    """
    try:
        if getattr(request, "user", None) and request.user.is_authenticated:
            items = CartItem.objects.filter(cart__user=request.user).values_list('product_id', 'quantity')
            return {'cart_quantities': {pid: qty for pid, qty in items}}
        session_cart = request.session.get('cart', {}) or {}
        return {'cart_quantities': {int(pid): int(qty) for pid, qty in session_cart.items()}}
    except Exception:
        return {'cart_quantities': {}}


def recently_viewed_processor(request):
    """
    Fetches the actual product objects for the IDs stored in the session.
    Returns 'global_recently_viewed' to all templates.
    """
    try:
        recent_ids = request.session.get('recently_viewed', [])
        recently_viewed_products = []
        
        if recent_ids:
            # Fetch products from DB. in_bulk preserves the ID as keys.
            items_dict = Product.objects.in_bulk(recent_ids)
            
            # Reconstruct the list in the correct order (most recently viewed first)
            # and handle cases where a product might have been deleted from the DB.
            recently_viewed_products = [items_dict[pk] for pk in recent_ids if pk in items_dict]
            
        return {'global_recently_viewed': recently_viewed_products[:6]}
    except Exception:
        return {'global_recently_viewed': []}