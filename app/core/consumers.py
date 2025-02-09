"""
Consumer for transaction
"""
import json
from rest_framework.exceptions import ValidationError
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from transaction.models import Transaction
from transaction.serializers import AddTransactionSerializer, ModifyTransactionSerializer
from app.helper import Helper


class NotFoundConsumer(AsyncWebsocketConsumer):
    """Disconnect for wrong path"""
    async def connect(self):
        await self.close(code=4040)


class CoreConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user_group_name = f"user_{self.scope["user"].id}"
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)
            await self.accept()
        else:
            await self.close(code=1008)

    async def disconnect(self, close_code):
        if self.scope["user"].is_authenticated:
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def transaction_message(self, event):
        await self.send(text_data=json.dumps({"message": event}))

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data['action'] == 'add_transaction':
            response = await self.handle_add_transaction(data)
            await self.send_response(response)
        elif data['action'] == 'modify_transaction':
            response = await self.handle_modify_transaction(data)
            await self.send_response(response)
        elif data['action'] == 'test':
            await self.send_response({
                "message": {
                    "type": "test",
                    "model": "transaction",
                    "method": "update",
                }
            })

    @sync_to_async
    def handle_add_transaction(self, data):
        try:
            serializer = AddTransactionSerializer(data=data.get('transaction_data', {}), context={'user': self.scope['user']})
            if serializer.is_valid():
                transaction = serializer.save()
                return Helper.format_error_response("SUCCESS_TRANSACTION_CREATED", {"transaction_id": transaction.id})
            else:
                return Helper.format_error_response("ERR_SOMETHING_WENT_WRONG", {"error": serializer.errors})
        except ValidationError as ve:
            error_details = ve.detail
            response_key = error_details.get('response_key', False)
            if response_key:
                return Helper.format_error_response(response_key)
            else:
                return Helper.format_error_response("ERR_SOMETHING_WENT_WRONG", {"error": str(ve)})
        except Exception as e:
            return Helper.format_error_response("ERR_SOMETHING_WENT_WRONG", {"error": str(e)})

    @sync_to_async
    def handle_modify_transaction(self, data):
        try:
            transaction = Transaction.objects.get(pk=data.get('transaction_data', {}).get('id'))
            serializer = ModifyTransactionSerializer(transaction, data=data.get('transaction_data', {}), context={'user': self.scope['user']})
            if serializer.is_valid():
                serializer.save()
                return Helper.format_error_response("SUCCESS_TRANSACTION_MODIFIED")
            return serializer.errors
        except Transaction.DoesNotExist:
            return Helper.format_error_response("ERR_TRANSACTION_NOT_FOUND")
        except ValidationError as ve:
            error_details = ve.detail
            response_key = error_details.get('response_key', False)
            if response_key:
                return Helper.format_error_response(response_key)
            else:
                return Helper.format_error_response("ERR_SOMETHING_WENT_WRONG", {"error": str(ve)})
        except Exception as e:
            return Helper.format_error_response("ERR_SOMETHING_WENT_WRONG", {"error": str(e)})

    async def send_response(self, response):
        await self.send(text_data=json.dumps(response))
