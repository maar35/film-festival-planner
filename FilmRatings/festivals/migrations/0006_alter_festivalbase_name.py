# Generated by Django 3.2.9 on 2022-06-13 16:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('festivals', '0005_festivalbase'),
    ]

    operations = [
        migrations.AlterField(
            model_name='festivalbase',
            name='name',
            field=models.CharField(max_length=60),
        ),
    ]
