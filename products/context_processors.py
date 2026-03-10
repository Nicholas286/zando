from .models import Cart


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
