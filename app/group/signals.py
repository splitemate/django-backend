from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from group.models import Group, GroupParticipant
from activity.models import Activity, ActivityType


@receiver(post_save, sender=Group)
def track_group_creation(sender, instance, created, **kwargs):
    if created:
        Activity.objects.create(
            user_id=instance.created_by,
            activity_type=ActivityType.GROUP_CREATED,
            group_id=instance,
            comments={"message": f"{instance.created_by.email} created the group '{instance.group_name}'"},
        )


@receiver(post_save, sender=GroupParticipant)
def track_participant_addition(sender, instance, created, **kwargs):
    if created:
        Activity.objects.create(
            user_id=instance.user,
            activity_type=ActivityType.ADDED_TO_GROUP,
            group_id=instance.group,
            comments={"message": f"{instance.user.email} was added to the group '{instance.group.group_name}'"},
        )


@receiver(post_delete, sender=GroupParticipant)
def track_participant_removal(sender, instance, **kwargs):
    Activity.objects.create(
        user_id=instance.user,
        activity_type=ActivityType.REMOVED_FROM_GROUP,
        group_id=instance.group,
        comments={"message": f"{instance.user.email} was removed from the group '{instance.group.group_name}'"},
    )


@receiver(pre_save, sender=Group)
def capture_old_group_state(sender, instance, **kwargs):
    """Capture the previous state of is_active before saving."""
    try:
        old_instance = sender.all_objects.get(pk=instance.pk)
        instance._old_is_active = old_instance.is_active
    except sender.DoesNotExist:
        instance._old_is_active = None


@receiver(post_save, sender=Group)
def handle_group_activation_change(sender, instance, created, **kwargs):
    """Handle actions when a group is reactivated from a soft delete."""
    print("Group activation change signal received")

    if not created:
        print("Group activation change signal is an update")
        old_is_active = getattr(instance, "_old_is_active", None)

        print(f"Old instance: {old_is_active}, New instance: {instance.is_active}")

        if old_is_active is False and instance.is_active:
            print("Group was restored")
            Activity.objects.create(
                user_id=instance.created_by,
                activity_type=ActivityType.GROUP_RESTORED,
                group_id=instance,
                comments={"message": f"Group '{instance.group_name}' was restored."},
            )

        elif old_is_active is True and not instance.is_active:
            print("Group was deleted")
            instance.participants.clear()
            Activity.objects.create(
                user_id=instance.created_by,
                activity_type=ActivityType.GROUP_DELETED,
                group_id=instance,
                comments={"message": f"Group '{instance.group_name}' was deleted."},
            )
