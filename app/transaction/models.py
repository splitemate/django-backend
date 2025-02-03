from django.db import models
from django.conf import settings
from group.models import Group
from django.utils import timezone
from django.db.models import Sum, Q


class TransactionTypes(models.TextChoices):
    DEBT = 'debt', 'Debt'
    SETTLEMENT = 'settlement', 'Settlement'


class Transaction(models.Model):
    payer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    split_count = models.PositiveIntegerField()
    description = models.CharField(max_length=255, blank=True, null=True)
    transaction_type = models.CharField(max_length=10, choices=TransactionTypes.choices, default='debt')
    transaction_date = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='transactions_created', on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk:
            original = Transaction.objects.get(pk=self.pk)
            if original.created_by != self.created_by:
                raise PermissionError("Only the user who created this transaction can modify it.")
        super(Transaction, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        payer_id = self.payer.id
        participants = TransactionParticipant.objects.filter(transaction=self)
        participant_user_ids = participants.values_list('user_id', flat=True)
        user_balance_pairs = []

        
        for user_id in participant_user_ids:
            sorted_tuple = tuple(sorted((payer_id, user_id)))
            user_balance_pairs.append(sorted_tuple)

        initiator_ids = [data[0] for data in user_balance_pairs]
        participant_ids = [data[1] for data in user_balance_pairs]

        existing_balances = {
                (balance.initiator.id, balance.participant.id): balance
                for balance in UserBalance.objects.filter(initiator_id__in=initiator_ids, participant_id__in=participant_ids)
        }

        for ids, blc in existing_balances.items():
            initiator = ids[0]
            payer = ids[1]
            is_initiator_payer = payer_id == initiator

            if is_initiator_payer:
                transaction_participant = participants.filter(user=payer).first()
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
        super(Transaction, self).delete(*args, **kwargs)

    def __str__(self):
        return f'{self.payer} - {self.total_amount}'


class TransactionParticipant(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.user} owes {self.amount_owed} in transaction {self.transaction}'


class UserBalance(models.Model):
    initiator  = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='balances_as_user', on_delete=models.CASCADE, db_index=True)
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='balances_as_friend', on_delete=models.CASCADE, db_index=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount_received = models.DecimalField(max_digits=10, decimal_places=2)
    last_transaction_date = models.DateTimeField(default=timezone.now)
    transaction_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('initiator', 'participant')
        ordering = ['last_transaction_date']

    def __str__(self):
        return f"Balance between {self.initiator} and {self.participant}: {self.balance}"
    
    @classmethod
    def get_user_balance(cls, user_id) -> dict:
        """
        Calculate total balance of a user

        Args:
            user_id (str): The user id for which balance to be calculated.

        Returns:
            float: Total balance of user.
        """
        credit = (
            cls.objects.filter(initiator_id=user_id)
            .aggregate(total_owed=Sum('balance'))['total_owed'] or 0
        )

        debit = (
            cls.objects.filter(participant_id=user_id)
            .aggregate(total_due=Sum('balance'))['total_due'] or 0
        )

        net_balance = credit - debit

        return {
            "total_owed": float(credit),
            "total_due": float(debit),
            "net_balance": float(net_balance)
        }
