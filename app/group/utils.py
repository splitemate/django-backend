from transaction.models import Transaction, TransactionParticipant


def can_group_be_deleted(group):
    """Check if the group can be deleted.
    A group can be deleted only if all its transactions have participants that are settled.
    """
    transactions = Transaction.all_objects.filter(group=group)
    return not TransactionParticipant.all_objects.filter(transaction__in=transactions, is_transaction_sattled=False).exists()
