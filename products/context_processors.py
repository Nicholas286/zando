from .models import Cart, OrderNotification, CartItem


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
        # Never break rendering if something goes wrong – return safe default
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
