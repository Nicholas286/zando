from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Sum
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from import_export.admin import ImportExportModelAdmin
from auditlog.models import LogEntry
from auditlog.admin import LogEntryAdmin

from .models import (
    Product, Category, Order, OrderItem, Wishlist,
    County, Town, Address, Cart, CartItem, Coupon, Review,
    OrderNotification, OrderTracking, ProductImage, ProductVariant, FlashSale
)

# ----------------------------------------------------------------      
# 1. CUSTOM ADMIN SITE (DASHBOARD)
# ----------------------------------------------------------------
class CustomAdminSite(admin.AdminSite):
    site_header = "ZANDO LOGISTICS PORTAL"
    site_title = "Zando Admin"
    index_title = "Business Intelligence Dashboard"

    def each_context(self, request):
        context = super().each_context(request)
        revenue_statuses = ['Confirmed', 'Processing', 'Paid', 'Shipped', 'Ready for Pickup', 'Delivered']
        all_orders = Order.objects.all()
        revenue_val = all_orders.filter(status__in=revenue_statuses).aggregate(total=Sum('total_price'))['total'] or 0
        
        context.update({
            'total_orders': all_orders.count(),
            'total_revenue': f"{int(revenue_val):,}", 
            'pending_orders': all_orders.filter(status__in=['Pending', 'Processing']).count(),
            'recent_orders': all_orders.order_by('-created_at')[:8],
        })
        return context

admin.site = CustomAdminSite()

# ----------------------------------------------------------------      
# 2. INLINES
# ----------------------------------------------------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

class FlashSaleInline(admin.StackedInline):
    model = FlashSale
    can_delete = False
    verbose_name_plural = 'Active Flash Sale'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('product_image', 'product', 'quantity', 'price', 'subtotal_display')
    readonly_fields = ('product_image', 'subtotal_display', 'price', 'product')
    can_delete = False
    extra = 0

    def product_image(self, obj):
        if obj and obj.product and obj.product.image:
            return format_html('<img src="{}" width="40" height="40" style="border-radius:4px; object-fit:cover;"/>', obj.product.image.url)
        return "No Image"

    def subtotal_display(self, obj):
        if obj and obj.quantity and obj.price:
            # FIX: Format number to string first
            amount = f"{int(obj.quantity * obj.price):,}"
            return format_html("<span style='color:#000; font-weight:bold;'>Ksh {}</span>", amount)
        return "Ksh 0"

# ----------------------------------------------------------------      
# 3. PRODUCT & FLASH SALE ADMIN
# ----------------------------------------------------------------
class ProductAdmin(ImportExportModelAdmin):
    list_display = ('name', 'category', 'current_price_display', 'colored_stock', 'is_flash_sale')
    list_filter = ('category',)
    search_fields = ('name',)
    inlines = [ProductImageInline, ProductVariantInline, FlashSaleInline]

    def current_price_display(self, obj):
        # FIX: Format numbers to strings with commas first
        reg_price = f"{int(obj.price):,}"
        
        if hasattr(obj, 'flash_sale') and obj.flash_sale.is_currently_active:
            flash_price = f"{int(obj.flash_sale.discount_price):,}"
            return format_html(
                '<span style="color: red; font-weight: bold;">Ksh {}</span> '
                '<small style="text-decoration: line-through; color: #999;">Ksh {}</small>', 
                flash_price, reg_price
            )
        return f"Ksh {reg_price}"
    current_price_display.short_description = "Price"

    def colored_stock(self, obj):
        if obj.stock < 10: color = "#d9534f" # Red
        elif obj.stock < 30: color = "#f68b1e" # Orange
        else: color = "#5cb85c" # Green
        return format_html('<b style="color:{}">{} in stock</b>', color, obj.stock)

    def is_flash_sale(self, obj):
        if hasattr(obj, 'flash_sale') and obj.flash_sale.is_currently_active:
            # ✅ Use mark_safe when you have a static string with no {} placeholders
            return mark_safe('<span style="color: #d9534f;">⚡ ACTIVE</span>')
        return "No"

class FlashSaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'discount_price_display', 'start_time', 'end_time', 'is_active_status')
    list_filter = ('is_active',)

    def discount_price_display(self, obj):
        return f"Ksh {int(obj.discount_price):,}"
    
    def is_active_status(self, obj):
        return obj.is_currently_active
    is_active_status.boolean = True

