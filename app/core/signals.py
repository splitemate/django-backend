from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from activity.models import Activity, ActivityType

User = get_user_model()


@receiver(m2m_changed, sender=User.friends.through)
def track_friend_changes(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Create a single Activity when a user adds or removes a friend in a symmetrical ManyToManyField.
    """
    if action == "post_add":
        for friend_id in pk_set:
            friend = User.objects.get(pk=friend_id)
            related_users = {instance.id, friend.id}
            activity = Activity.objects.create(
                user_id=instance,
                activity_type=ActivityType.ADDED_YOU_AS_FRIEND,
                comments={"message": f"{instance.email} and {friend.email} are now friends"},
            )
            activity.related_users_ids.add(*related_users)

    elif action == "post_remove":
        for friend_id in pk_set:
            friend = User.objects.get(pk=friend_id)
            related_users = {instance.id, friend.id}
            activity = Activity.objects.create(
                user_id=instance,
                activity_type=ActivityType.REMOVED_YOU_AS_FRIEND,
                comments={"message": f"{instance.email} and {friend.email} are no longer friends"},
            )
            activity.related_users_ids.add(*related_users)
