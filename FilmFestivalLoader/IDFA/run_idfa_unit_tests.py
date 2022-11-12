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


def main():
    tests = [compare_a0,
             compare_0a,
             compare_a_,
             compare_00,
             test_film_title_error]
    execute_tests(tests)


class TestFilm():

    def __init__(self, title, url, minutes):
        self.title = title
        self.url = url
        self.duration = datetime.timedelta(minutes=minutes)
        parser = idfa.FilmPageParser(idfa_data, film_id, url, 'UT', debugging=False)
        parser.title = title
        parser.duration = self.duration
        parser.add_film()
        super().__init__(parser.film)


class TestList:

    test_films = []
    test_films.append(TestFilm(
        1,
        'Zappa',
        'https://www.idfa.nl/nl/film/4c62c61a-5d03-43f1-b3fd-1acc5fe74b2c/zappa%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        129))
    test_films.append(TestFilm(
        2,
        '100UP',
        'https://www.idfa.nl/nl/film/904e10e4-2b45-49ab-809a-bdac8e8950d1/100up%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        93))
    test_films.append(TestFilm(
        3,
        '’Til Kingdom Come',
        'https://www.idfa.nl/nl/film/c0e65192-b1a9-4fbe-b380-c74002cee909/til-kingdom-come%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        76))
    test_films.append(TestFilm(
        4,
        '48',
        'Films;https://www.idfa.nl/nl/film/ecf51812-683c-4811-be3d-175d97d6e583/48%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        93))
    # idfa_data = idfa.IdfaData(idfa.plandata_dir)
    for film in test_films:
        parser = idfa.FilmPageParser(idfa_data, film.film_id, film.url, 'UT', debugging=False)
        parser.title = film.title
        parser.duration = film.duration
        parser.add_film()

    def __init(self):
        pass


@equity_decorator
def compare_a0():
    # Arrange.
    films = idfa_data.films

    # Act.
    less = films[0] < films[1]

    # Assert.
    return less, True


@equity_decorator
def compare_0a():
    # Arrange.
    films = idfa_data.films

    # Act.
    greater = films[0] > films[1]

    # Assert.
    return greater, False


@equity_decorator
def compare_a_():
    # Arrange.
    films = idfa_data.films

    # Act.
    less = films[0] < films[2]

    # Assert.
    return less, True


@equity_decorator
def compare_00():
    # Arrange.
    films = idfa_data.films

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
    idfa_data = idfa.IdfaData(idfa.plandata_dir)
    compilation_url = 'https://www.idfa.nl/nl/shows/82f713ed-7812-4e2f-a8f5-9de4ceba3daf/boyi-biyo-red-card'
    compilation_title = 'Boyi-biyo @ Red Card'
    film = idfa.planner.Film(1, 1, compilation_title, compilation_url)
    # parser = idfa.SpecialFeaturePageParser(idfa_data, compilation_url, compilation_title)
    parser = idfa.SpecialFeaturePageParser(idfa_data, film)
    parser.screened_title = screened_title
    parser.screened_description = screened_description

    # Act.
    correct_exception = None
    try:
        _ = idfa.planner.ScreenedFilm(film.filmid, screened_title, screened_description)
    except idfa.planner.FilmTitleError:
        correct_exception = True
    except Exception:
        correct_exception = False

    # Assert.
    return correct_exception, True


if __name__ == '__main__':
    main()
