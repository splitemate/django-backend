from django.db import models
from django.conf import settings


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
