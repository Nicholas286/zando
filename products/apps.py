from django.apps import AppConfig


class ProductsConfig(AppConfig):
    name = 'products'

    def ready(self):
        # Register signal handlers
        from . import signals  # noqa: F401
