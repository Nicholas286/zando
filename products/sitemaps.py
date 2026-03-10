from django.contrib.sitemaps import Sitemap
from .models import Product, Category

class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Product.objects.all()

    def lastmod(self, obj):
        return None

class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.all()

    def lastmod(self, obj):
        return None
