# Generated by Django 2.2.5 on 2019-10-25 02:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Users', '0002_auto_20191025_0754'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='number_of_groups',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='number_of_transactions',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='user_privacy',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='user_type',
        ),
    ]
