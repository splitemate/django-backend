from django.db import models
from django.conf import settings
from core.models import ActiveManager


class GroupType(models.TextChoices):
    OTHER = 'other', 'Other'
    TRIP = 'trip', 'Trip'
    ROOMMATES = 'roommates', 'Roommates'
    COUPLE = 'couple', 'Couple'
    FAMILY = 'family', 'Family'
    INVESTMENT = 'investment', 'Investment'
    WORK = 'work', 'Work/Office'


class Group(models.Model):
    is_active = models.BooleanField(default=True)
    group_name = models.CharField(max_length=100, verbose_name='Name')
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name='Description')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Created By')
    group_type = models.CharField(choices=GroupType.choices, verbose_name='Group Type')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, through='GroupParticipant', related_name='groups_participated')

    objects = ActiveManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        """Soft delete instead of actual delete"""
        self.is_active = False
        self.save()

    def restore(self):
        """Restore a soft-deleted group"""
        self.is_active = True
        self.save()

    def get_group_members(self):
        return list(GroupParticipant.objects.filter(group=self).values_list('user_id', flat=True))

    def get_group_ws_data(self):
        return {
            'id': str(self.id),
            'group_name': self.group_name,
            'description': self.description,
            'created_by': str(self.created_by.id),
            'group_type': self.group_type,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    def __str__(self):
        return self.group_name


class GroupRole(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    USER = 'user', 'User'


class GroupParticipant(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(choices=GroupRole.choices, verbose_name='Role')

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user} in {self.group} as {self.role}"
