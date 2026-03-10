from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from products.models import Order, Product, Category

class Command(BaseCommand):
    help = 'Create default user groups for the e-commerce admin'

    def handle(self, *args, **options):
        # Create Order Managers group
        order_managers, created = Group.objects.get_or_create(name='Order Managers')
        if created:
            # Get permissions for Order model
            order_content_type = ContentType.objects.get_for_model(Order)
            order_permissions = Permission.objects.filter(content_type=order_content_type)
            order_managers.permissions.set(order_permissions)
            self.stdout.write(self.style.SUCCESS('Created Order Managers group'))

        # Create Product Managers group
        product_managers, created = Group.objects.get_or_create(name='Product Managers')
        if created:
            # Get permissions for Product and Category models
            product_content_type = ContentType.objects.get_for_model(Product)
            product_permissions = Permission.objects.filter(content_type=product_content_type)
            category_content_type = ContentType.objects.get_for_model(Category)
            category_permissions = Permission.objects.filter(content_type=category_content_type)
            product_managers.permissions.set(list(product_permissions) + list(category_permissions))
            self.stdout.write(self.style.SUCCESS('Created Product Managers group'))

        self.stdout.write(self.style.SUCCESS('Groups created successfully'))