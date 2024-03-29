# Generated by Django 3.2.9 on 2022-05-30 19:48

from django.db import migrations
import csv
import os
import datetime

planner_dir = os.path.expanduser("~/Documents/Film/MTMF/MTMF2022/_planner_data")
films_file = os.path.join(planner_dir, "films.csv")


def add_films(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version.
    film_class = apps.get_model("film_list", "Film")
    db_alias = schema_editor.connection.alias
    films = []
    in_header = True
    with open(films_file, newline='') as csvfile:
        film_reader = csv.reader(csvfile, delimiter=';', quotechar='"')
        film_reader.__next__()
        for row in film_reader:
            seq_nr = int(row[0])
            film_id = int(row[1])
            film = film_class(film_id=film_id, seq_nr=seq_nr)
            film.sort_title = row[2]
            film.title = row[3]
            film.title_language = row[4]
            film.section = row[5]
            film.duration = datetime.timedelta(minutes=int(row[6].rstrip("′")))
            film.medium_category = row[7]
            film.url = row[8]
            films.append(film)

    film_class.objects.using(db_alias).bulk_create(films)


def revert_add_films(apps, schema_editor):
    # add_films() reads all Film instances into the database,
    # so revert_add_films() should delete them.
    film_class = apps.get_model("film_list", "Film")
    db_alias = schema_editor.connection.alias
    for film in film_class.films.all():
        film_class.objects.using(db_alias).filter(film_id=film.film).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('film_list', '0007_auto_20220530_1843'),
    ]

    # Operation commented out in order to get a working test database.
    operations = [
        # migrations.RunPython(add_films, revert_add_films)
    ]
