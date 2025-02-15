from django.db import models
from django.conf import settings
from group.models import Group
from django.utils import timezone
from django.db.models import Sum, Q, F
from core.models import ActiveManager


class TransactionTypes(models.TextChoices):
    DEBT = 'debt', 'Debt'
    SETTLEMENT = 'settlement', 'Settlement'


class Transaction(models.Model):
    is_active = models.BooleanField(default=True)
    payer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    split_count = models.PositiveIntegerField()
    description = models.CharField(max_length=255, blank=True, null=True)
    transaction_type = models.CharField(max_length=10, choices=TransactionTypes.choices, default='debt')
    transaction_date = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='transactions_created', on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        """Soft delete instead of actual delete."""
        self.is_active = False
        TransactionParticipant.all_objects.filter(transaction=self).update(is_active=False)
        self.save()

    def restore(self):
        """Restore a soft-deleted transaction."""
        transaction = Transaction.all_objects.filter(id=self.id).first()
        if not transaction:
            return
        transaction.is_active = True
        transaction.save()
        TransactionParticipant.all_objects.filter(transaction=transaction).update(is_active=True)

    def save(self, *args, **kwargs):
        if self.pk:
            original = Transaction.all_objects.get(pk=self.pk)
            if original.created_by != self.created_by:
                raise PermissionError("Only the user who created this transaction can modify it.")
        super(Transaction, self).save(*args, **kwargs)

    def get_split_details(self) -> list:
        """Get split details of a transaction."""
        participants = TransactionParticipant.objects.filter(transaction=self)
        split_details = []
        for participant in participants:
            split_details.append({
                'user': str(participant.user.id),
                'amount': float(participant.amount_owed)
            })
        return split_details

    def get_associated_members(self) -> list[int]:
        """Get associated user IDs of a transaction."""
        return list(TransactionParticipant.objects.filter(transaction=self).values_list('user_id', flat=True))

    def __str__(self):
        return f'{self.payer} - {self.total_amount}'


class TransactionParticipant(models.Model):
    is_active = models.BooleanField(default=True)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2)
    is_transaction_sattled = models.BooleanField(default=False)

    objects = ActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return f'{self.user} owes {self.amount_owed} in transaction {self.transaction}'


class UserBalance(models.Model):
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='balances_as_user', on_delete=models.CASCADE, db_index=True)
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
        constraints = [
            models.CheckConstraint(
                check=~Q(initiator=F('participant')),
                name='initiator_not_equal_participant'),
            ]

    def __str__(self):
        return f"Balance between {self.initiator} and {self.participant}: {self.balance}"

    def save(self, *args, **kwargs):
        if self.initiator_id == self.participant_id:
            raise ValueError("Cannot create a UserBalance record for the same user (initiator == participant).")
        super().save(*args, **kwargs)

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
