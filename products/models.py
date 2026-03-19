from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
from django.utils import timezone  # Needed for Flash Sale timing

# --- 1. GEOGRAPHY ---
class County(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Town(models.Model):
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name='towns')
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

# --- 2. CATEGORY & PRODUCT ---
class Category(models.Model):
    name = models.CharField(max_length=100)
    icon_class = models.CharField(max_length=50, default='fa-solid fa-box')
    def __str__(self): return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Regular Price
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    related_products = models.ManyToManyField('self', blank=True, symmetrical=False)

    def __str__(self): return self.name

    # --- FLASH SALE LOGIC ---
    def get_current_price(self):
        """Returns flash price if active, else returns regular price."""
        if hasattr(self, 'flash_sale') and self.flash_sale.is_currently_active:
            return self.flash_sale.discount_price
        return self.price

    def get_discount_percentage(self):
        """Calculates percentage saved."""
        if hasattr(self, 'flash_sale') and self.flash_sale.is_currently_active:
            discount = ((self.price - self.flash_sale.discount_price) / self.price) * 100
            return int(discount)
        return 0

    # --- RATINGS ---
    def get_reviews(self):
        return Review.objects.filter(order_item__product=self)

    @property
    def average_rating(self):
        avg = self.get_reviews().aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0

    @property
    def review_count(self):
        return self.get_reviews().count()

class FlashSale(models.Model):
    # OneToOne ensures a product can only have ONE flash sale record
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='flash_sale')
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="The price during the flash sale")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Flash Sale: {self.product.name}"

    @property
    def is_currently_active(self):
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='gallery', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=255, blank=True, null=True)

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    size = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(default=0)

# --- 3. SHOPPING TOOLS ---
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)
    discount_percent = models.PositiveIntegerField(default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    def __str__(self): return self.code

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    @property
    def subtotal(self):
        # UPDATED: Uses the current dynamic price (Flash or Regular)
        return self.product.get_current_price() * self.quantity

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

# --- 4. ADDRESS & ORDERS ---
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50, default='')
    last_name = models.CharField(max_length=50, default='')
    street = models.CharField(max_length=255)
    town = models.ForeignKey(Town, on_delete=models.CASCADE)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=15)
    is_default = models.BooleanField(default=False)
    class Meta:
        verbose_name_plural = "Addresses"
    def __str__(self): return f"{self.first_name} - {self.town.name}"

class Order(models.Model):
    DELIVERY_METHOD_CHOICES = [('standard', 'Standard'), ('express', 'Express'), ('pickup', 'Pick-up Station')]
    STATUS_CHOICES = [
        ('Pending', 'Pending'), ('Confirmed', 'Confirmed'), ('Processing', 'Processing'),
        ('Paid', 'Paid'), ('Shipped', 'Shipped'), ('Ready for Pickup', 'Ready for Pickup'),
        ('Delivered', 'Delivered'), ('Cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    payment_method = models.CharField(max_length=50, default='M-Pesa')
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHOD_CHOICES, default='standard')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_delivery_start = models.DateField(null=True, blank=True)
    estimated_delivery_end = models.DateField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self): return f"Order {self.id} - {self.status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at time of purchase
    @property
    def subtotal(self): return self.quantity * self.price

# --- 5. REVIEWS ---
class Review(models.Model):
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='review')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

# --- 6. NOTIFICATIONS & TRACKING ---
class OrderNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='order_notifications')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='notifications')
    status = models.CharField(max_length=50)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']

class OrderTracking(models.Model):
    order = models.ForeignKey(Order, related_name='tracking_steps', on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['created_at']