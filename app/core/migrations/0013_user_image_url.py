# Generated by Django 5.0.9 on 2025-01-18 14:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_alter_user_user_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='image_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
    ]
