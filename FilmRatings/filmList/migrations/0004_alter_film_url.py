# Generated by Django 3.2.9 on 2022-05-29 21:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filmList', '0003_auto_20220529_2351'),
    ]

    operations = [
        migrations.AlterField(
            model_name='film',
            name='url',
            field=models.URLField(default='https://moviesthatmatter.nl/festival/film/107-mothers/'),
            preserve_default=False,
        ),
    ]