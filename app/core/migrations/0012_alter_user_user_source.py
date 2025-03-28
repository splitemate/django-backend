# Generated by Django 5.0.8 on 2024-09-22 06:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_user_user_source'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='user_source',
            field=models.CharField(choices=[('standard', 'Standard'), ('google', 'Google')], default='standard', help_text="Indicates the source of the user registration (e.g., 'google').", max_length=10, verbose_name='User Source'),
        ),
    ]
