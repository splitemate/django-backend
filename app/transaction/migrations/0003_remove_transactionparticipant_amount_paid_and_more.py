# Generated by Django 5.0.8 on 2024-09-28 16:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transaction', '0002_userbalance'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transactionparticipant',
            name='amount_paid',
        ),
        migrations.RemoveField(
            model_name='transactionparticipant',
            name='is_settled',
        ),
    ]
