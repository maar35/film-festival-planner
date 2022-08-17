# Generated by Django 3.2.9 on 2022-08-06 18:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('festivals', '0014_remove_festival_border_color'),
        ('film_list', '0027_film_festival'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='filmfanfilmrating',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='filmfanfilmrating',
            name='film',
        ),
        migrations.AlterField(
            model_name='film',
            name='film_id',
            field=models.IntegerField(),
        ),
        migrations.AddField(
            model_name='film',
            name='id',
            field=models.AutoField(default=0, primary_key=True, serialize=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='filmfanfilmrating',
            name='film',
            field=models.ManyToManyField(to='film_list.Film'),
        ),
        migrations.AlterUniqueTogether(
            name='film',
            unique_together={('festival', 'film_id')},
        ),
    ]
