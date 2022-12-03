#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide unit tests for IDFA loader.

Created on Tue Nov 24 16:18:02 2020

@author: maartenroos
"""


import datetime

import parse_idfa_html as idfa
from Shared.test_tools import execute_tests, equity_decorator


idfa_data = idfa.IdfaData(idfa.plandata_dir)
idfa_films = []


def main():
    tests = [compare_a0,
             compare_0a,
             compare_a_,
             compare_00,
             test_film_title_error]
    arrange_test_films()
    execute_tests(tests)


def arrange_test_films():
    # Create a list of bare-bones films.
    test_films = []
    test_films.append(TestFilm(
        'Zappa',
        'https://www.idfa.nl/nl/film/4c62c61a-5d03-43f1-b3fd-1acc5fe74b2c/zappa%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        129))
    test_films.append(TestFilm(
        '100UP',
        'https://www.idfa.nl/nl/film/904e10e4-2b45-49ab-809a-bdac8e8950d1/100up%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        93))
    test_films.append(TestFilm(
        '’Til Kingdom Come',
        'https://www.idfa.nl/nl/film/c0e65192-b1a9-4fbe-b380-c74002cee909/til-kingdom-come%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        76))
    test_films.append(TestFilm(
        '48',
        'Films;https://www.idfa.nl/nl/film/ecf51812-683c-4811-be3d-175d97d6e583/48%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        93))

    # Fill the list with films that have IDFA sorting.
    for test_film in test_films:
        film = idfa_data.create_film(test_film.title, test_film.url)
        film.duration = test_film.duration
        idfa_films.append(idfa.Film(film))


class TestFilm:

    def __init__(self, title, url, minutes):
        self.title = title
        self.url = url
        self.duration = datetime.timedelta(minutes=minutes)


@equity_decorator
def compare_a0():
    # Arrange.
    films = idfa_films

    # Act.
    less = films[0] < films[1]

    # Assert.
    return less, True


@equity_decorator
def compare_0a():
    # Arrange.
    films = idfa_films

    # Act.
    greater = films[0] > films[1]

    # Assert.
    return greater, False


@equity_decorator
def compare_a_():
    # Arrange.
    films = idfa_films

    # Act.
    less = films[0] < films[2]

    # Assert.
    return less, True


@equity_decorator
def compare_00():
    # Arrange.
    films = idfa_films

    # Act.
    less = films[1] < films[3]

    # Assert.
    return less, True


@equity_decorator
def test_film_title_error():
    # Arrange.
    screened_title = None
    screened_description = "Boyi-biyo vertelt het verhaal van Shilo, die in de Centraal-Afrikaanse Republiek"
    screened_description += " met zijn gezin maar net kan rondkomen van zijn werk als vleeskoerier. Ondanks"
    screened_description += " vele obstakels blijft hij ondertussen dromen van een carrière als marathonloper."
    combination_url = 'https://www.idfa.nl/nl/shows/82f713ed-7812-4e2f-a8f5-9de4ceba3daf/boyi-biyo-red-card'
    combination_title = 'Boyi-biyo @ Red Card'
    combination_film = idfa_data.create_film(combination_title, combination_url)

    # Act.
    correct_exception = None
    try:
        _ = idfa.planner.ScreenedFilm(combination_film.filmid, screened_title, screened_description)
    except idfa.planner.FilmTitleError:
        correct_exception = True
    except Exception:
        correct_exception = False

    # Assert.
    return correct_exception, True


if __name__ == '__main__':
    main()
