# Generated by Django 3.2.9 on 2022-06-01 16:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('filmList', '0013_auto_20220531_2118'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='filmfan',
            name='id',
        ),
        migrations.AlterField(
            model_name='filmfan',
            name='name',
            field=models.CharField(max_length=16, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='filmfanfilmrating',
            name='film_fan',
            field=models.ForeignKey(db_column='name', on_delete=django.db.models.deletion.CASCADE, to='filmList.filmfan'),
        ),
        migrations.AlterUniqueTogether(
            name='filmfanfilmrating',
            unique_together={('film', 'film_fan')},
        ),
    ]