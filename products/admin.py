from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from auditlog.models import LogEntry
from auditlog.admin import LogEntryAdmin
from django.db.models import Sum, Count
from django.shortcuts import render
from .models import (
    Product, Category, Order, OrderItem, Wishlist,
    County, Town, Address, Cart, CartItem, Coupon, Review
)

# Import auth models for user/group management
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin

from auditlog.registry import auditlog

# Override default admin site index
class CustomAdminSite(admin.AdminSite):
    site_header = "Zando Administration"
    site_title = "Zando Admin"
    index_title = "Dashboard"

    def each_context(self, request):
        context = super().each_context(request)
        
        # Add custom dashboard data
        total_orders = Order.objects.count()
        total_revenue = Order.objects.filter(status__in=['Paid', 'Shipped', 'Delivered']).aggregate(Sum('total_price'))['total_price__sum'] or 0
        pending_orders = Order.objects.filter(status__in=['Pending', 'Processing']).count()
        recent_orders = Order.objects.order_by('-created_at')[:10]

        context.update({
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'pending_orders': pending_orders,
            'recent_orders': recent_orders,
        })
        
        return context

# Replace the default admin site
admin.site = CustomAdminSite()

# Register audit log
admin.site.register(LogEntry, LogEntryAdmin)

# Register built-in auth models on the custom site
admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)

# Import-Export Resources
class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'category__name', 'stock', 'description')

class OrderResource(resources.ModelResource):
    class Meta:
        model = Order
        fields = ('id', 'user__username', 'total_price', 'status', 'payment_method', 'created_at', 'phone_number')

# 1. Enhanced Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_class', 'product_count')
    search_fields = ('name',)

    def product_count(self, obj):
        return obj.product_set.count()
    product_count.short_description = 'Products'

# 2. Enhanced Product Admin
@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('name', 'price', 'category', 'stock', 'is_available')
    list_filter = ('category', 'stock')
    search_fields = ('name', 'description')
    list_editable = ('stock', 'price')
    ordering = ('name',)

    def is_available(self, obj):
        return obj.stock > 0
    is_available.boolean = True

# 3. OrderItem Inline for Order
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product', 'quantity', 'price', 'total')
    can_delete = False
    extra = 0

    def total(self, obj):
        return obj.quantity * obj.price
    total.short_description = 'Total'

# 4. Enhanced Order Admin
@admin.register(Order)
class OrderAdmin(ImportExportModelAdmin):
    resource_class = OrderResource
    list_display = ('id', 'user', 'total_price', 'discount_amount', 'coupon_code', 'status', 'payment_method', 'created_at', 'order_actions')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('user__username', 'id', 'transaction_id')
    readonly_fields = ('id', 'created_at', 'transaction_id')
    inlines = [OrderItemInline]
    actions = ['mark_as_processing', 'mark_as_paid', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled', 'send_status_email']

    def order_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">View Details</a>',
            reverse('admin:products_order_change', args=[obj.pk])
        )
    order_actions.short_description = 'Actions'

    def mark_as_processing(self, request, queryset):
        queryset.update(status='Processing')
        self.message_user(request, f"{queryset.count()} orders marked as Processing.")
    mark_as_processing.short_description = "Mark selected orders as Processing"

    def mark_as_paid(self, request, queryset):
        queryset.update(status='Paid')
        self.message_user(request, f"{queryset.count()} orders marked as Paid.")
    mark_as_paid.short_description = "Mark selected orders as Paid"

    def mark_as_shipped(self, request, queryset):
        queryset.filter(status__in=['Paid', 'Processing']).update(status='Shipped')
        self.message_user(request, f"{queryset.count()} orders marked as Shipped.")
    mark_as_shipped.short_description = "Mark selected orders as Shipped"

    def mark_as_delivered(self, request, queryset):
        queryset.filter(status='Shipped').update(status='Delivered')
        self.message_user(request, f"{queryset.count()} orders marked as Delivered.")
    mark_as_delivered.short_description = "Mark selected orders as Delivered"

    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='Cancelled')
        self.message_user(request, f"{queryset.count()} orders marked as Cancelled.")
    mark_as_cancelled.short_description = "Mark selected orders as Cancelled"

    def send_status_email(self, request, queryset):
        from django.core.mail import send_mail
        import os

        for order in queryset:
            subject = f'Order {order.id} Status Update'
            message = f'Your order status has been updated to: {order.status}'
            from_email = os.environ.get('EMAIL_HOST_USER', 'admin@zando.com')
            recipient_list = [order.user.email]
            try:
                send_mail(subject, message, from_email, recipient_list)
                self.message_user(request, f"Email sent to {order.user.username} for order {order.id}")
            except Exception as e:
                self.message_user(request, f"Failed to send email for order {order.id}: {str(e)}", level='error')
    send_status_email.short_description = "Send status update email to customers"

# 5. Location Models
@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Town)
class TownAdmin(admin.ModelAdmin):
    list_display = ('name', 'county')
    list_filter = ('county',)
    search_fields = ('name',)

# 6. Address Admin
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'street', 'town', 'phone', 'is_default')
    list_filter = ('is_default', 'town__county')
    search_fields = ('user__username', 'street', 'phone')

# 7. Cart and CartItem
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'item_count', 'total_price')
    search_fields = ('user__username',)

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'

    def total_price(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())
    total_price.short_description = 'Total'

class CartItemInline(admin.TabularInline):
    model = CartItem
    readonly_fields = ('product', 'quantity')
    can_delete = True
    extra = 0

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'total')
    list_filter = ('cart__user',)

    def total(self, obj):
        return obj.product.price * obj.quantity
    total.short_description = 'Total'

# 8. Wishlist
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'product__name')

# Register models for audit logging
auditlog.register(Product)
auditlog.register(Category)
auditlog.register(Order)
auditlog.register(OrderItem)
auditlog.register(Wishlist)
auditlog.register(Address)
auditlog.register(Cart)
auditlog.register(CartItem)

# Register all models with the custom admin site
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Wishlist, WishlistAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem, CartItemAdmin)
admin.site.register(County, CountyAdmin)
admin.site.register(Town, TownAdmin)
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'discount_amount', 'min_total', 'active', 'starts_at', 'ends_at')
    list_filter = ('active',)
    search_fields = ('code', 'description')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'comment')
