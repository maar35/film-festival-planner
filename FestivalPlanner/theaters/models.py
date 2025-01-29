import os

from django.db import models

from festivals.config import Config

TEST_COMMON_DATA_DIR = None


def common_data_dir():
    if TEST_COMMON_DATA_DIR:
        _dir = TEST_COMMON_DATA_DIR.name
    else:
        _dir = os.path.expanduser(f'~/{Config().config["Paths"]["CommonDataDirectory"]}')
    return _dir


def clean_common_data_dir():
    if TEST_COMMON_DATA_DIR:
        TEST_COMMON_DATA_DIR.cleanup()


def cities_path():
    return os.path.join(common_data_dir(), 'cities.csv')


def cities_cache_path():
    return os.path.join(common_data_dir(), 'cities_cache.csv')


def new_cities_path():
    return os.path.join(common_data_dir(), 'new_cities.csv')


def theaters_path():
    return os.path.join(common_data_dir(), 'theaters.csv')


def theaters_cache_path():
    return os.path.join(common_data_dir(), 'theaters_cache.csv')


def new_theaters_path():
    return os.path.join(common_data_dir(), 'new_theaters.csv')


def screens_path():
    return os.path.join(common_data_dir(), 'screens.csv')


def screens_cache_path():
    return os.path.join(common_data_dir(), 'screens_cache.csv')


def new_screens_path():
    return os.path.join(common_data_dir(), 'new_screens.csv')


class City(models.Model):
    """
    City table, a city groups theaters.
    """
    # Define the fields.
    city_id = models.IntegerField(unique=True, null=False)
    name = models.CharField(max_length=128, null=False, blank=False)
    country = models.CharField(max_length=72, null=False, blank=False)

    # Define a manager.
    cities = models.Manager()

    class Meta:
        db_table = 'city'
        unique_together = ('name', 'country')

    def __str__(self):
        return f'{self.name}'


class Theater(models.Model):
    """
    Theaters, provide screens.
    """
    # Define theater priorities as preference level while automatic
    # planning.
    class Priority(models.IntegerChoices):
        NO_GO = 0
        LOW = 1
        HIGH = 2

    # Define color dictionary.
    color_by_priority = {
        Priority.NO_GO: 'SlateGray',
        Priority.LOW: 'PowderBlue',
        Priority.HIGH: 'Coral'
    }

    # Define the fields.
    theater_id = models.IntegerField(unique=True, null=False)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    parse_name = models.CharField(max_length=64, null=False, blank=False)
    abbreviation = models.CharField(max_length=10, null=False, blank=False)
    priority = models.IntegerField(choices=Priority.choices)

    # Define a manager.
    theaters = models.Manager()

    class Meta:
        db_table = 'theater'
        unique_together = ('city', 'abbreviation')

    def __str__(self):
        return f'{self.abbreviation} {self.city.name}'


class Screen(models.Model):
    """
    Screen, used to display a film on.
    """
    class ScreenAddressType(models.IntegerChoices):
        """
            Define screen address types as to indicate on location, on demand, physical.
        """
        PHYSICAL = 3
        ONDEMAND = 2
        ONLINE = 1

    # Define the fields.
    screen_id = models.IntegerField(unique=True, null=False)
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    parse_name = models.CharField(max_length=64, null=False, blank=False)
    abbreviation = models.CharField(max_length=8, null=True, blank=False)
    address_type = models.IntegerField(choices=ScreenAddressType.choices)

    # Define a manager.
    screens = models.Manager()

    class Meta:
        db_table = 'screen'

    def __str__(self):
        return f'{self.theater.abbreviation}{self.abbreviation}'
