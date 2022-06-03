# Tools tom support Film Rating data migrations.
import os
import csv
# from filmList.models import Film, FilmFan
import filmList.models


def main():
    festival = Festival('MTMF', 2022)
    print(os.path.join(festival.festival_data_dir, 'ratings.csv'))


def base_dir():
    return os.path.expanduser('~/Documents/Film')


class Festival:

    supported_names = ['IFFR', 'IDFA', 'Imagine', 'MTMF', 'NFF']

    def __init__(self, name, year):

        # Check the parameters.
        if name not in self.supported_names:
            raise UnsupportedFestivalException(name)

        if year < 2015 or year > 2030:
            raise UnsupportedFestivalYearException(year)

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

    def read_ratings(self, rating_class):
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
                except Exception as e:
                    print(f'Film not found: #{film_id}: {e}.')
                    continue
                print()
                print(film)
                try:
                    film_fan = filmList.models.FilmFan.film_fans.get(name=film_fan_name)
                except IndexError:
                    print(f'Film fan not found: {film_fan_name}.')
                    continue
                print(film_fan)
                fan_rating = filmList.models.FilmFanFilmRating(film=film, film_fan=film_fan)
                fan_rating.rating = rating
                fan_ratings.append(fan_rating)
        return fan_ratings


class UnsupportedFestivalException(Exception):

    def __init__(self, festival_name):
        self.festival_name = festival_name

    def __str__(self):
        return f'Festival named "{self.festival_name}" is not supported.'


class UnsupportedFestivalYearException(Exception):

    def __init__(self, year):
        self.year = year

    def __str__(self):
        return f'Year "{self.year}" is not supported.'


if __name__ == '__main__':
    main()
