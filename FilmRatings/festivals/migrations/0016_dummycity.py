# Generated by Django 3.2.9 on 2023-05-29 14:01

from django.db import migrations, models
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('festivals', '0015_cityproxy'),
    ]

    operations = [
        migrations.CreateModel(
            name='DummyCity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city_id', models.IntegerField(unique=True)),
                ('name', models.CharField(max_length=256)),
                ('country', models.CharField(max_length=256)),
            ],
            options={
                'db_table': 'dummy_cities',
                'unique_together': {('name', 'country')},
            },
            managers=[
                ('cities', django.db.models.manager.Manager()),
            ],
        ),
    ]
