from django.forms.models import model_to_dict
from channels.layers import get_channel_layer
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from copy import deepcopy
from asgiref.sync import async_to_sync
from app.response_codes import RESPONSE_CODES
from rest_framework.exceptions import ValidationError
from transaction.models import UserBalance


class Helper:

    @staticmethod
    def get_tokens_for_user(user) -> dict:
        """Generate Tokens manually"""

        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    @staticmethod
    def transform_split_data(data) -> list:
        transformed_data = []

        for item in data:
            transformed_item = {
                'user': int(item['user']),
                'amount': Decimal(item['amount']),
            }
            transformed_data.append(transformed_item)

        return transformed_data

    @staticmethod
    def raise_validation_error(error_key, extra_data=None):
        """
        Raises a ValidationError with structured error data.
        """
        error_info = RESPONSE_CODES.get(error_key, {})
        error_data = {
            "status": "failure",
            "error_code": error_info.get("code"),
            "response_key": error_key,
            "description": error_info.get("message")
        }
        if extra_data:
            sanitized_extra_data = {key: str(value) for key, value in extra_data.items()}
            error_data.update(sanitized_extra_data)
        raise ValidationError(error_data)

    @staticmethod
    def format_error_response(error_key, extra_data=None):
        """
        Returns a structured error response dictionary.
        """
        error_info = RESPONSE_CODES.get(error_key, {})
        response_code = error_info.get("code")
        error_data = {
            "status": "failure" if response_code.startswith("E") else "success",
            "is_success": False if response_code.startswith("E") else True,
            "response_code": response_code,
            "response_key": error_key,
            "description": error_info.get("message")
        }
        if extra_data:
            sanitized_extra_data = {key: str(value) for key, value in extra_data.items()}
            error_data.update(sanitized_extra_data)
        return error_data

    @staticmethod
    def get_group_data(group):
        """
        Returns a dictionary representation of a group object.

        Args:
            group (Object): The group object to be converted. This should be a Django model instance.

        Returns:
            dict: A dictionary representation of the group object.
        """
        data = model_to_dict(group)
        data['id'] = str(data.get('id', ''))
        data['created_by'] = str(data.get('created_by', ''))
        data['created_at'] = group.created_at.isoformat()
        data['updated_at'] = group.updated_at.isoformat()
        data.pop('participants', None)
        return data

    @staticmethod
    def pre_process_user_balance(filtered_records) -> dict:
        """
        Processes and categorizes user balances based on the transaction records.

        Parameters:
            filtered_records (Object): A object of UserBalance.
            payer_id (str): Payer Id of transaction

        Returns:
            dict: A dictionary where each user ID is a key and the value is another list of dictonary
                containing their balance , id, name, email.

        Purpose:
            This method is used to compute and set user balances based on transactions,
            ensuring each user's role in the transaction is clearly defined.
            Assist to create Ledger structure for app.
        """
        user_balances = {}

        for record in filtered_records:
            initiator = record.initiator
            participant = record.participant
            balance = record.balance

            initiator_id = str(initiator.id)
            participant_id = str(participant.id)

            if initiator_id not in user_balances:
                user_balances[initiator_id] = []
            user_balances[initiator_id].append({
                'id': participant_id,
                'name': participant.name,
                'email': participant.email,
                'balance': float(balance),
                'image_url': participant.image_url,
            })

            if participant_id not in user_balances:
                user_balances[participant_id] = []
            user_balances[participant_id].append({
                'id': initiator_id,
                'name': initiator.name,
                'email': initiator.email,
                'balance': -float(balance),
                'image_url': initiator.image_url,
            })

        return user_balances

    def convert_to_transaction_dict(transaction_obj, split_details, detail_split_details) -> dict:
        """
        Converts a transaction object into a dictionary representation.

        Args:
            transaction_obj (object): The transaction object to be converted. This should be a Django model instance.
            split_details (list): A list of dictionaries containing user and their respective split amounts.
            detail_split_details (list): A list of dictionaries containing detailed split information, which will be modified with amounts.

        Returns:
            dict: A dictionary representation of the transaction object with the following modifications:
                - `total_amount` field is converted to a float.
                - `transaction_date` is converted to ISO 8601 string format.
                - `id`, `payer`, and `group` fields are converted to strings.
                - The split details in `detail_split_details` are updated with respective amounts from `split_details`.
        """
        detail_split_details_copy = deepcopy(detail_split_details)

        # Add payer to split detail balance will be updated in next step
        detail_split_details_copy.append({
            'id': str(transaction_obj.payer.id),
            'name': transaction_obj.payer.name,
            'email': transaction_obj.payer.email,
            'image_url': transaction_obj.payer.image_url,
            'balance': 0.0,
        })
        split_details_map = {str(item["user"]): float(item["amount"]) for item in split_details}
        for detail in detail_split_details_copy:
            detail.pop("balance", None)
            detail["amount"] = split_details_map.get(detail["id"], 0.0)

        data = model_to_dict(transaction_obj)
        data['total_amount'] = float(data.get('total_amount', ''))
        data['transaction_date'] = data.get('transaction_date', '').isoformat()
        data['id'] = str(data.get('id', ''))
        data['payer'] = str(data.get('payer', ''))
        data['group'] = str(data.get('group', '')) if data.get('group', '') else None
        data['created_by'] = str(data.get('created_by', ''))
        data['created_at'] = transaction_obj.created_at.isoformat()
        data['updated_at'] = transaction_obj.updated_at.isoformat()
        return data, detail_split_details_copy

    @staticmethod
    def broadcast_transaction_message(model, method, transaction_obj, exclude_user, ledger_dict, split_details):
        """
        Broadcasts a transaction message to relevant users.

        Args:
            model (str): The model name.
            method (str): The method triggering the broadcast.
            transaction_data (Object): Transaction object.
            exclude_user (User): The user to exclude from notifications.
            ledger_dict (dict): A dictionary of all user ledger data.
        """
        payer_id = str(transaction_obj.payer.id)
        detail_split_details = ledger_dict.get(payer_id)
        transaction_dict, detail_split_details_copy = Helper.convert_to_transaction_dict(transaction_obj=transaction_obj, split_details=split_details, detail_split_details=detail_split_details)
        exclude_user_id = str(exclude_user.id) if exclude_user else None
        exclude_user_id_set = {exclude_user_id} if exclude_user_id else set()
        group_details = {}

        if transaction_obj.group:
            group = transaction_obj.group
            group_details = Helper.get_group_data(group)

        channel_layer = get_channel_layer()
        for split in split_details:
            user_id = str(split.get('user', ''))
            if user_id in exclude_user_id_set:
                continue

            ledgers = ledger_dict.get(str(user_id))
            user_total_balance = UserBalance.get_user_balance(user_id)

            data = {
                **transaction_dict,
                'method': method,
                'split_details': detail_split_details_copy,
                'ledger_balance': ledgers,
                'group_details': group_details,
                'user_total_balance': user_total_balance
            }

            final_data = {
                'type': 'transaction_message',
                'model': model,
                'data': data
            }

            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                final_data
            )
