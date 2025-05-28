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
    payer_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='payer', write_only=True
    )
    split_details = serializers.ListField(write_only=True)
    is_group = serializers.BooleanField(write_only=True)

    class Meta:
        model = Transaction
        fields = [
            'payer_id', 'group', 'total_amount', 'description',
            'transaction_type', 'transaction_date', 'split_details', 'is_group'
        ]

    def validate(self, data):
        split_details = data.get('split_details', [])
        total_amount = data.get('total_amount')
        payer = data.get('payer')
        group = data.get('group', None)
        is_group = data.get('is_group', False)

        if not split_details:
            Helper.raise_validation_error("ERR_SPLIT_DETAILS_REQUIRED")

        user_ids = []
        total_split_amount = 0

        split_users_set = set()
        for split in split_details:
            try:
                participant_id = int(split['user'])
                amount = float(split['amount'])
                if amount < 0:
                    raise ValueError
            except (KeyError, ValueError):
                Helper.raise_validation_error("ERR_SPLIT_DETAILS_REQUIRED")

            split_users_set.add(participant_id)
            user_ids.append(participant_id)
            total_split_amount += amount

        if total_split_amount != total_amount:
            Helper.raise_validation_error("ERR_SPLIT_MISMATCH")

        if payer.id not in split_users_set:
            Helper.raise_validation_error("ERR_PAYER_NOT_IN_SPLIT")

        non_friends = [uid for uid in user_ids if not payer.friends.filter(id=uid).exists() and uid != payer.id]
        if non_friends:
            Helper.raise_validation_error("ERR_FRIENDS_REQUIRED")

        if is_group and not group:
            Helper.raise_validation_error("ERR_GROUP_REQUIRED")

        if is_group and group:
            group_participants_ids = set(group.participants.values_list('id', flat=True))
            if set(user_ids) != group_participants_ids:
                Helper.raise_validation_error("ERR_NOT_ALL_GROUP_MEMBERS_INCLUDED")

        return data

    def accumulate_balance_changes(self, balance_changes, payer, split_details):
        """Accumulate balance changes for each initiator-participant pair in a dictionary."""
        participant_ids = [split['user'] for split in split_details]
        participants = User.objects.filter(id__in=participant_ids)
        participant_map = {user.id: user for user in participants}

        for split in split_details:
            participant_id = split['user']
            amount_owed = split['amount']

            # Skip zero-amount as new user balance
            if amount_owed == 0:
                continue

            participant = participant_map.get(int(participant_id))
            if not participant:
                Helper.raise_validation_error('ERR_PARTICIPANT_NOT_FOUND', {'participant_id': participant_id})

            initiator, participant = sorted([payer, participant], key=lambda x: x.id)

            if initiator.id == participant.id:
                # Means the same user => skip
                continue

            is_initiator_payer = (payer == initiator)
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
                (bal.initiator.id, bal.participant.id): bal
                for bal in UserBalance.objects.filter(
                    initiator_id__in=initiator_ids, participant_id__in=participant_ids
                )
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
                    updates,
                    ['balance', 'total_amount_paid', 'total_amount_received',
                     'transaction_count', 'last_transaction_date']
                )
                updated_records = updates
            else:
                updated_records = []

            all_records = list(chain(created_records, updated_records))
            filtered_records = [r for r in all_records if r.initiator != r.participant]
            return filtered_records

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
    payer_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='payer', write_only=True
    )
    split_details = serializers.ListField(write_only=True)
    is_group = serializers.BooleanField(write_only=True)

    class Meta:
        model = Transaction
        fields = [
            'payer_id', 'group', 'total_amount', 'description',
            'transaction_type', 'transaction_date', 'split_details', 'is_group'
        ]

    def validate(self, data):
        split_details = data.get('split_details', [])
        total_amount = data.get('total_amount')
        payer = data.get('payer')
        group = data.get('group', None)
        is_group = data.get('is_group', False)

        if not split_details:
            Helper.raise_validation_error("ERR_SPLIT_DETAILS_REQUIRED")

        user_ids = []
        total_split_amount = 0
        split_users_set = set()

        for split in split_details:
            try:
                participant_id = int(split['user'])
                amount = float(split['amount'])
                # Now allow amount >= 0
                if amount < 0:
                    raise ValueError
            except (KeyError, ValueError):
                Helper.raise_validation_error("ERR_SPLIT_DETAILS_REQUIRED")

            split_users_set.add(participant_id)
            user_ids.append(participant_id)
            total_split_amount += amount

        if total_split_amount != total_amount:
            Helper.raise_validation_error("ERR_SPLIT_MISMATCH")

        if payer.id not in split_users_set:
            Helper.raise_validation_error("ERR_PAYER_NOT_IN_SPLIT")

        non_friends = [uid for uid in user_ids if uid != payer.id and not payer.friends.filter(id=uid).exists()]
        if non_friends:
            Helper.raise_validation_error("ERR_FRIENDS_REQUIRED")

        if is_group and not group:
            Helper.raise_validation_error("ERR_GROUP_REQUIRED")

        if is_group and group:
            group_participants_ids = set(group.participants.values_list('id', flat=True))
            if set(user_ids) != group_participants_ids:
                Helper.raise_validation_error("ERR_NOT_ALL_GROUP_MEMBERS_INCLUDED")

        return data

    def accumulate_balance_changes(self, new_payer_id, old_payer_id, split_details, old_split_details):
        """Accumulate balance changes for each initiator-participant pair in a dictionary."""

        is_payer_changed = new_payer_id != old_payer_id
        new_balance_map = {
            (min(s['user'], new_payer_id), max(s['user'], new_payer_id)): s['amount'] for s in split_details if s['user'] != new_payer_id
        }

        old_balance_map = {
            (min(os['user'], old_payer_id), max(os['user'], old_payer_id)): os['amount'] for os in old_split_details if os['user'] != old_payer_id
        }

        all_user_ids = set()
        for key in list(new_balance_map.keys()) + list(old_balance_map.keys()):
            all_user_ids.update(key)

        all_user_ids = list(all_user_ids)
        all_users = User.objects.filter(id__in=all_user_ids)
        all_users_map = {user.id: user for user in all_users}

        modification_balance_map = {}

        will_create_bal = {k: v for k, v in new_balance_map.items() if k not in old_balance_map}
        will_reverse_bal = {k: v for k, v in old_balance_map.items() if k not in new_balance_map and is_payer_changed}
        will_update_bal = {k: {'new_balance': new_balance_map[k], 'old_balance': old_balance_map[k]} for k in new_balance_map.keys() & old_balance_map.keys()}

        for k, v in will_create_bal.items():
            bal_initiator = k[0]
            is_initiator_payer = (new_payer_id == bal_initiator)

            amount_owed = v if is_initiator_payer else -v
            total_paid_bal = v if is_initiator_payer else 0
            total_received_bal = 0 if is_initiator_payer else v

            modification_balance_map[k] = {
                'initiator': all_users_map.get(k[0]),
                'participant': all_users_map.get(k[1]),
                'increase_balance': amount_owed,
                'increase_transaction_count': 1,
                'increase_total_amount_paid': total_paid_bal,
                'increase_total_amount_received': total_received_bal
            }

        for k, v in will_reverse_bal.items():
            bal_initiator = k[0]
            is_initiator_payer = (new_payer_id == bal_initiator)

            amount_owed = -v
            total_paid_bal = 0 if is_initiator_payer else -v
            total_received_bal = -v if is_initiator_payer else 0

            modification_balance_map[k] = {
                'initiator': all_users_map.get(k[0]),
                'participant': all_users_map.get(k[1]),
                'increase_balance': amount_owed,
                'increase_transaction_count': -1,
                'increase_total_amount_paid': total_paid_bal,
                'increase_total_amount_received': total_received_bal
            }

        for k, data in will_update_bal.items():
            old_amt = data['old_balance']
            new_amt = data['new_balance']
            delta = new_amt - old_amt

            bal_initiator = k[0]
            is_initiator_new_payer = (new_payer_id == bal_initiator)
            is_initiator_old_payer = (old_payer_id == bal_initiator)

            if is_initiator_new_payer == is_initiator_old_payer:
                amount_owed = delta if is_initiator_new_payer else -delta
                total_paid_bal = delta if is_initiator_new_payer else 0
                total_received_bal = 0 if is_initiator_new_payer else delta
            else:
                amount_owed = new_amt + old_amt if is_initiator_new_payer else -(new_amt + old_amt)
                total_paid_bal = new_amt if is_initiator_new_payer else -old_amt
                total_received_bal = -old_amt if is_initiator_new_payer else new_amt

            modification_balance_map[k] = {
                'initiator': all_users_map.get(k[0]),
                'participant': all_users_map.get(k[1]),
                'increase_balance': amount_owed,
                'increase_transaction_count': 0,
                'increase_total_amount_paid': total_paid_bal,
                'increase_total_amount_received': total_received_bal
            }
        return modification_balance_map

    def bulk_update_user_balance(self, balance_changes):
        """Update the UserBalance in bulk based on the accumulated balance changes."""
        with transaction.atomic():
            initiator_ids = [key[0] for key in balance_changes]
            participant_ids = [key[1] for key in balance_changes]

            existing_balances = {
                (bal.initiator.id, bal.participant.id): bal
                for bal in UserBalance.objects.filter(
                    initiator_id__in=initiator_ids, participant_id__in=participant_ids
                )
            }

            updates = []
            inserts = []

            for key, changes in balance_changes.items():
                initiator_id, participant_id = key
                balance_record = existing_balances.get((initiator_id, participant_id))

                if balance_record:
                    balance_record.balance += changes['increase_balance']
                    balance_record.total_amount_paid += changes['increase_total_amount_paid']
                    balance_record.total_amount_received += changes['increase_total_amount_received']
                    balance_record.transaction_count += changes['increase_transaction_count']
                    balance_record.last_transaction_date = timezone.now()
                    updates.append(balance_record)
                else:
                    new_balance = UserBalance(
                        initiator=changes['initiator'],
                        participant=changes['participant'],
                        balance=changes['increase_balance'],
                        total_amount_paid=changes['increase_total_amount_paid'],
                        total_amount_received=changes['increase_total_amount_received'],
                        transaction_count=changes['increase_transaction_count'],
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
                    updates,
                    ['balance', 'total_amount_paid', 'total_amount_received',
                     'transaction_count', 'last_transaction_date']
                )
                updated_records = updates
            else:
                updated_records = []

            all_records = list(chain(created_records, updated_records))
            filtered_records = [r for r in all_records if r.initiator != r.participant]
            return filtered_records

    def update(self, instance, validated_data):
        old_payer = instance.payer
        payer = validated_data.get('payer', instance.payer)
        group = validated_data.get('group')
        total_amount = validated_data.get('total_amount', instance.total_amount)
        description = validated_data.get('description', instance.description)
        transaction_type = validated_data.get('transaction_type', instance.transaction_type)
        transaction_date = validated_data.get('transaction_date', instance.transaction_date)

        split_details = validated_data.get('split_details', [])
        split_details = TransactionHelper.transform_split_data(split_details)

        user = self.context.get('user') or getattr(self.context.get('request'), 'user', None)
        initial_user_id = getattr(user, 'id', None)

        # Ownership check
        if initial_user_id not in instance.allowed_to_modify_transaction():
            Helper.raise_validation_error("ERR_NOT_OWNER")

        old_payer_id = old_payer.id
        new_payer_id = payer.id

        # Grab old participants
        old_split_details = []
        old_participant_qs = instance.transactionparticipant_set.values('user_id', 'amount_owed')
        for detail in old_participant_qs:
            old_split_details.append({'amount': float(detail['amount_owed']), 'user': int(detail['user_id'])})
        old_split_details = TransactionHelper.transform_split_data(old_split_details)

        # Update instance fields
        instance.payer = payer
        instance.group = group
        instance.total_amount = total_amount
        instance.description = description
        instance.transaction_type = transaction_type
        instance.transaction_date = transaction_date
        instance.split_count = len(split_details)
        instance.updated_at = datetime.now()

        existing_participants = {
            p.user_id: p for p in instance.transactionparticipant_set.all()
        }
        new_user_map = {split['user']: split['amount'] for split in split_details}

        # Create or update participants
        for user_id, amount in new_user_map.items():
            if user_id in existing_participants:
                # Update if changed
                participant_obj = existing_participants[user_id]
                if participant_obj.amount_owed != amount:
                    participant_obj.amount_owed = amount
                    participant_obj.save()
                del existing_participants[user_id]
            else:
                # New participant
                TransactionParticipant.objects.create(
                    transaction=instance,
                    user=get_object_or_404(User, id=user_id),
                    amount_owed=amount
                )
        balance_changes = self.accumulate_balance_changes(new_payer_id, old_payer_id, split_details, old_split_details)

        self.bulk_update_user_balance(balance_changes)

        set_custom_context('exclude_user', user.id)
        instance.save()
        clear_custom_context()
        return instance


class BulkTransactionSerializer(serializers.Serializer):
    transaction_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False
    )
