from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from transaction.models import Transaction
from transaction.utils import TransactionHelper
from transaction.serializers import post_bulk_create_participants
from activity.models import Activity, ActivityType


@receiver(pre_save, sender=Transaction)
def capture_old_transaction_state(sender, instance, **kwargs):
    """Capture the previous state of is_active before saving."""
    try:
        old_instance = sender.all_objects.get(pk=instance.pk)
        instance._old_is_active = old_instance.is_active
        instance._old_members = old_instance.get_associated_members()
        instance._old_payer = old_instance.payer
    except sender.DoesNotExist:
        instance._old_is_active = None


@receiver(post_save, sender=Transaction)
def handle_transaction_modification_change(sender, instance, created, **kwargs):
    """Handle actions when a transaction is reactivated from a soft delete."""
    if not created:
        old_is_active = getattr(instance, "_old_is_active", None)
        old_payer = getattr(instance, "_old_payer", None)
        old_members = getattr(instance, "_old_members", None)
        new_members = instance.get_associated_members()
        payers = [instance.payer.id, old_payer.id if old_payer else None]
        related_user_ids = set(old_members or []) | set(new_members or []) | set(payers)

        if old_is_active is False and instance.is_active:
            TransactionHelper.update_user_balances_on_delete_or_restore(instance, reverse=True)
            activity = Activity.objects.create(
                user_id=instance.created_by,
                activity_type=ActivityType.RESTORED_TRANSACTION,
                transaction_id=instance,
                comments={"message": f"Transaction '{instance.id}' was restored."},
            )

        elif old_is_active is True and not instance.is_active:
            TransactionHelper.update_user_balances_on_delete_or_restore(instance, reverse=False)
            activity = Activity.objects.create(
                user_id=instance.created_by,
                activity_type=ActivityType.DELETED_TRANSACTION,
                transaction_id=instance,
                comments={"message": f"Transaction '{instance.id}' was deleted."},
            )
        else:
            activity = Activity.objects.create(
                user_id=instance.created_by,
                activity_type=ActivityType.MODIFIED_TRANSACTION,
                transaction_id=instance,
                comments={"message": f"Transaction '{instance.id}' was modified."},
            )
        activity.related_users_ids.add(*related_user_ids)


@receiver(post_bulk_create_participants)
def handle_transaction_creation_with_partiticpants(sender, instance, **kwargs):
    transaction = instance
    activity = Activity.objects.create(
        user_id=transaction.created_by,
        activity_type=ActivityType.ADDED_TRANSACTION,
        transaction_id=transaction,
        comments={"message": f"{transaction.created_by.email} created the transaction '{transaction.id}'"},
    )
    related_user_ids = set(transaction.get_associated_members())
    activity.related_users_ids.add(*related_user_ids)


@receiver(pre_delete, sender=Transaction)
def handle_user_balance_on_transaction_delete(sender, instance, **kwargs):
    if not instance.is_active:
        return
    TransactionHelper.update_user_balances_on_delete_or_restore(instance, reverse=False)
