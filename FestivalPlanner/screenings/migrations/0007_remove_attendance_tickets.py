# Generated by Django 4.2.8 on 2025-04-09 14:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('screenings', '0006_ticket_ticket_unique_screening_fan'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='attendance',
            name='tickets',
        ),
    ]
