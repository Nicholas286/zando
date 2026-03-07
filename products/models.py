from django.db import models
from django.contrib.auth.models import User

# 1. CATEGORY GOES FIRST
class Category(models.Model):
    name = models.CharField(max_length=100)
    icon_class = models.CharField(max_length=50, default='fa-solid fa-box')

    def __str__(self):
        return self.name

# 2. PRODUCT GOES SECOND (with the category link)
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # CHANGE THIS LINE:
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    stock = models.IntegerField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

# 3. OTHER MODELS FOLLOW
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product_names = models.TextField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=50, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s wishlist: {self.product.name}"


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    is_default = models.BooleanField(default=False)
