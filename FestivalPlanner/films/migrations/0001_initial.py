# Generated by Django 3.2.9 on 2023-06-03 14:13

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('festivals', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Film',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('film_id', models.IntegerField()),
                ('seq_nr', models.IntegerField()),
                ('sort_title', models.CharField(max_length=128)),
                ('title', models.CharField(max_length=128)),
                ('title_language', models.CharField(max_length=2)),
                ('subsection', models.CharField(max_length=32, null=True)),
                ('duration', models.DurationField()),
                ('medium_category', models.CharField(max_length=32)),
                ('url', models.URLField()),
                ('festival', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='festivals.festival')),
            ],
            options={
                'db_table': 'film',
                'unique_together': {('festival', 'film_id')},
            },
            managers=[
                ('films', django.db.models.manager.Manager()),
            ],
        ),
    ]