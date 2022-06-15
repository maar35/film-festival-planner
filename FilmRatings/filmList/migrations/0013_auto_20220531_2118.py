# Generated by Django 3.2.9 on 2022-05-31 19:18

from django.db import migrations
from FilmRatings import tools


def add_film_ratings(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version.
    fan_rating_class = apps.get_model("filmList", "FilmFanFilmRating")
    db_alias = schema_editor.connection.alias
    # fan_ratings = tools.Festival('MTMF', 2022).read_ratings(fan_rating_class)
    fan_ratings = []
    fan_rating_class.fan_ratings.using(db_alias).bulk_create(fan_ratings)


class Migration(migrations.Migration):

    dependencies = [
        ('filmList', '0012_rename_film_id_filmfanfilmrating_film'),
    ]

    operations = [
        migrations.RunPython(add_film_ratings)
    ]