# Generated by Django 3.2.9 on 2022-07-28 21:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('festivals', '0013_festival_festival_color'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='festival',
            name='border_color',
        ),
    ]
