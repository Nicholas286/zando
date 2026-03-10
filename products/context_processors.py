from pathlib import Path
import os
from .models import Product

from .models import Cart



def cart_contents(request):
    count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            count = sum(item.quantity for item in cart.items.all())
    else:
        session_cart = request.session.get('cart', {})
        count = sum(int(qty) for qty in session_cart.values())
