from django.core.exceptions import ObjectDoesNotExist
import os
import csv
import filmList.models
from festivals.models import Festival as FestivalEdition


# Test opportunity.
def main():
    festival = Festival('MTMF', 2022)
    print(os.path.join(festival.festival_data_dir, 'ratings.csv'))


# Define common parameters for base template.
def add_base_context(param_dict):
    festivals = FestivalEdition.festivals.filter(is_current_festival=True)
    if len(festivals) > 0:
        festival = festivals[0]
        border_color = festival.border_color
    else:
        festival = None
        border_color = None
    base_param_dict = {
        'border_color': border_color,
        'festival': festival
    }
    return {**base_param_dict, **param_dict}


# Maintain the current festival.
def set_current_festival(festival):
    current_festivals = FestivalEdition.festivals.filter(is_current_festival=True)
    for current_festival in current_festivals:
        current_festival.is_current_festival = False
        current_festival.save()
    festival.is_current_festival = True
    festival.save()


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
                    film = filmList.models.Film.films.get(film_id=film_id)
                except ObjectDoesNotExist:
                    print(f'Film not found: #{film_id}.')
                    continue
                try:
                    film_fan = filmList.models.FilmFan.film_fans.get(name=film_fan_name)
                except ObjectDoesNotExist:
                    print(f'Film fan not found: {film_fan_name}.')
                    continue
                fan_rating = filmList.models.FilmFanFilmRating(film=film, film_fan=film_fan)
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


if __name__ == '__main__':
    main()
