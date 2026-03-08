from django.contrib import admin
from .models import (
    Product, Category, Order, Wishlist,
    County, Town, Address, Cart, CartItem
)

# 1. Register Category
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_class')

# 2. Register Product
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'stock')
    list_filter = ('category',)
    search_fields = ('name',)

# 3. Register Location Models
@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Town)
class TownAdmin(admin.ModelAdmin):
    list_display = ('name', 'county')
    list_filter = ('county',)

# 4. Register Address and Cart
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'street', 'town', 'phone')

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')

admin.site.register(CartItem)

# 5. Register remaining models
admin.site.register(Order)
admin.site.register(Wishlist)