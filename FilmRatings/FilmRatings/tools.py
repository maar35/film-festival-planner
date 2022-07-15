import csv
import os

from django.core.exceptions import ObjectDoesNotExist

from festivals.models import current_festival
from film_list.models import Film, FilmFan, FilmFanFilmRating, current_fan, get_user_fan


# Define common parameters for base template.
def user_is_admin(request):
    user_fan = get_user_fan(request.user)
    if user_fan is None:
        return False
    return user_fan.is_admin


def user_represents_fan(request, fan):
    if fan is None:
        return False
    user_fan = get_user_fan(request.user)
    if user_fan is None:
        return False
    return fan != user_fan and user_fan.is_admin


def add_base_context(request, param_dict):
    festival = current_festival(request.session)
    border_color = festival.border_color if festival is not None else None
    background_image = festival.base.image if festival is not None else None
    fan = current_fan(request.session)

    base_param_dict = {
        'border_color': border_color,
        'background_image': background_image,
        'festival': festival,
        'current_fan': fan,
        'user_is_admin': user_is_admin(request),
        'user_represents_fan': user_represents_fan(request, fan),
    }
    return {**base_param_dict, **param_dict}


# Tools to support Film Rating data migrations.
def base_dir():
    return os.path.expanduser('~/Documents/Film')


class Festival:

    supported_names = ['IFFR', 'IDFA', 'Imagine', 'MTMF', 'NFF']

    def __init__(self, name, year):

        # Check the parameters.
        if name not in self.supported_names:
            raise UnsupportedFestivalError(name)
        if year < 2015 or year > 2030:
            raise UnsupportedFestivalYearError(year)

        # Assign the member variables.
        self.name = name
        self.year = int(year)

    @property
    def festival_dir(self):
        return os.path.join(base_dir(), f'{self.name}', f'{self.name}{self.year}')

    @property
    def planner_data_dir(self):
        return os.path.join(self.festival_dir, '_planner_data')

    @property
    def festival_data_dir(self):
        return os.path.join(self.festival_dir, 'FestivalPlan')

    def read_ratings(self):
        ratings_file = os.path.join(self.festival_data_dir, 'ratings.csv')
        fan_ratings = []
        with open(ratings_file, newline='') as csvfile:
            rating_reader = csv.reader(csvfile, delimiter=';', quotechar='"')
            rating_reader.__next__()    # Skip header.
            for row in rating_reader:
                film_id = int(row[0])
                film_fan_name = row[1]
                rating = int(row[2])
                try:
                    film = Film.films.get(film_id=film_id)
                except ObjectDoesNotExist:
                    print(f'Film not found: #{film_id}.')
                    continue
                try:
                    film_fan = FilmFan.film_fans.get(name=film_fan_name)
                except ObjectDoesNotExist:
                    print(f'Film fan not found: {film_fan_name}.')
                    continue
                fan_rating = FilmFanFilmRating(film=film, film_fan=film_fan)
                fan_rating.rating = rating
                fan_ratings.append(fan_rating)
        print(f'{len(fan_ratings)} fan ratings found.')
        return fan_ratings


class UnsupportedFestivalError(Exception):

    def __init__(self, festival_name):
        self.festival_name = festival_name

    def __str__(self):
        return f'Festival named "{self.festival_name}" is not supported.'


class UnsupportedFestivalYearError(Exception):

    def __init__(self, year):
        self.year = year

    def __str__(self):
        return f'Year "{self.year}" is not supported.'
