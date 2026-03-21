import datetime
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Sum
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from import_export.admin import ImportExportModelAdmin
from auditlog.models import LogEntry
from auditlog.admin import LogEntryAdmin
from decimal import Decimal 

from .models import (
    Product, Category, Order, OrderItem, Wishlist,
    County, Town, Address, Cart, CartItem, Coupon, Review,
    OrderNotification, OrderTracking, ProductImage, ProductVariant, 
    FlashSale, PromotionStrip 
)

# ----------------------------------------------------------------      
# 1. CUSTOM ADMIN SITE
# ----------------------------------------------------------------
class CustomAdminSite(admin.AdminSite):
    site_header = mark_safe('<span style="color: #fff; font-weight: 800;">ZANDO LOGISTICS PORTAL</span>')
    site_title = "Zando Admin"
    index_title = "Business Intelligence"

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
            return format_html('<img src="{}" width="40" height="40" style="border-radius:4px; object-fit:cover; border: 1px solid #eee;"/>', obj.product.image.url)
        return "No Image"

    def subtotal_display(self, obj):
        if obj and obj.quantity and obj.price:
            amount = f"{int(obj.quantity * obj.price):,}"
            return format_html("<span style='color:#000; font-weight:bold;'>Ksh {}</span>", amount)
        return "Ksh 0"

# ----------------------------------------------------------------      
# 3. PRODUCT ADMIN
# ----------------------------------------------------------------
class ProductAdmin(ImportExportModelAdmin):
    list_display = ('name', 'category', 'current_price_display', 'colored_stock', 'is_flash_sale_badge')
    list_filter = ('category',)
    search_fields = ('name',)
    inlines = [ProductImageInline, ProductVariantInline, FlashSaleInline]
    actions = ['bulk_flash_10', 'bulk_flash_25', 'bulk_flash_50']

    def current_price_display(self, obj):
        reg_price = f"{int(obj.price):,}"
        if hasattr(obj, 'flash_sale') and obj.flash_sale.is_currently_active:
            flash_price = f"{int(obj.flash_sale.discount_price):,}"
            return format_html(
                '<span style="color: #e61601; font-weight: bold;">Ksh {}</span> '
                '<small style="text-decoration: line-through; color: #999; margin-left:5px;">Ksh {}</small>', 
                flash_price, reg_price
            )
        return f"Ksh {reg_price}"
    current_price_display.short_description = "Price"

    def colored_stock(self, obj):
        if obj.stock < 10: color = "#d9534f"
        elif obj.stock < 30: color = "#f68b1e"
        else: color = "#28a745"
        return format_html('<b style="color:{}">{} in stock</b>', color, obj.stock)

    def is_flash_sale_badge(self, obj):
        if hasattr(obj, 'flash_sale') and obj.flash_sale.is_currently_active:
            return mark_safe('<span style="background: #e61601; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">⚡ ACTIVE</span>')
        return "No"
    is_flash_sale_badge.short_description = "Flash Sale"

    def apply_bulk_flash(self, request, queryset, percentage):
        now = timezone.now()
        end = now + datetime.timedelta(days=2) 
        for product in queryset:
            discount_factor = Decimal(percentage) / Decimal(100)
            FlashSale.objects.update_or_create(
                product=product,
                defaults={
                    'discount_price': product.price - (product.price * discount_factor),
                    'start_time': now, 'end_time': end, 'is_active': True
                }
            )
        self.message_user(request, f"Applied {percentage}% Flash Sale to {queryset.count()} products.")

    # FIX: Used %% to escape the percentage sign and prevent the crash
    @admin.action(description="⚡ Apply 10%% Flash Sale")
    def bulk_flash_10(self, request, queryset): self.apply_bulk_flash(request, queryset, 10)

    @admin.action(description="⚡ Apply 25%% Flash Sale")
    def bulk_flash_25(self, request, queryset): self.apply_bulk_flash(request, queryset, 25)

    @admin.action(description="⚡ Apply 50%% Flash Sale")
    def bulk_flash_50(self, request, queryset): self.apply_bulk_flash(request, queryset, 50)

