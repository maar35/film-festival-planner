# Generated by Django 3.2.9 on 2022-06-13 16:13

from django.db import migrations, models
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('festivals', '0004_auto_20220613_1325'),
    ]

    operations = [
        migrations.CreateModel(
            name='FestivalBase',
            fields=[
                ('mnemonic', models.CharField(max_length=10, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=40)),
            ],
            options={
                'db_table': 'film_festival_base',
            },
            managers=[
                ('festival_bases', django.db.models.manager.Manager()),
            ],
        ),
    ]