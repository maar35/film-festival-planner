# Generated by Django 3.2.9 on 2023-05-28 21:16

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('theaters', '0010_delete_theater'),
    ]

    operations = [
        migrations.CreateModel(
            name='Theater',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('theater_id', models.IntegerField(unique=True)),
                ('parse_name', models.CharField(max_length=64)),
                ('abbreviation', models.CharField(max_length=10)),
                ('priority', models.IntegerField(choices=[(0, 'No Go'), (1, 'Low'), (2, 'High')])),
                ('city', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='theaters.city')),
            ],
            options={
                'db_table': 'theaters',
                'unique_together': {('city', 'abbreviation')},
            },
            managers=[
                ('theaters', django.db.models.manager.Manager()),
            ],
        ),
    ]
