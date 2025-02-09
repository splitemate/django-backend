from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from group.models import Group, GroupParticipant
from activity.models import Activity, ActivityType


@receiver(post_save, sender=GroupParticipant)
def track_participant_addition(sender, instance, created, **kwargs):
    if created:
        group_members = instance.get_group_members()
        activity = Activity.objects.create(
            user_id=instance.user,
            activity_type=ActivityType.ADDED_TO_GROUP,
            group_id=instance.group,
            comments={"message": f"{instance.user.email} was added to the group '{instance.group.group_name}'"},
        )
        activity.related_users_ids.add(*set(group_members))


@receiver(pre_delete, sender=GroupParticipant)
def track_participant_removal(sender, instance, **kwargs):
    group_members = instance.group.get_group_members()
    activity = Activity.objects.create(
        user_id=instance.user,
        activity_type=ActivityType.REMOVED_FROM_GROUP,
        group_id=instance.group,
        comments={"message": f"{instance.user.email} was removed from the group '{instance.group.group_name}'"},
    )
    activity.related_users_ids.add(*set(group_members))


@receiver(pre_save, sender=Group)
def capture_old_group_state(sender, instance, **kwargs):
    """Capture the previous state of is_active before saving."""
    try:
        old_instance = sender.all_objects.get(pk=instance.pk)
        instance._old_is_active = old_instance.is_active
        instance._old_group_members = old_instance.get_group_members()
    except sender.DoesNotExist:
        instance._old_is_active = None


@receiver(post_save, sender=Group)
def handle_group_activation_change(sender, instance, created, **kwargs):
    """Handle actions when a group is reactivated from a soft delete."""

    if not created:
        old_is_active = getattr(instance, "_old_is_active", None)
        old_group_members = getattr(instance, "_old_group_members", None)
        new_group_members = instance.get_group_members()
        related_user_ids = set(old_group_members or []) | set(new_group_members or [])

        if old_is_active is False and instance.is_active:
            activity = Activity.objects.create(
                user_id=instance.created_by,
                activity_type=ActivityType.GROUP_RESTORED,
                group_id=instance,
                comments={"message": f"Group '{instance.group_name}' was restored."},
            )
            activity.related_users_ids.add(*related_user_ids)

        elif old_is_active is True and not instance.is_active:
            instance.participants.clear()
            activity = Activity.objects.create(
                user_id=instance.created_by,
                activity_type=ActivityType.GROUP_DELETED,
                group_id=instance,
                comments={"message": f"Group '{instance.group_name}' was deleted."},
            )
            activity.related_users_ids.add(*related_user_ids)
    else:
        activity = Activity.objects.create(
            user_id=instance.created_by,
            activity_type=ActivityType.GROUP_CREATED,
            group_id=instance,
            comments={"message": f"{instance.created_by.email} created the group '{instance.group_name}'"},
        )
        related_user_ids = set(instance.get_group_members())
        activity.related_users_ids.add(*related_user_ids)
