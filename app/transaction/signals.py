from django.db.models.signals import post_delete
from django.dispatch import receiver
from transaction.models import Transaction, TransactionParticipant, UserBalance
from activity.models import Activity, ActivityType


@receiver(post_delete, sender=Transaction)
def handle_transaction_deletion(sender, instance, **kwargs):
    """
    1. Reverse the balances when a transaction is deleted.
    2. Log an activity for tracking.
    """
    payer_id = instance.payer.id
    participants = TransactionParticipant.objects.filter(transaction=instance)
    participant_user_ids = participants.values_list('user_id', flat=True)
    user_balance_pairs = []

    for user_id in participant_user_ids:
        sorted_tuple = tuple(sorted((payer_id, user_id)))
        user_balance_pairs.append(sorted_tuple)

    initiator_ids = [data[0] for data in user_balance_pairs]
    participant_ids = [data[1] for data in user_balance_pairs]

    existing_balances = {
        (balance.initiator.id, balance.participant.id): balance
        for balance in UserBalance.objects.filter(
            initiator_id__in=initiator_ids,
            participant_id__in=participant_ids
        )
    }

    for ids, blc in existing_balances.items():
        initiator = ids[0]
        participant = ids[1]
        is_initiator_payer = payer_id == initiator

        if is_initiator_payer:
            transaction_participant = participants.filter(user=participant).first()
            if transaction_participant:
                blc.balance -= transaction_participant.amount_owed
                blc.total_amount_paid -= transaction_participant.amount_owed
                blc.transaction_count -= 1
                blc.save()
        else:
            transaction_participant = participants.filter(user=initiator).first()
            if transaction_participant:
                blc.balance += transaction_participant.amount_owed
                blc.total_amount_received -= transaction_participant.amount_owed
                blc.transaction_count -= 1
                blc.save()

    if instance.created_by:
        Activity.objects.create(
            user_id=instance.created_by,
            transaction_id=instance,
            activity_type=ActivityType.DELETED_TRANSACTION,
            comments={"message": f"Transaction {instance.id} was deleted and balances were updated."},
        )
