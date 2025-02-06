from django.db import models
from django.conf import settings
from group.models import Group
from transaction.models import Transaction


class ActivityType(models.TextChoices):
    ADDED_YOU_AS_FRIEND = "added_you_as_friend", "Added you as a Friend"
    REMOVED_YOU_AS_FRIEND = "removed_you_as_friend", "Removed you as a Friend"
    GROUP_CREATED = "group_created", "Group Created"
    GROUP_DELETED = "group_deleted", "Group Deleted"
    GROUP_RESTORED = "group_restored", "Group Restored"
    ADDED_TO_GROUP = "added_to_group", "Added to Group"
    REMOVED_FROM_GROUP = "removed_from_group", "Removde from Group"
    ADDED_TRANSACTION = "added_transaction", "Added a Transaction"
    MODIFIED_TRANSACTION = "modified_transaction", "Modified a Transaction"
    DELETED_TRANSACTION = "deleted_transaction", "Deleted a Transaction"
    RESTORED_TRANSACTION = "restored_transaction", "Restored a Transaction"
    SETTLED_AMOUNT = "settled_amount", "Settled the Amount"


class Activity(models.Model):
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activities")
    related_users_ids = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="related_activities", blank=True)
    group_id = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_id = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    activity_type = models.CharField(max_length=50, choices=ActivityType.choices)
    comments = models.JSONField(blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)

    def generate_explanation(self):
        """Generates a human-readable explanation based on JSON changes"""
        if self.activity_type != "modified_transaction" or not self.comments:
            return ""

        old_data = self.comments.get("old", {})
        new_data = self.comments.get("new", {})
        messages = []

        if "amount" in old_data and "amount" in new_data and old_data["amount"] != new_data["amount"]:
            messages.append(f"Amount changed from {old_data['amount']} to {new_data['amount']}.")

        if "payer" in old_data and "payer" in new_data and old_data["payer"] != new_data["payer"]:
            messages.append(f"Payer changed from User {old_data['payer']} to User {new_data['payer']}.")

        if "participants" in old_data and "participants" in new_data:
            old_participants = set(old_data["participants"])
            new_participants = set(new_data["participants"])

            added = new_participants - old_participants
            removed = old_participants - new_participants

            if removed:
                messages.append(f"Participants removed: {', '.join(map(str, removed))}.")
            if added:
                messages.append(f"Participants added: {', '.join(map(str, added))}.")

        return " ".join(messages)

    class Meta:
        ordering = ["-created_date"]

    def __str__(self):
        return f"{self.user_id} - {self.activity_type} at {self.created_date}"
