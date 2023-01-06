#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 24 12:27:14 2020

@author: maartenroos
"""


import datetime

import parse_iffr_html as iffr
from Shared.parse_tools import FileKeeper
from Shared.planner_interface import Film, ScreenedFilmType, ScreenedFilm, Screen
from Shared.test_tools import execute_tests, equity_decorator
from Shared.web_tools import fix_json

festival = 'IFFR'
festival_year = 2022


def main():
    tests = [compare_a0,
             compare_0a,
             compare_a_,
             compare_00,
             # repair_url_works,
             # repair_url_pass,
             append_combination_0,
             append_combination_1,
             new_screened_film_0,
             new_screened_film_1,
             new_screen_online,
             new_screen_ondemand,
             new_screen_physical,
             fix_html_code_point,
             fix_html_code_point_str]
    execute_tests(tests)


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
        return Film.film_info(self, data)


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
    file_keeper = FileKeeper(festival, festival_year)
    festival_data = iffr.IffrData(file_keeper.plandata_dir)
    az_parser = iffr.AzPageParser(festival_data)
    for film in test_films:
        az_parser.title = film.title
        az_parser.url = film.url
        az_parser.duration = film.duration
        az_parser.sorted_title = film.title
        az_parser.description = film.description
        az_parser.add_film()
    info_parser = iffr.FilmInfoPageParser(festival_data, test_films[0])


@equity_decorator
def compare_a0():
    # Arrange.
    films = TestList.festival_data.films

    # Act.
    less = films[1] < films[0]

    # Assert.
    return less, True


@equity_decorator
def compare_0a():
    # Arrange.
    films = TestList.festival_data.films

    # Act.
    greater = films[1] > films[0]

    # Assert.
    return greater, False


@equity_decorator
def compare_a_():
    # Arrange.
    films = TestList.festival_data.films

    # Act.
    less = films[0] < films[2]

    # Assert.
    return less, True


@equity_decorator
def compare_00():
    # Arrange.
    films = TestList.festival_data.films

    # Act.
    less = films[1] < films[3]

    # Assert.
    return less, True


# @equity_decorator
# def repair_url_works():
#     # Arrange.
#     faulty_url = 'https://iffr.com/nl/2021/films/the-amusement-park'
#     correct_url = 'https://iffr.com/nl/iffr/2021/films/the-amusement-park'
#
#     # Act.
#     repaired_url = TestList.info_parser.repair_url(faulty_url)
#
#     # Assert.
#     return repaired_url, correct_url
#
#
# @equity_decorator
# def repair_url_pass():
#     # Arrange.
#     correct_url = 'https://iffr.com/nl/iffr/2021/films/the-amusement-park'
#
#     # Act.
#     repaired_url = TestList.info_parser.repair_url(correct_url)
#
#     # Assert.
#     return repaired_url, correct_url


@equity_decorator
def append_combination_0():
    # Arrange.
    new_film = TestList.festival_data.films[0]
    film_infos = TestList.festival_data.filminfos

    # Act.
    film_infos[0].combination_films.append(new_film)

    # Assert.
    return len(film_infos[1].combination_films), 0


@equity_decorator
def append_combination_1():
    # Arrange.
    first_film = TestList.festival_data.films[1]
    second_film = TestList.festival_data.films[2]
    third_film = TestList.festival_data.films[3]
    film_infos = TestList.festival_data.filminfos

    # Act.
    film_infos[1].combination_films.append(first_film)
    film_infos[1].combination_films.append(second_film)
    film_infos[2].combination_films.append(third_film)

    # Assert.
    return film_infos[1].combination_films[0], first_film


@equity_decorator
def new_screened_film_0():
    # Arrange.
    film = TestList.festival_data.films[0]
    film_id = film.filmid
    title = film.title
    description = TestList.test_films[0].description
    sf_type = ScreenedFilmType.SCREENED_BEFORE

    # Act.
    screened_film = ScreenedFilm(film_id, title, description, sf_type)

    # Assert.
    return screened_film.screened_film_type, ScreenedFilmType.SCREENED_BEFORE


@equity_decorator
def new_screened_film_1():
    # Arrange.
    film = TestList.festival_data.films[0]
    film_id = film.filmid
    title = film.title
    description = TestList.test_films[0].description
    sf_type = ScreenedFilmType.SCREENED_AFTER

    # Act.
    screened_film = ScreenedFilm(film_id, title, description, sf_type)

    # Assert.
    return screened_film.screened_film_type.name, 'SCREENED_AFTER'


@equity_decorator
def new_screen_online():
    # Arrange.
    city = 'The Hague'
    name = 'Online Program 42'
    screen_type = Screen.screen_types[1]  # OnLine

    # Act.
    screen = TestList.festival_data.get_screen(city, name)

    # Assert.
    return screen.type, screen_type


@equity_decorator
def new_screen_ondemand():
    # Arrange.
    city = 'The Hague'
    name = 'On Demand Theater'
    screen_type = Screen.screen_types[2]  # OnDemand

    # Act.
    screen = TestList.festival_data.get_screen(city, name)

    # Assert.
    return screen.type, screen_type


@equity_decorator
def new_screen_physical():
    # Arrange.
    city = 'The Hague'
    name = 'The Horse 666'
    screen_type = Screen.screen_types[0]  # Physical

    # Act.
    screen = TestList.festival_data.get_screen(city, name)

    # Assert.
    return screen.type, screen_type


@equity_decorator
def fix_html_code_point():
    # Arrange.
    code_point_str = '\u003c'

    # Act.
    result_str = fix_json(code_point_str)

    # Assert.
    return result_str, '<'


@equity_decorator
def fix_html_code_point_str():
    # Arrange.
    code_point_str = "Steve McQueens vorige installatie, \u003cem\u003eYear 3\u003c/em\u003e, maakte hij in " \
                     "opdracht van Tate Britain in 2019."
    clean_str = "Steve McQueens vorige installatie, <em>Year 3</em>, maakte hij in opdracht van Tate Britain in " \
                "2019."

    # Act.
    result_str = fix_json(code_point_str)

    # Assert.
    return result_str, clean_str


if __name__ == '__main__':
    main()
