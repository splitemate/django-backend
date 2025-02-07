# Generated by Django 5.0.12 on 2025-02-07 17:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0001_initial'),
        ('transaction', '0005_transactionparticipant_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='transactionparticipant',
            name='is_transaction_sattled',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='group.group'),
        ),
    ]
