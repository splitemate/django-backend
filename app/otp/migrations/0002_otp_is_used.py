# Generated by Django 5.0.7 on 2024-08-04 12:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('otp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='otp',
            name='is_used',
            field=models.BooleanField(default=False),
        ),
    ]
