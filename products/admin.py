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
    OrderNotification, OrderTracking 
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
        if obj and obj.quantity is not None and obj.price is not None:
            return format_html("<span style='color:#000; font-weight:bold;'>Ksh {:,.0f}</span>", obj.quantity * obj.price)
        return "Ksh 0"

# ----------------------------------------------------------------      
# 3. ORDER ADMIN (FIXED FOR DOUBLE MESSAGES & BULK ACTIONS)
# ----------------------------------------------------------------
class OrderAdmin(ImportExportModelAdmin):
    list_display = ('id', 'user', 'colored_status', 'total_price_formatted', 'created_at', 'order_actions')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('id', 'user__username', 'phone_number')
    inlines = [OrderItemInline]
    
    # Bulk actions dropdown at the top of the list
    actions = ['bulk_confirm', 'bulk_processing', 'bulk_shipped', 'bulk_ready', 'bulk_delivered']

    fieldsets = (
        ('ORDER TRACKING', {'fields': ('status_timeline', 'status', ('payment_method', 'transaction_id'))}),
        ('CUSTOMER DETAILS', {'fields': (('user', 'phone_number'), 'customer_email')}),
        ('SHIPPING LOCATION', {'fields': ('delivery_method', 'full_address_card')}),
        ('BILLING SUMMARY', {'fields': (('total_price', 'discount_amount'), 'coupon_code')}),
    )

    readonly_fields = ('status_timeline', 'customer_email', 'full_address_card', 'user')

    # --- THE HELPER: Handles Tracking & Notifications ONLY ---
    def create_status_records(self, order, new_status):
        """Creates history and notification record without double-saving the order."""
        msg_map = {
            'Confirmed': 'Order confirmed. We are getting it ready.',
            'Processing': 'Items are being packed at our warehouse.',
            'Shipped': 'Package dispatched! On the way to you.',
            'Ready for Pickup': 'Package is ready at your pickup station.',
            'Delivered': 'Successfully delivered. Enjoy your purchase!',
            'Cancelled': 'Order has been cancelled.',
        }
        msg = msg_map.get(new_status, f"Order status updated to {new_status}")

        # Add to Timeline History
        OrderTracking.objects.create(order=order, status=new_status, message=msg)

        # Add to App Inbox
        OrderNotification.objects.create(user=order.user, order=order, status=new_status, message=msg)

    # --- SINGLE ORDER SAVE (When editing one page) ---
    def save_model(self, request, obj, form, change):
        if change:
            # Check if status changed compared to the database
            old_status = Order.objects.get(pk=obj.pk).status
            if old_status != obj.status:
                self.create_status_records(obj, obj.status)
        super().save_model(request, obj, form, change)

    # --- BULK ACTIONS (When selecting multiple checkboxes) ---
    def bulk_confirm(self, request, queryset):
        for order in queryset:
            self.create_status_records(order, 'Confirmed')
        queryset.update(status='Confirmed')
    bulk_confirm.short_description = "⭐ Mark as Confirmed"

    def bulk_processing(self, request, queryset):
        for order in queryset:
            self.create_status_records(order, 'Processing')
        queryset.update(status='Processing')
    bulk_processing.short_description = "📦 Mark as Processing"

    def bulk_shipped(self, request, queryset):
        for order in queryset:
            self.create_status_records(order, 'Shipped')
        queryset.update(status='Shipped')
    bulk_shipped.short_description = "🚚 Mark as Shipped"

    def bulk_ready(self, request, queryset):
        for order in queryset:
            self.create_status_records(order, 'Ready for Pickup')
        queryset.update(status='Ready for Pickup')
    bulk_ready.short_description = "📍 Mark as Ready for Pickup"

    def bulk_delivered(self, request, queryset):
        for order in queryset:
            self.create_status_records(order, 'Delivered')
        queryset.update(status='Delivered')
    bulk_delivered.short_description = "✅ Mark as Delivered"

    # --- UI HELPERS ---
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
            return format_html('<div style="background: #ffffff; padding: 15px; border: 1px solid #ccc; border-left: 6px solid #ffa500; border-radius: 4px; color: #000 !important; line-height: 1.8;">'
                               '<span style="color: #000;"><strong>Recipient:</strong> {} {}</span><br>'
                               '<span style="color: #000;"><strong>Street:</strong> {}</span><br>'
                               '<span style="color: #000;"><strong>Location:</strong> {}, {}</span><br>'
                               '<span style="color: #000;"><strong>Phone:</strong> {}</span></div>',
                               a.first_name, a.last_name, a.street, a.town.name, a.town.county.name, a.phone)
        return "No shipping address linked."

    def customer_email(self, obj): return obj.user.email

    def colored_status(self, obj):
        colors = {'Pending': '#6c757d', 'Confirmed': '#007bff', 'Processing': '#17a2b8', 'Ready for Pickup': '#ffa500', 'Delivered': '#198754', 'Cancelled': '#dc3545', 'Shipped': '#6f42c1'}
        color = colors.get(obj.status, '#333')
        return format_html('<span style="background:{}; color:white; padding:4px 12px; border-radius:20px; font-size:10px; font-weight:bold;">{}</span>', color, obj.status)

    def total_price_formatted(self, obj): return f"Ksh {int(obj.total_price):,}"

    def order_actions(self, obj):
        url = reverse('admin:products_order_change', args=[obj.pk])
        return format_html('<a class="button" style="background:#ffa500; color:white; border:none; padding: 4px 12px; font-weight: bold;" href="{}">MANAGE</a>', url)

# ----------------------------------------------------------------      
# 4. REGISTRATION
# ----------------------------------------------------------------
class ProductAdmin(ImportExportModelAdmin):
    list_display = ('name', 'category', 'price_display', 'colored_stock')
    def price_display(self, obj): return f"Ksh {int(obj.price):,}"
    def colored_stock(self, obj):
        color = "#d9534f" if obj.stock < 5 else "#5cb85c"
        return format_html('<b style="color:{}">{} in stock</b>', color, obj.stock)

admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Category); admin.site.register(Address); admin.site.register(Town)
admin.site.register(County); admin.site.register(Wishlist); admin.site.register(Cart)
admin.site.register(Coupon); admin.site.register(Review); admin.site.register(OrderTracking)