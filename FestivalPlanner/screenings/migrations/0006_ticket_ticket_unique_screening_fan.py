# Generated by Django 4.2.8 on 2025-03-16 23:31

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
        ('screenings', '0005_screening_auto_planned'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('confirmed', models.BooleanField(default=False)),
                ('fan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='authentication.filmfan')),
                ('screening', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='screenings.screening')),
            ],
            options={
                'db_table': 'ticket',
            },
            managers=[
                ('tickets', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AddConstraint(
            model_name='ticket',
            constraint=models.UniqueConstraint(fields=('screening', 'fan'), name='unique_screening_fan'),
        ),
    ]