# ----------------------------------------------------------------      
# 4. ORDER ADMIN
# ----------------------------------------------------------------
class OrderAdmin(ImportExportModelAdmin):
    list_display = ('id', 'user', 'colored_status', 'total_price_formatted', 'created_at', 'order_actions')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('id', 'user__username', 'phone_number')
    inlines = [OrderItemInline]
    actions = ['bulk_confirm', 'bulk_processing', 'bulk_shipped', 'bulk_ready', 'bulk_delivered']
    readonly_fields = ('status_timeline', 'customer_email', 'full_address_card', 'user')

    def customer_email(self, obj):
        return obj.user.email if obj.user else "No User Attached"
    customer_email.short_description = "Customer Email"

    @admin.display(description="Status Timeline")
    def status_timeline(self, obj):
        steps = ['Pending', 'Confirmed', 'Processing', 'Shipped', 'Ready for Pickup', 'Delivered']
        current_status = obj.status if obj.status in steps else 'Pending'
        try: current_index = steps.index(current_status)
        except ValueError: current_index = 0
        
        html = '<div style="display: flex; align-items: center; width: 100%; max-width: 100%; padding: 15px 5px; background: #fff; border-radius: 4px; border: 1px solid #eee; overflow-x: auto; -webkit-overflow-scrolling: touch;">'
        for i, step in enumerate(steps):
            color = "#006bff" if i <= current_index else "#ddd"
            text_color = "#333" if i <= current_index else "#aaa"
            html += f'''<div style="flex: 0 0 80px; text-align: center; position: relative;">
                        <div style="width: 12px; height: 12px; background: {color}; border-radius: 50%; margin: 0 auto; border: 2px solid #fff; box-shadow: 0 0 0 1px {color};"></div>
                        <div style="font-size: 8px; color: {text_color}; margin-top: 6px; font-weight: bold; text-transform: uppercase;">{step}</div>
                    </div>'''
            if i < len(steps) - 1:
                line_color = "#006bff" if i < current_index else "#ddd"
                html += f'<div style="flex: 1; min-width: 10px; height: 2px; background: {line_color}; margin-top: -18px;"></div>'
        html += '</div>'
        return mark_safe(html)

    @admin.display(description="Shipping Address")
    def full_address_card(self, obj):
        if obj.address:
            a = obj.address
            return format_html(
                '<div style="background: #ffffff; padding: 12px; border: 1px solid #eee; border-left: 5px solid #006bff; border-radius: 4px; color: #333; line-height: 1.6; font-size: 13px;">'
                '<b>Recipient:</b> {} {}<br><b>Street:</b> {}<br><b>Location:</b> {}, {}<br><b>Phone:</b> {}</div>',
                a.first_name, a.last_name, a.street, a.town.name, a.town.county.name, a.phone
            )
        return "No shipping address."

    @admin.display(description="Total")
    def total_price_formatted(self, obj): 
        return f"Ksh {int(obj.total_price):,}"

    @admin.display(description="Actions")
    def order_actions(self, obj):
        url = reverse('admin:products_order_change', args=[obj.pk])
        return format_html('<a class="button" style="background:#006bff; color:white; border:none; padding: 3px 10px; font-weight: bold; font-size: 11px;" href="{}">MANAGE</a>', url)

    def colored_status(self, obj):
        colors = {'Pending': '#6c757d', 'Confirmed': '#006bff', 'Processing': '#17a2b8', 'Ready for Pickup': '#5bc0de', 'Delivered': '#28a745', 'Cancelled': '#d9534f', 'Shipped': '#6f42c1'}
        return format_html('<span style="background:{}; color:white; padding:3px 10px; border-radius:10px; font-size:10px; font-weight:bold;">{}</span>', colors.get(obj.status, '#333'), obj.status)

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
            if old_status != obj.status: self.create_status_records(obj, obj.status)
        super().save_model(request, obj, form, change)

    @admin.action(description="⭐ Confirm Selected")
    def bulk_confirm(self, request, queryset): 
        for o in queryset: self.create_status_records(o, 'Confirmed')
        queryset.update(status='Confirmed')

    @admin.action(description="📦 Process Selected")
    def bulk_processing(self, request, queryset):
        for o in queryset: self.create_status_records(o, 'Processing')
        queryset.update(status='Processing')

    @admin.action(description="🚚 Ship Selected")
    def bulk_shipped(self, request, queryset):
        for o in queryset: self.create_status_records(o, 'Shipped')
        queryset.update(status='Shipped')

    @admin.action(description="📍 Ready Selected")
    def bulk_ready(self, request, queryset):
        for o in queryset: self.create_status_records(o, 'Ready for Pickup')
        queryset.update(status='Ready for Pickup')

    @admin.action(description="✅ Deliver Selected")
    def bulk_delivered(self, request, queryset):
        for o in queryset: self.create_status_records(o, 'Delivered')
        queryset.update(status='Delivered')

# ----------------------------------------------------------------      
# 5. OTHER MODELS
# ----------------------------------------------------------------
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'user', 'rating', 'created_at')
    readonly_fields = ('order_item', 'user', 'product_name')
    def product_name(self, obj): return obj.order_item.product.name

class PromotionStripAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order', 'bg_color_preview')
    filter_horizontal = ('products',)
    def bg_color_preview(self, obj):
        return format_html('<div style="width: 30px; height: 15px; background: {}; border: 1px solid #000;"></div>', obj.bg_color)

admin.site.register(Order, OrderAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(FlashSale, admin.ModelAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(PromotionStrip, PromotionStripAdmin)
admin.site.register(Category)
admin.site.register(Address)
admin.site.register(Town)
admin.site.register(County)
admin.site.register(Wishlist)
admin.site.register(Cart)
admin.site.register(Coupon)
admin.site.register(OrderTracking)