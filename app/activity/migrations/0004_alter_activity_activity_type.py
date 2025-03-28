# Generated by Django 5.0.11 on 2025-02-05 18:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0003_alter_activity_activity_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='activity_type',
            field=models.CharField(choices=[('added_you_as_friend', 'Added you as a Friend'), ('removed_you_as_friend', 'Removed you as a Friend'), ('group_created', 'Group Created'), ('group_deleted', 'Group Deleted'), ('added_to_group', 'Added to Group'), ('removed_from_group', 'Removde from Group'), ('added_transaction', 'Added a Transaction'), ('modified_transaction', 'Modified a Transaction'), ('deleted_transaction', 'Deleted a Transaction'), ('settled_amount', 'Settled the Amount')], max_length=50),
        ),
    ]
