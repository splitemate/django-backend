# Generated by Django 5.0.11 on 2025-02-05 01:30

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('group', '0001_initial'),
        ('transaction', '0003_remove_transactionparticipant_amount_paid_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_type', models.CharField(choices=[('added_transaction', 'Added a Transaction'), ('friend_request', 'Sent a Friend Request'), ('added_to_group', 'Added to Group'), ('modified_transaction', 'Modified a Transaction'), ('deleted_transaction', 'Deleted a Transaction'), ('settled_amount', 'Settled the Amount')], max_length=50)),
                ('comments', models.JSONField(blank=True, null=True)),
                ('datetime', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='group.group')),
                ('related_users', models.ManyToManyField(blank=True, related_name='related_activities', to=settings.AUTH_USER_MODEL)),
                ('transaction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='transaction.transaction')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-datetime'],
            },
        ),
    ]
