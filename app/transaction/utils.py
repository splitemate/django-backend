from transaction.models import TransactionParticipant, UserBalance


def update_user_balances_on_delete_or_restore(instance, reverse=False) -> None:
    """
    Updates user balances when a transaction is deleted or restored.

    If reverse=False → Adjust balances as if transaction is being deleted.
    If reverse=True  → Adjust balances as if transaction is being restored.
    """
    payer_id = instance.payer.id
    participants = TransactionParticipant.all_objects.filter(transaction=instance)
    participant_user_ids = participants.values_list('user_id', flat=True)
    user_balance_pairs = [tuple(sorted((payer_id, user_id))) for user_id in participant_user_ids]

    initiator_ids = [data[0] for data in user_balance_pairs]
    participant_ids = [data[1] for data in user_balance_pairs]

    existing_balances = {
        (balance.initiator.id, balance.participant.id): balance
        for balance in UserBalance.objects.filter(
            initiator_id__in=initiator_ids,
            participant_id__in=participant_ids
        )
    }

    factor = 1 if not reverse else -1

    for (initiator, participant), balance in existing_balances.items():
        is_initiator_payer = payer_id == initiator
        transaction_participant = participants.filter(user=participant if is_initiator_payer else initiator).first()

        if transaction_participant:
            amount_owed = transaction_participant.amount_owed * factor

            if is_initiator_payer:
                balance.balance -= amount_owed
                balance.total_amount_paid -= amount_owed
            else:
                balance.balance += amount_owed
                balance.total_amount_received -= amount_owed

            balance.transaction_count -= factor
            balance.save()
