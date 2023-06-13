import os

from django.db import models

from festivals.config import Config


def common_data_dir():
    return os.path.expanduser(f'~/{Config().config["Paths"]["CommonDataDirectory"]}')


def cities_path():
    return os.path.join(common_data_dir(), 'cities.csv')


def theaters_path():
    return os.path.join(common_data_dir(), 'theaters.csv')


def screens_path():
    return os.path.join(common_data_dir(), 'screens.csv')


class City(models.Model):
    """
    City table, a city groups theaters.
    """

    # Define the fields.
    city_id = models.IntegerField(unique=True, null=False)
    name = models.CharField(max_length=256, null=False, blank=False)
    country = models.CharField(max_length=256, null=False, blank=False)

    # Define a manager.
    cities = models.Manager()

    class Meta:
        db_table = 'cities'
        unique_together = ('name', 'country')

    def __str__(self):
        return f'{self.name}'


class Theater(models.Model):
    """
    Theaters, provide screens.
    """
    class Priority(models.IntegerChoices):
        NO_GO = 0
        LOW = 1
        HIGH = 2

    # Define the fields.
    theater_id = models.IntegerField(unique=True, null=False)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    parse_name = models.CharField(max_length=64, null=False, blank=False)
    abbreviation = models.CharField(max_length=10, null=False, blank=False)
    priority = models.IntegerField(choices=Priority.choices)

    # Define a manager.
    theaters = models.Manager()

    class Meta:
        db_table = 'theaters'
        unique_together = ('city', 'abbreviation')

    def __str__(self):
        return f'{self.abbreviation} {self.city.name}'
