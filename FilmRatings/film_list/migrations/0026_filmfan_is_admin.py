# Generated by Django 3.2.9 on 2022-07-15 19:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('film_list', '0025_auto_20220714_1655'),
    ]

    operations = [
        migrations.AddField(
            model_name='filmfan',
            name='is_admin',
            field=models.BooleanField(default=False),
        ),
    ]