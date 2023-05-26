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
    id = models.IntegerField(primary_key=True, serialize=False)
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
    id = models.IntegerField(primary_key=True, serialize=False)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    parse_name = models.CharField(max_length=64, null=False, blank=False)
    abbreviation = models.CharField(max_length=10, null=False, blank=False)
    priority = models.IntegerField(choices=Priority.choices)

    # Define a manager.
    theaters = models.Manager()

    class Meta:
        db_table = 'theaters'
        unique_together = ('city_id', 'abbreviation')

    def __str__(self):
        return f'{self.abbreviation} {self.city.name}'


class Screen(models.Model):
    """
    Screen, used to display a film on.
    """
    class ScreenAddressType(models.IntegerChoices):
        LOCATION = 3
        ONDEMAND = 2
        ONLINE = 1

    # Define the fields.
    id = models.IntegerField(primary_key=True, serialize=False)
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    parse_name = models.CharField(max_length=64, null=False, blank=False)
    abbreviation = models.CharField(max_length=8, null=True, blank=False)
    address_type = models.IntegerField(choices=ScreenAddressType.choices)

    # Define a manager.
    screens = models.Manager()

    class Meta:
        db_table = 'screens'

    def __str__(self):
        return f'{self.theater.abbreviation}{self.abbreviation}'
