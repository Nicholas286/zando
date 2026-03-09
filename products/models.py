from django.db import models
from django.contrib.auth.models import User

class County(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Town(models.Model):
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name='towns')
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name


# 1. CATEGORY
class Category(models.Model):
    name = models.CharField(max_length=100)
    icon_class = models.CharField(max_length=50, default='fa-solid fa-box')

    def __str__(self):
        return self.name

# 2. PRODUCT
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock = models.IntegerField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

# 3. CART
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

# 4. CART ITEM
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        return self.product.price * self.quantity


# 5. WISHLIST
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s wishlist: {self.product.name}"

# 6. ADDRESS
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # ADD THESE TWO LINES:
    first_name = models.CharField(max_length=50, default='')
    last_name = models.CharField(max_length=50, default='')

    street = models.CharField(max_length=255)
    town = models.ForeignKey(Town, on_delete=models.CASCADE)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=15)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.street}, {self.town.name}"

    # THIS IS THE ONLY ALLOWED META ATTRIBUTE FOR THIS MODEL
    class Meta:
        verbose_name_plural = "Addresses"

# 7. ORDER
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    payment_method = models.CharField(max_length=50, default='M-Pesa')
    status = models.CharField(max_length=50, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

# 8. ORDER ITEM
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # price at time of purchase

    @property
    def subtotal(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.id}"


