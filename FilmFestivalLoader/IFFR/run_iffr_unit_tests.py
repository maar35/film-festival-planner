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
             compare_00,
             repair_url_works,
             repair_url_pass]
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
        self.film_inf0 = None

    def film_info(self, data):
        return None


class TestList:

    test_films = []
    test_films.append(TestFilm(
        'Zappa',
        'https://www.idfa.nl/nl//film//4c62c61a-5d03-43f1-b3fd-1acc5fe74b2c/zappa%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        129))
    test_films.append(TestFilm(
        '100UP',
        'https://www.idfa.nl/nl//film//904e10e4-2b45-49ab-809a-bdac8e8950d1/100up%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        93))
    test_films.append(TestFilm(
        '’Til Kingdom Come',
        'https://www.idfa.nl/nl//film//c0e65192-b1a9-4fbe-b380-c74002cee909/til-kingdom-come%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        76))
    test_films.append(TestFilm(
        '80 000 ans',
        'https://iffr.com/nl/2021/films/80-000-ans',
        28))
    festival_data = iffr.IffrData(iffr.plandata_dir)
    az_parser = iffr.AzPageParser(festival_data)
    for film in test_films:
        az_parser.title = film.title
        az_parser.url = film.url
        az_parser.duration = film.duration
        az_parser.sorted_title = film.title
        az_parser.add_film()
    combi_parser = iffr.FilmInfoPageParser(festival_data, test_films[0])



@test_tools.equity_decorator
def test_new_name_first():

    # Arrange.
    screen_splitter = iffr.ScreenSplitter(iffr.plandata_dir)
    testname = 'offline'
    names = ['offline']

    # Act.
    newname = screen_splitter.new_name(testname, names)

    # Assert.
    return newname, 'offline2'


@test_tools.equity_decorator
def test_new_name_not():

    # Arrange.
    screen_splitter = iffr.ScreenSplitter(iffr.plandata_dir)
    testname = 'offline'
    names = []

    # Act.
    newname = screen_splitter.new_name(testname, names)

    # Assert.
    return newname, 'offline'


@test_tools.equity_decorator
def test_new_name_gap():

    # Arrange.
    screen_splitter = iffr.ScreenSplitter(iffr.plandata_dir)
    testname = 'offline'
    names = ['offline', 'offline3']

    # Act.
    newname = screen_splitter.new_name(testname, names)

    # Assert.
    return newname, 'offline2'


@test_tools.equity_decorator
def test_new_name_next():

    # Arrange.
    screen_splitter = iffr.ScreenSplitter(iffr.plandata_dir)
    testname = 'offline199'
    names = ['offline199', 'offline200']

    # Act.
    newname = screen_splitter.new_name(testname, names)

    # Assert.
    return newname, 'offline201'


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


@test_tools.equity_decorator
def repair_url_works():
    # Arrange.
    faulty_url = 'https://iffr.com/nl/2021/films/the-amusement-park'
    correct_url = 'https://iffr.com/nl/iffr/2021/films/the-amusement-park'

    # Act.
    repaired_url = TestList.combi_parser.repair_url(faulty_url)

    # Assert.
    return repaired_url, correct_url


@test_tools.equity_decorator
def repair_url_pass():
    # Arrange.
    correct_url = 'https://iffr.com/nl/iffr/2021/films/the-amusement-park'

    # Act.
    repaired_url = TestList.combi_parser.repair_url(correct_url)

    # Assert.
    return repaired_url, correct_url


if __name__ == '__main__':
    main()
