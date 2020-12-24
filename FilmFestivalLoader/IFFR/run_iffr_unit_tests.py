#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 24 12:27:14 2020

@author: maartenroos
"""


import datetime
import sys
import os
import parse_iffr_html as iffr

prj_dir = os.path.expanduser("~/Projects/FilmFestivalPlanner")
shared_dir = os.path.join(prj_dir, "FilmFestivalLoader/Shared")
sys.path.insert(0, shared_dir)
import test_tools


def main():
    tests = [compare_a0,
             compare_0a,
             compare_a_,
             compare_00]
    test_tools.execute_tests(tests)


class TestFilm:

    def __init__(self, title, url, minutes):
        self.title = title
        self.url = url
        self.duration = datetime.timedelta(minutes=minutes)
        self.film = None
        self.description = None
        self.article = None
        self.sorted_title = None


class TestList:

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
    festival_data = iffr.IffrData(iffr.plandata_dir)
    parser = iffr.AzPageParser(festival_data)
    for film in test_films:
        parser.title = film.title
        parser.url = film.url
        parser.duration = film.duration
        parser.sorted_title = film.title
        parser.add_film()

    def __init(self):
        pass


@test_tools.equity_decorator
def compare_a0():
    # Arrange.
    films = TestList.festival_data.films

    # Act.
    less = films[1] < films[0]

    # Assert.
    return less, True


@test_tools.equity_decorator
def compare_0a():
    # Arrange.
    films = TestList.festival_data.films

    # Act.
    greater = films[1] > films[0]

    # Assert.
    return greater, False


@test_tools.equity_decorator
def compare_a_():
    # Arrange.
    films = TestList.festival_data.films

    # Act.
    less = films[0] < films[2]

    # Assert.
    return less, True


@test_tools.equity_decorator
def compare_00():
    # Arrange.
    films = TestList.festival_data.films

    # Act.
    less = films[1] < films[3]

    # Assert.
    return less, True


if __name__ == '__main__':
    main()