# ----------------------------------------------------------------      
# 4. ORDER ADMIN
# ----------------------------------------------------------------
class OrderAdmin(ImportExportModelAdmin):
    list_display = ('id', 'user', 'colored_status', 'total_price_formatted', 'created_at', 'order_actions')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('id', 'user__username', 'phone_number')
    inlines = [OrderItemInline]
    actions = ['bulk_confirm', 'bulk_processing', 'bulk_shipped', 'bulk_ready', 'bulk_delivered']

    fieldsets = (
        ('ORDER TRACKING', {'fields': ('status_timeline', 'status', ('payment_method', 'transaction_id'))}),
        ('CUSTOMER DETAILS', {'fields': (('user', 'phone_number'), 'customer_email')}),
        ('SHIPPING LOCATION', {'fields': ('delivery_method', 'full_address_card')}),
        ('BILLING SUMMARY', {'fields': (('total_price', 'discount_amount'), 'coupon_code')}),
    )

    readonly_fields = ('status_timeline', 'customer_email', 'full_address_card', 'user')

    def create_status_records(self, order, new_status):
        msg_map = {
            'Confirmed': 'Order confirmed. We are getting it ready.',
            'Processing': 'Items are being packed at our warehouse.',
            'Shipped': 'Package dispatched! On the way to you.',
            'Ready for Pickup': 'Package is ready at your pickup station.',
            'Delivered': 'Successfully delivered. Enjoy your purchase!',
            'Cancelled': 'Order has been cancelled.',
        }
        msg = msg_map.get(new_status, f"Order status updated to {new_status}")
        OrderTracking.objects.create(order=order, status=new_status, message=msg)
        OrderNotification.objects.create(user=order.user, order=order, status=new_status, message=msg)

    def save_model(self, request, obj, form, change):
        if change:
            old_status = Order.objects.get(pk=obj.pk).status
            if old_status != obj.status:
                self.create_status_records(obj, obj.status)
        super().save_model(request, obj, form, change)

    # Bulk actions
    def bulk_confirm(self, request, queryset):
        for order in queryset: self.create_status_records(order, 'Confirmed')
        queryset.update(status='Confirmed')
    bulk_confirm.short_description = "⭐ Mark as Confirmed"

    def bulk_delivered(self, request, queryset):
        for order in queryset: self.create_status_records(order, 'Delivered')
        queryset.update(status='Delivered')
    bulk_delivered.short_description = "✅ Mark as Delivered"

    # UI UI UI
    def status_timeline(self, obj):
        steps = ['Pending', 'Confirmed', 'Processing', 'Shipped', 'Ready for Pickup', 'Delivered']
        current_status = obj.status if obj.status in steps else 'Pending'
        try: current_index = steps.index(current_status)
        except ValueError: current_index = 0
        html = '<div style="display: flex; align-items: center; width: 100%; max-width: 800px; padding: 30px 10px; background: #fff; border-radius: 8px; border: 1px solid #ccc; overflow-x: auto;">'
        for i, step in enumerate(steps):
            color = "#28a745" if i <= current_index else "#ddd"
            text_color = "#333" if i <= current_index else "#999"
            html += f'''<div style="flex: 1; text-align: center; position: relative; min-width: 85px;">
                        <div style="width: 16px; height: 16px; background: {color}; border-radius: 50%; margin: 0 auto; border: 2px solid #fff; box-shadow: 0 0 0 1px {color};"></div>
                        <div style="font-size: 8px; color: {text_color}; margin-top: 8px; font-weight: bold; white-space: nowrap; text-transform: uppercase;">{step}</div>
                    </div>'''
            if i < len(steps) - 1:
                line_color = "#28a745" if i < current_index else "#ddd"
                html += f'<div style="flex: 1; height: 3px; background: {line_color}; margin-top: -22px; min-width: 15px;"></div>'
        html += '</div>'
        return mark_safe(html)

    def full_address_card(self, obj):
        if obj.address:
            a = obj.address
            return format_html('<div style="background: #ffffff; padding: 15px; border: 1px solid #ccc; border-left: 6px solid #ffa500; border-radius: 4px; color: #000; line-height: 1.8;">'
                               '<strong>Recipient:</strong> {} {}<br><strong>Street:</strong> {}<br><strong>Location:</strong> {}, {}<br><strong>Phone:</strong> {}</div>',
                               a.first_name, a.last_name, a.street, a.town.name, a.town.county.name, a.phone)
        return "No shipping address."

    def customer_email(self, obj): return obj.user.email
    def colored_status(self, obj):
        colors = {'Pending': '#6c757d', 'Confirmed': '#007bff', 'Processing': '#17a2b8', 'Ready for Pickup': '#ffa500', 'Delivered': '#198754', 'Cancelled': '#dc3545', 'Shipped': '#6f42c1'}
        return format_html('<span style="background:{}; color:white; padding:4px 12px; border-radius:20px; font-size:10px; font-weight:bold;">{}</span>', colors.get(obj.status, '#333'), obj.status)
    
    def total_price_formatted(self, obj): 
        # FIX: Ensure it returns a string
        return f"Ksh {int(obj.total_price):,}"
    
    def order_actions(self, obj):
        url = reverse('admin:products_order_change', args=[obj.pk])
        return format_html('<a class="button" style="background:#ffa500; color:white; border:none; padding: 4px 12px; font-weight: bold;" href="{}">MANAGE</a>', url)

# ----------------------------------------------------------------      
# 5. REGISTRATION
# ----------------------------------------------------------------
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'user', 'rating', 'created_at')
    readonly_fields = ('order_item', 'user', 'product_name')
    
    def product_name(self, obj):
        return obj.order_item.product.name

admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(FlashSale, FlashSaleAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Category); admin.site.register(Address); admin.site.register(Town)
admin.site.register(County); admin.site.register(Wishlist); admin.site.register(Cart)
admin.site.register(Coupon); admin.site.register(OrderTracking)