# Generated by Django 3.2.9 on 2022-05-29 21:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filmList', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='film',
            name='id',
        ),
        migrations.AlterField(
            model_name='film',
            name='film_id',
            field=models.IntegerField(primary_key=True, serialize=False),
        ),
    ]
