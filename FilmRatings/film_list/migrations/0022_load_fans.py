# Generated by Django 3.2.9 on 2022-06-19 11:59

from django.db import migrations


def add_film_fans(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version.
    film_fan_class = apps.get_model("film_list", "FilmFan")
    db_alias = schema_editor.connection.alias
    film_fan_class.film_fans.using(db_alias).bulk_create([
        film_fan_class(name="Maarten", seq_nr=1),
        film_fan_class(name="Adrienne", seq_nr=2),
        film_fan_class(name="Manfred", seq_nr=3),
        film_fan_class(name="Piggel", seq_nr=4),
        film_fan_class(name="Rijk", seq_nr=5),
    ])


def revert_add_fim_fans(apps, schema_editor):
    # add_film_fans() creates 5 FilmFan instances,
    # so revert_add_fim_fans() should delete them.
    film_fan_class = apps.get_model("film_list", "FilmFan")
    db_alias = schema_editor.connection.alias
    seq_nr = 0
    for name in ["Maarten", "Adrienne", "Manfred", "Piggel", "Rijk"]:
        seq_nr += 1
        film_fan_class.film_fans.using(db_alias).filter(name=name, seq_nr=seq_nr).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('film_list', '0021_alter_filmfanfilmrating_film_fan'),
    ]

    operations = [
        migrations.RunPython(add_film_fans, revert_add_fim_fans)
    ]
