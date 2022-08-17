# Generated by Django 3.2.9 on 2022-08-06 19:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('film_list', '0028_auto_20220806_2025'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='filmfanfilmrating',
            name='film',
        ),
        migrations.AddField(
            model_name='filmfanfilmrating',
            name='film',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.CASCADE, to='film_list.film'),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='filmfanfilmrating',
            unique_together={('film', 'film_fan')},
        ),
    ]