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
import planner_interface


def main():
    tests = [compare_a0,
             compare_0a,
             compare_a_,
             compare_00,
             repair_url_works,
             repair_url_pass,
             append_combination_0,
             append_combination_1]
    test_tools.execute_tests(tests)


class TestFilm:

    def __init__(self, film_id, title, url, minutes, description):
        self.filmid = film_id
        self.title = title
        self.url = url
        self.duration = datetime.timedelta(minutes=minutes)
        self.description = description
        self.film = None
        self.article = None
        self.sorted_title = None

    def film_info(self, data):
        return planner_interface.Film.film_info(self, data)


class TestList:

    test_films = []
    test_films.append(TestFilm(
        500, 'Zappa',
        'https://www.idfa.nl/nl//film//4c62c61a-5d03-43f1-b3fd-1acc5fe74b2c/zappa%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        129,
        'A fabulous documentary on the greatest musical artist ever.'))
    test_films.append(TestFilm(
        501, '100UP',
        'https://www.idfa.nl/nl//film//904e10e4-2b45-49ab-809a-bdac8e8950d1/100up%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        93,
        'this is test film, specially created for this unit test'))
    test_films.append(TestFilm(
        502, '’Til Kingdom Come',
        'https://www.idfa.nl/nl//film//c0e65192-b1a9-4fbe-b380-c74002cee909/til-kingdom-come%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        76,
        'As the tile already indicates, the makers of the film disrespect the English language.'))
    test_films.append(TestFilm(
        503, '80 000 ans',
        'https://iffr.com/nl/2021/films/80-000-ans',
        28,
        'This is some French movie. I would not bother to see it.'))
    festival_data = iffr.IffrData(iffr.plandata_dir)
    az_parser = iffr.AzPageParser(festival_data)
    for film in test_films:
        az_parser.title = film.title
        az_parser.url = film.url
        az_parser.duration = film.duration
        az_parser.sorted_title = film.title
        az_parser.description = film.description
        az_parser.add_film()
    info_parser = iffr.FilmInfoPageParser(festival_data, test_films[0])


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
    repaired_url = TestList.info_parser.repair_url(faulty_url)

    # Assert.
    return repaired_url, correct_url


@test_tools.equity_decorator
def repair_url_pass():
    # Arrange.
    correct_url = 'https://iffr.com/nl/iffr/2021/films/the-amusement-park'

    # Act.
    repaired_url = TestList.info_parser.repair_url(correct_url)

    # Assert.
    return repaired_url, correct_url


@test_tools.equity_decorator
def append_combination_0():
    # Arrange.
    new_film = TestList.festival_data.films[0]
    film_infos = TestList.festival_data.filminfos
    append_combination = planner_interface.append_combination_film

    # Act.
    film_infos[0].combination_films = append_combination(film_infos[0].combination_films, new_film)

    # Assert.
    return len(film_infos[1].combination_films), 0


@test_tools.equity_decorator
def append_combination_1():
    # Arrange.
    first_film = TestList.festival_data.films[1]
    second_film = TestList.festival_data.films[2]
    third_film = TestList.festival_data.films[3]
    film_infos = TestList.festival_data.filminfos
    append_combination = planner_interface.append_combination_film

    # Act.
    film_infos[1].combination_films = append_combination(film_infos[1].combination_films, first_film)
    film_infos[1].combination_films = append_combination(film_infos[1].combination_films, second_film)
    film_infos[2].combination_films = append_combination(film_infos[2].combination_films, third_film)

    # Assert.
    return film_infos[1].combination_films[0], first_film


if __name__ == '__main__':
    main()
