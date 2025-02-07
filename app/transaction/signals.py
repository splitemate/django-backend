from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from transaction.models import Transaction
from transaction.utils import update_user_balances_on_delete_or_restore
from activity.models import Activity, ActivityType


@receiver(pre_save, sender=Transaction)
def capture_old_transaction_state(sender, instance, **kwargs):
    """Capture the previous state of is_active before saving."""
    try:
        old_instance = sender.all_objects.get(pk=instance.pk)
        instance._old_is_active = old_instance.is_active
    except sender.DoesNotExist:
        instance._old_is_active = None


@receiver(post_save, sender=Transaction)
def handle_transaction_modification_change(sender, instance, created, **kwargs):
    """Handle actions when a transaction is reactivated from a soft delete."""
    if not created:
        old_is_active = getattr(instance, "_old_is_active", None)

        if old_is_active is False and instance.is_active:
            update_user_balances_on_delete_or_restore(instance, reverse=True)
            Activity.objects.create(
                user_id=instance.created_by,
                activity_type=ActivityType.RESTORED_TRANSACTION,
                transaction_id=instance,
                comments={"message": f"Transaction '{instance.id}' was restored."},
            )

        elif old_is_active is True and not instance.is_active:
            update_user_balances_on_delete_or_restore(instance, reverse=False)
            Activity.objects.create(
                user_id=instance.created_by,
                activity_type=ActivityType.DELETED_TRANSACTION,
                transaction_id=instance,
                comments={"message": f"Transaction '{instance.id}' was deleted."},
            )
        else:
            Activity.objects.create(
                user_id=instance.created_by,
                activity_type=ActivityType.MODIFIED_TRANSACTION,
                transaction_id=instance,
                comments={"message": f"Transaction '{instance.id}' was modified."},
            )

    else:
        Activity.objects.create(
            user_id=instance.created_by,
            activity_type=ActivityType.ADDED_TRANSACTION,
            transaction_id=instance,
            comments={"message": f"{instance.created_by.email} created the transaction '{instance.id}'"},
        )


@receiver(pre_delete, sender=Transaction)
def handle_user_balance_on_transaction_delete(sender, instance, **kwargs):
    update_user_balances_on_delete_or_restore(instance, reverse=False)
