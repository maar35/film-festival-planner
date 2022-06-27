# Generated by Django 3.2.9 on 2022-06-24 10:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('festivals', '0010_festivalbase_picture_url'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='festivalbase',
            name='picture_url',
        ),
        migrations.AddField(
            model_name='festivalbase',
            name='image',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
