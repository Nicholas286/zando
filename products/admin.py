from django.contrib import admin
from .models import Product, Category, Order, Wishlist

# 1. Register Category
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_class')

# 2. Register Product (This handles registration, so no need for site.register below)
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'stock')
    list_filter = ('category',)
    search_fields = ('name',)

# 3. Register the remaining models normally
admin.site.register(Order)
admin.site.register(Wishlist)