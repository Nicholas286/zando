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

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)
    discount_percent = models.PositiveIntegerField(default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code

    def compute_discount(self, subtotal):
        fixed = self.discount_amount or 0
        percent = (subtotal * self.discount_percent / 100) if self.discount_percent else 0
        return max(fixed, percent)

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
    DELIVERY_METHOD_CHOICES = [
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('pickup', 'Pick-up Station'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Processing', 'Processing'),
        ('Paid', 'Paid'),
        ('Shipped', 'Shipped'),
        ('Ready for Pickup', 'Ready for Pickup'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    payment_method = models.CharField(max_length=50, default='M-Pesa')
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHOD_CHOICES, default='standard')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    estimated_delivery_start = models.DateField(null=True, blank=True)
    estimated_delivery_end = models.DateField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

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

class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review {self.rating} for {self.product.name} by {self.user.username}"


class OrderNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='order_notifications')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='notifications')
    status = models.CharField(max_length=50)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for Order {self.order_id} - {self.status}"

