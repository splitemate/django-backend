from django.db.models.signals import post_save, post_delete
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

@receiver(post_delete, sender=Group)
def track_group_deletion(sender, instance, **kwargs):
    Activity.objects.create(
        user_id=instance.created_by,
        activity_type=ActivityType.GROUP_DELETED,
        comments={"message": f"Group '{instance.group_name}' was deleted"},
    )
