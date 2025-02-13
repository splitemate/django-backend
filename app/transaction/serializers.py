"""
Serializers for Transaction API View
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from transaction.models import Transaction, TransactionParticipant, UserBalance
from django.dispatch import Signal
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from itertools import chain
from app.helper import Helper
from transaction.utils import TransactionHelper
from datetime import datetime
from core.context import set_custom_context, clear_custom_context


User = get_user_model()
post_bulk_create_participants = Signal()


class AddTransactionSerializer(serializers.ModelSerializer):
    payer_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='payer', write_only=True)
    split_details = serializers.ListField(write_only=True)
    is_group = serializers.BooleanField(write_only=True)

    class Meta:
        model = Transaction
        fields = ['payer_id', 'group', 'total_amount', 'description', 'transaction_type', 'transaction_date', 'split_details', 'is_group']

    def accumulate_balance_changes(self, balance_changes, payer, split_details):
        """Accumulate balance changes for each initiator-participant pair in a dictionary."""

        participant_ids = [split['user'] for split in split_details]
        participants = User.objects.filter(id__in=participant_ids)
        participant_map = {user.id: user for user in participants}

        for split in split_details:
            participant_id = split['user']
            amount_owed = split['amount']

            participant = participant_map.get(int(participant_id))

            if not participant:
                Helper.raise_validation_error('ERR_PARTICIPANT_NOT_FOUND', {'participant_id': participant_id})

            initiator, participant = sorted([payer, participant], key=lambda x: x.id)
            is_initiator_payer = payer == initiator

            key = (initiator.id, participant.id)

            if key not in balance_changes:
                balance_changes[key] = {
                    'initiator': initiator,
                    'participant': participant,
                    'balance': 0,
                    'total_amount_paid': 0,
                    'total_amount_received': 0,
                    'transaction_count': 0,
                }

            if is_initiator_payer:
                balance_changes[key]['balance'] += amount_owed
                balance_changes[key]['total_amount_paid'] += amount_owed
            else:
                balance_changes[key]['balance'] -= amount_owed
                balance_changes[key]['total_amount_received'] += amount_owed

            balance_changes[key]['transaction_count'] += 1

    def bulk_update_user_balance(self, balance_changes):
        """Update the UserBalance in bulk based on the accumulated balance changes."""

        with transaction.atomic():
            initiator_ids = [key[0] for key in balance_changes]
            participant_ids = [key[1] for key in balance_changes]

            existing_balances = {
                (balance.initiator.id, balance.participant.id): balance
                for balance in UserBalance.objects.filter(initiator_id__in=initiator_ids, participant_id__in=participant_ids)
            }

            updates = []
            inserts = []

            for key, changes in balance_changes.items():
                initiator_id, participant_id = key

                balance_record = existing_balances.get((initiator_id, participant_id))

                if balance_record:
                    balance_record.balance += changes['balance']
                    balance_record.total_amount_paid += changes['total_amount_paid']
                    balance_record.total_amount_received += changes['total_amount_received']
                    balance_record.transaction_count += changes['transaction_count']
                    balance_record.last_transaction_date = timezone.now()
                    updates.append(balance_record)
                else:
                    new_balance = UserBalance(
                        initiator=changes['initiator'],
                        participant=changes['participant'],
                        balance=changes['balance'],
                        total_amount_paid=changes['total_amount_paid'],
                        total_amount_received=changes['total_amount_received'],
                        transaction_count=changes['transaction_count'],
                        last_transaction_date=timezone.now(),
                        is_active=True
                    )
                    inserts.append(new_balance)

            if inserts:
                created_records = UserBalance.objects.bulk_create(inserts)
            else:
                created_records = []

            if updates:
                UserBalance.objects.bulk_update(
                    updates, ['balance', 'total_amount_paid', 'total_amount_received', 'transaction_count', 'last_transaction_date']
                )
                updated_records = updates
            else:
                updated_records = []
            all_records = list(chain(created_records, updated_records))
            filtered_records = [record for record in all_records if record.initiator != record.participant]
            return filtered_records

    def validate(self, data):
        split_details = data.get('split_details', [])
        total_amount = data.get('total_amount')
        payer = data.get('payer')
        group = data.get('group', False)
        is_group = data.get('is_group', False)

        if not split_details:
            Helper.raise_validation_error("ERR_SPLIT_DETAILS_REQUIRED")

        user = self.context.get('user') or getattr(self.context.get('request'), 'user', None)
        user_ids = [user.id] if user else []

        total_split_amount = 0

        for split in split_details:
            try:
                user = int(split['user'])
                amount = float(split['amount'])
                if amount <= 0:
                    raise ValueError
            except (KeyError, ValueError):
                Helper.raise_validation_error("ERR_SPLIT_DETAILS_REQUIRED")
            user_ids.append(user)
            total_split_amount += amount

        if total_split_amount != total_amount:
            Helper.raise_validation_error("ERR_SPLIT_MISMATCH")

        if not payer.friends.filter(id__in=user_ids).exists():
            Helper.raise_validation_error("ERR_FRIENDS_REQUIRED")

        if is_group and not group:
            Helper.raise_validation_error("ERR_GROUP_REQUIRED")

        if is_group and group:
            group_participants_ids = set(group.participants.values_list('id', flat=True))
            if not set(user_ids).issubset(group_participants_ids):
                Helper.raise_validation_error("ERR_NON_GROUP_MEMBER")
        return data

    def create(self, validated_data):
        payer = validated_data['payer']
        group = validated_data.get('group', None)
        total_amount = validated_data['total_amount']
        description = validated_data.get('description', '')
        transaction_type = validated_data.get('transaction_type', 'debt')
        transaction_date = validated_data['transaction_date']
        split_details = validated_data['split_details']

        initial_user = self.context.get('user') or getattr(self.context.get('request'), 'user', None)
        set_custom_context('exclude_user', initial_user.id)
        transaction = Transaction.objects.create(
            payer=payer,
            group=group,
            total_amount=total_amount,
            description=description,
            transaction_type=transaction_type,
            transaction_date=transaction_date,
            created_by=initial_user,
            split_count=len(split_details)
        )
        clear_custom_context()

        participants = [
            TransactionParticipant(
                transaction=transaction,
                user=get_object_or_404(User, id=split['user']),
                amount_owed=split['amount'],

            ) for split in split_details
        ]

        TransactionParticipant.objects.bulk_create(participants)

        balance_changes = {}

        self.accumulate_balance_changes(balance_changes, payer, split_details)
        self.bulk_update_user_balance(balance_changes)
        post_bulk_create_participants.send(sender=Transaction, instance=transaction)
        return transaction


class ModifyTransactionSerializer(serializers.ModelSerializer):
    payer_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='payer', write_only=True)
    split_details = serializers.ListField(write_only=True)
    is_group = serializers.BooleanField(write_only=True)

    class Meta:
        model = Transaction
        fields = ['payer_id', 'group', 'total_amount', 'description', 'transaction_type', 'transaction_date', 'split_details', 'is_group']

    def validate(self, data):
        split_details = data.get('split_details', [])
        total_amount = data.get('total_amount')
        payer = data.get('payer')
        group = data.get('group', False)
        is_group = data.get('is_group', False)

        if not split_details:
            Helper.raise_validation_error("ERR_SPLIT_DETAILS_REQUIRED")

        user = self.context.get('user') or getattr(self.context.get('request'), 'user', None)
        user_ids = [user.id] if user else []

        total_split_amount = 0

        for split in split_details:
            try:
                user = int(split['user'])
                amount = float(split['amount'])
                if amount <= 0:
                    raise ValueError
            except (KeyError, ValueError):
                Helper.raise_validation_error("ERR_SPLIT_DETAILS_REQUIRED")
            user_ids.append(user)
            total_split_amount += amount

        if total_split_amount != total_amount:
            Helper.raise_validation_error("ERR_SPLIT_MISMATCH")

        if not payer.friends.filter(id__in=user_ids).exists():
            Helper.raise_validation_error("ERR_FRIENDS_REQUIRED")

        if is_group and not group:
            Helper.raise_validation_error("ERR_GROUP_REQUIRED")

        if is_group and group:
            group_participants_ids = set(group.participants.values_list('id', flat=True))
            if not set(user_ids).issubset(group_participants_ids):
                Helper.raise_validation_error("ERR_NON_GROUP_MEMBER")

        return data

    def accumulate_balance_changes(self, balance_changes, payer, split_details):
        """Accumulate balance changes for each initiator-participant pair in a dictionary."""

        participant_ids = [split['user'] for split in split_details]
        participants = User.objects.filter(id__in=participant_ids)
        participant_map = {user.id: user for user in participants}

        for split in split_details:
            participant_id = split['user']
            amount_owed = split['amount']

            participant = participant_map.get(int(participant_id))

            if not participant:
                Helper.raise_validation_error('ERR_PARTICIPANT_NOT_FOUND', {'participant_id': participant_id})

            initiator, participant = sorted([payer, participant], key=lambda x: x.id)
            is_initiator_payer = payer == initiator

            key = (initiator.id, participant.id)

            if key not in balance_changes:
                balance_changes[key] = {
                    'initiator': initiator,
                    'participant': participant,
                    'balance': 0,
                    'total_amount_paid': 0,
                    'total_amount_received': 0,
                    'transaction_count': 0,
                }

            balance_change = amount_owed if is_initiator_payer else -amount_owed
            total_received_key = 'total_amount_received' if not is_initiator_payer else 'total_amount_paid'
            total_paid_key = 'total_amount_paid' if not is_initiator_payer else 'total_amount_received'

            if balance_changes[key].get('remove_entry', False):
                balance_changes[key]['balance'] -= balance_change
                balance_changes[key][total_paid_key] += amount_owed
            else:
                balance_changes[key]['balance'] += balance_change
                balance_changes[key][total_received_key] += amount_owed

            if split.get('remove_entry', False):
                balance_changes[key]['transaction_count'] -= 1

    def bulk_update_user_balance(self, balance_changes):
        """Update the UserBalance in bulk based on the accumulated balance changes."""
        with transaction.atomic():
            initiator_ids = [key[0] for key in balance_changes]
            participant_ids = [key[1] for key in balance_changes]

            existing_balances = {
                (balance.initiator.id, balance.participant.id): balance
                for balance in UserBalance.objects.filter(initiator_id__in=initiator_ids, participant_id__in=participant_ids)
            }

            updates = []
            inserts = []

            for key, changes in balance_changes.items():
                initiator_id, participant_id = key

                balance_record = existing_balances.get((initiator_id, participant_id))

                if balance_record:
                    balance_record.balance += changes['balance']
                    balance_record.total_amount_paid += changes['total_amount_paid']
                    balance_record.total_amount_received += changes['total_amount_received']
                    balance_record.transaction_count += changes['transaction_count']
                    balance_record.last_transaction_date = timezone.now()
                    updates.append(balance_record)
                else:
                    new_balance = UserBalance(
                        initiator=changes['initiator'],
                        participant=changes['participant'],
                        balance=changes['balance'],
                        total_amount_paid=changes['total_amount_paid'],
                        total_amount_received=changes['total_amount_received'],
                        transaction_count=changes['transaction_count'],
                        last_transaction_date=timezone.now(),
                        is_active=True
                    )
                    inserts.append(new_balance)

            if inserts:
                created_records = UserBalance.objects.bulk_create(inserts)
            else:
                created_records = []

            if updates:
                UserBalance.objects.bulk_update(
                    updates, ['balance', 'total_amount_paid', 'total_amount_received', 'transaction_count', 'last_transaction_date']
                )
                updated_records = updates
            else:
                updated_records = []

            all_records = list(chain(created_records, updated_records))
            filtered_records = [record for record in all_records if record.initiator != record.participant]
            return filtered_records

    def update(self, instance, validated_data):
        payer = validated_data.get('payer', instance.payer)
        group = validated_data.get('group')
        total_amount = validated_data.get('total_amount', instance.total_amount)
        description = validated_data.get('description', instance.description)
        transaction_type = validated_data.get('transaction_type', instance.transaction_type)
        transaction_date = validated_data.get('transaction_date', instance.transaction_date)

        split_details = validated_data.get('split_details', [])
        split_details = TransactionHelper.transform_split_data(split_details)

        user = self.context.get('user') or getattr(self.context.get('request'), 'user', None)
        initial_user = user
        initial_user_id = getattr(user, 'id', False)

        if instance.created_by.id != initial_user_id:
            Helper.raise_validation_error("ERR_NOT_OWNER")

        balance_changes = {}
        old_split_details = []
        old_split_details_dict = {}

        old_split_details_obj = instance.transactionparticipant_set.values('user_id', 'amount_owed')
        for detail in old_split_details_obj:
            old_split_details_dict[detail['user_id']] = {'amount': detail['amount_owed']}
            old_split_details.append({'user': detail['user_id'], 'amount': detail['amount_owed']})

        excluded_ids = list(set(user.get('user') for user in old_split_details) - set(user.get('user') for user in split_details))

        instance.payer = payer
        instance.group = group
        instance.total_amount = total_amount
        instance.description = description
        instance.transaction_type = transaction_type
        instance.transaction_date = transaction_date
        instance.split_count = len(split_details)
        instance.updated_at = datetime.now()

        existing_participants = {p.user_id: p for p in instance.transactionparticipant_set.all()}
        new_user_ids = {split['user']: split['amount'] for split in split_details}

        for user_id, amount in new_user_ids.items():
            if user_id in existing_participants:
                participant = existing_participants[user_id]
                if participant.amount_owed != amount:
                    participant.amount_owed = amount
                    participant.save()
                del existing_participants[user_id]
            else:
                TransactionParticipant.objects.create(
                    transaction=instance,
                    user=get_object_or_404(User, id=user_id),
                    amount_owed=amount,
                )

        for participant in existing_participants.values():
            participant.delete()

        for data in split_details:
            id = data.get('user')
            user = old_split_details_dict.get(id)
            if user:
                old_amount = data.get('amount')
                new_amount = user.get('amount')
                data['amount'] = old_amount - new_amount if old_amount != new_amount else 0

        for user in excluded_ids:
            amount = old_split_details_dict.get(user, {}).get('amount', 0)
            split_details.append({'user': user, 'amount': amount * -1, 'remove_entry': True})

        self.accumulate_balance_changes(balance_changes, payer, split_details)
        self.bulk_update_user_balance(balance_changes)

        set_custom_context('exclude_user', initial_user.id)
        instance.save()
        clear_custom_context()

        return instance
