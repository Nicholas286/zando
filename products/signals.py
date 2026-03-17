from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.template.loader import render_to_string

from .models import Order, OrderNotification


@receiver(pre_save, sender=Order)
def remember_previous_order_status(sender, instance: Order, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        instance._previous_status = sender.objects.only("status").get(pk=instance.pk).status
    except sender.DoesNotExist:
        instance._previous_status = None

    # If status is being set to Delivered, capture delivered timestamp once.
    if instance._previous_status != "Delivered" and instance.status == "Delivered" and not instance.delivered_at:
        from django.utils import timezone
        instance.delivered_at = timezone.now()


@receiver(post_save, sender=Order)
def send_order_status_update_email(sender, instance: Order, created: bool, **kwargs):
    """
    Send an email to the customer whenever an existing order's status changes.
    This triggers on Order.save(); note that bulk updates (queryset.update)
    do not emit signals.
    """
    if created:
        # Create an in-app inbox notification for new orders
        OrderNotification.objects.create(
            user=instance.user,
            order=instance,
            status=instance.status,
            message=f"Your order #{instance.id} has been placed.",
        )
        return

    previous_status = getattr(instance, "_previous_status", None)
    if not previous_status or previous_status == instance.status:
        return

    # Create an in-app inbox notification (always, even if user has no email)
    OrderNotification.objects.create(
        user=instance.user,
        order=instance,
        status=instance.status,
        message=_status_message(instance.id, instance.status),
    )

    user_email = getattr(instance.user, "email", "") or ""
    if not user_email:
        return

    subject = f"Zando: Order #{instance.id} {instance.status}"
    message = _status_message(instance.id, instance.status)
    html_message = render_to_string("emails/order_status_update.html", {
        "username": instance.user.username,
        "order_id": instance.id,
        "status": instance.status,
        "previous_status": previous_status,
        "message": message,
        "order": instance,
    })

    send_mail(
        subject,
        message,
        getattr(settings, "DEFAULT_FROM_EMAIL", "from@zando.com"),
        [user_email],
        html_message=html_message,
    )


def _status_message(order_id: int, status: str) -> str:
    s = (status or "").strip()
    if s == "Ready for Pickup":
        return f"Your order #{order_id} is ready for pickup."
    if s == "Shipped":
        return f"Your order #{order_id} has been shipped."
    if s == "Delivered":
        return f"Your order #{order_id} has been delivered."
    if s == "Cancelled":
        return f"Your order #{order_id} has been cancelled."
    if s == "Confirmed":
        return f"Your order #{order_id} has been confirmed."
    if s == "Paid":
        return f"Your order #{order_id} has been paid."
    if s == "Processing":
        return f"Your order #{order_id} is being processed."
    if s == "Pending":
        return f"Your order #{order_id} is pending."
    return f"Your order #{order_id} status is now {s}."

