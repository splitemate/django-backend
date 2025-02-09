from django.db.models.signals import m2m_changed
from asgiref.sync import async_to_sync
from django.dispatch import receiver
from channels.layers import get_channel_layer
from activity.models import Activity, ActivityType
from transaction.utils import TransactionHelper
from core.context import get_custom_context


@receiver(m2m_changed, sender=Activity.related_users_ids.through)
def track_activity_creation(sender, instance, action, pk_set, **kwargs):
    if action != "post_add":
        return
    exclude_user = get_custom_context('exclude_user')
    exclude_user = str(exclude_user) if exclude_user else None
    associated_members = instance.related_users_ids.all().values_list('id', flat=True)

    channel_layer = get_channel_layer()
    if instance.activity_type in [ActivityType.ADDED_TRANSACTION, ActivityType.MODIFIED_TRANSACTION, ActivityType.DELETED_TRANSACTION, ActivityType.RESTORED_TRANSACTION]:
        for user_id in associated_members:
            if exclude_user and exclude_user == str(user_id):
                continue
            transaction_data = TransactionHelper.get_transaction_ws_data(instance.transaction_id, user_id)
            data = {
                'type': 'transaction_message',
                'data': transaction_data
            }
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                data
            )

    elif instance.activity_type in [ActivityType.ADDED_YOU_AS_FRIEND, ActivityType.REMOVED_YOU_AS_FRIEND]:
        for user_id in associated_members:
            if user_id == instance.user_id.id:
                continue
            user = instance.user_id
            data = {
                'type': 'transaction_message',
                'data': {
                    "type": instance.activity_type,
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "image_url": user.image_url
                    },
                    "message": instance.comments.get('message')
                }
            }
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                data
            )

    elif instance.activity_type in [ActivityType.ADDED_TO_GROUP, ActivityType.REMOVED_FROM_GROUP, ActivityType.GROUP_CREATED, ActivityType.GROUP_DELETED, ActivityType.GROUP_RESTORED]:
        group_details = instance.group_id.get_group_ws_data()
        group_members = instance.group_id.get_group_members()
        participants = instance.user_id.get_users_details(group_members)
        for user_id in associated_members:
            data = {
                'type': 'transaction_message',
                'data': {
                    "type": instance.activity_type,
                    "group_details": group_details,
                    "message": instance.comments.get('message'),
                    "participant_details": participants
                }
            }
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                data
            )
