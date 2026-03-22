from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
from django.utils import timezone
from decimal import Decimal

# --- 1. GEOGRAPHY ---
class County(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Town(models.Model):
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name='towns')
    name = models.CharField(max_length=100)
    # NEW FIELDS FOR DELIVERY
    base_delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=150.00)
    estimated_days = models.IntegerField(default=3)

    def __str__(self):
        return f"{self.name} ({self.county.name})"

# --- 2. CATEGORY & PRODUCT ---
class Category(models.Model):
    name = models.CharField(max_length=100)
    icon_class = models.CharField(max_length=50, default='fa-solid fa-box')
    def __str__(self): return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    related_products = models.ManyToManyField('self', blank=True, symmetrical=False)
    
    # NEW FIELDS FOR BULKY DELIVERY
    is_bulky = models.BooleanField(default=False)
    bulky_surcharge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self): return self.name

    def get_current_price(self):
        if hasattr(self, 'flash_sale') and self.flash_sale.is_currently_active:
            return self.flash_sale.discount_price
        return self.price

    def get_discount_percentage(self):
        if hasattr(self, 'flash_sale') and self.flash_sale.is_currently_active:
            discount = ((self.price - self.flash_sale.discount_price) / self.price) * 100
            return int(discount)
        return 0

    def get_reviews(self):
        # This is the correct way to get reviews since they are linked via OrderItem
        return Review.objects.filter(order_item__product=self)

    @property
    def average_rating(self):
        avg = self.get_reviews().aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0

    @property
    def review_count(self):
        return self.get_reviews().count()

class FlashSale(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='flash_sale')
    discount_price = models.DecimalField(max_digits=10, decimal_places=2)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)

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
    discount_percent = models.PositiveIntegerField(default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    def compute_discount(self, subtotal):
        fixed = self.discount_amount or 0
        percent = (subtotal * self.discount_percent / 100) if self.discount_percent else 0
        return max(fixed, percent)

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())
class CartItem(models.Model):
    cart = models.ForeignKey('Cart', related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def price_analysis(self):
        """
        Calculates the full price breakdown for display and checkout.
        """
        unit_price = self.product.get_current_price()
        raw_total = unit_price * self.quantity
        
        discount_amount = Decimal('0.00')
        promo_name = ""

        # Logic for Promotion Strips
        promo = self.product.promotion_strips.filter(is_active=True).first()
        if promo and self.quantity >= promo.min_quantity:
            multiplier = Decimal(promo.discount_percent) / Decimal('100')
            discount_amount = raw_total * multiplier
            promo_name = promo.title

        final_subtotal = raw_total - discount_amount

        return {
            'unit_price': unit_price,
            'raw_total': raw_total,
            'discount_amount': discount_amount,
            'final_subtotal': final_subtotal,
            'promo_name': promo_name,
            'is_discounted': discount_amount > 0
        }

    @property
    def subtotal(self):
        """Used by the Cart.total_price property. No () needed."""
        # FIX: Ensure this matches the property name 'price_analysis'
        return self.price_analysis['final_subtotal']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
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
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # NEW
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
    price = models.DecimalField(max_digits=10, decimal_places=2)
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
        
class PromotionStrip(models.Model):
    title = models.CharField(max_length=255, help_text="Internal name for the strip line")
    # NEW FIELD: Manually describe what the badge says. Leave empty to hide badge.
    badge_text = models.CharField(max_length=50, blank=True, null=True, help_text="Optional: e.g. 'Add 2 to Cart Get 10%'")
    
    bg_color = models.CharField(max_length=20, default="#9c27b0")
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField('Product', related_name='promotion_strips')
    order = models.PositiveIntegerField(default=0)
    
    # ... logic fields ...
    min_quantity = models.PositiveIntegerField(default=2)
    discount_percent = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title
    
   # models.py
class HomeBubble(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to='bubbles/')
    # This is where you will add products in the admin
    products = models.ManyToManyField(Product, blank=True, related_name='home_bubbles')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['order']