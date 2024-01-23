#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide unit tests for IFFR loader.

Created on Thu Dec 24 12:27:14 2020

@author: maartenroos
"""
import shutil
import unittest

from IFFR.parse_iffr_html import IffrData
from Shared.parse_tools import FileKeeper
from Shared.planner_interface import Film, ScreenedFilmType, ScreenedFilm, Screen, FilmInfo
from Shared.web_tools import fix_json
from Tests.AuxiliaryClasses.test_film import TestFilm

festival = 'Cannes'
festival_year = 2023


def arrange_festival_data(file_keeper):
    return IffrData(file_keeper.plandata_dir)


def tear_down_festival_data(file_keeper):
    base_dir = file_keeper.festival_dir
    shutil.rmtree(base_dir)


def arrange_test_films(festival_data):
    # Create a list of bare-bones film-like objects.
    # noinspection PyListCreation
    test_films = []
    test_films.append(IffrTestFilm(
        500, 'Zappa',
        'https://iffr.com/nl/iffr/2021/films/4c62c61a-5d03-43f1-b3fd-1acc5fe74b2c/zappa',
        129,
        'A fabulous documentary on the greatest musical artist ever.',
        festival_data))
    test_films.append(IffrTestFilm(
        501, '100UP',
        'https://iffr.com/nl/iffr/2021/films/904e10e4-2b45-49ab-809a-bdac8e8950d1/100up',
        93,
        'this is test film, specially created for this unit test',
        festival_data))
    test_films.append(IffrTestFilm(
        502, '’Til Kingdom Come',
        'https://iffr.com/nl/iffr/2021/films/c0e65192-b1a9-4fbe-b380-c74002cee909/til-kingdom-come',
        76,
        'As the tile already indicates, the makers of the film disrespect the English language.',
        festival_data))
    test_films.append(IffrTestFilm(
        503, '80 000 ans',
        'https://iffr.com/nl/iffr/2021/films/80-000-ans',
        28,
        'This is some French movie. I would not bother to see it.',
        festival_data))

    # Fill the IFFR films list.
    for test_film in test_films:
        festival_data.film_seqnr += 1
        festival_data.curr_film_id += 1
        film = Film(festival_data.film_seqnr,
                    festival_data.curr_film_id,
                    test_film.title,
                    test_film.url)
        film.duration = test_film.duration
        film.sortstring = test_film.title
        film.medium_category = Film.category_films
        festival_data.films.append(film)
        film_info = FilmInfo(film.filmid, test_film.description, '')
        festival_data.filminfos.append(film_info)


class IffrTestFilm(TestFilm):

    def __init__(self, film_id, title, url, minutes, description, festival_data):
        TestFilm.__init__(self, film_id, title, url, minutes, description, festival_data)


class IffrBaseTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.file_keeper = FileKeeper(festival, festival_year)
        self.festival_data = arrange_festival_data(self.file_keeper)

    def tearDown(self):
        super().tearDown()
        tear_down_festival_data(self.file_keeper)


class CompareIffrFilmsTestCase(IffrBaseTestCase):
    def setUp(self):
        super().setUp()
        arrange_test_films(self.festival_data)

    def tearDown(self):
        super().tearDown()

    def test_compare_a0(self):
        # Arrange.
        films = self.festival_data.films

        # Act.
        less = films[1] < films[0]

        # Assert.
        self.assertTrue(less)

    def test_compare_0a(self):
        # Arrange.
        films = self.festival_data.films

        # Act.
        greater = films[1] > films[0]

        # Assert.
        self.assertFalse(greater)

    def test_compare_a_(self):
        # Arrange.
        films = self.festival_data.films

        # Act.
        less = films[0] < films[2]

        # Assert.
        self.assertTrue(less)

    def test_compare_00(self):
        # Arrange.
        films = self.festival_data.films

        # Act.
        less = films[1] < films[3]

        # Assert.
        self.assertTrue(less)


class IffrCombinationProgramsTestCase(IffrBaseTestCase):
    def setUp(self):
        super().setUp()
        arrange_test_films(self.festival_data)

    def tearDown(self):
        super().tearDown()

    def test_combinations_correct_initialized(self):
        # Arrange.
        new_film = self.festival_data.films[0]
        film_infos = self.festival_data.filminfos

        # Act.
        film_infos[0].combination_films.append(new_film)

        # Assert.
        self.assertEqual(len(film_infos[1].combination_films), 0,
                         'Combinations are correctly initialized (not as empty list)')

    def test_append_combination(self):
        # Arrange.
        first_film = self.festival_data.films[1]
        second_film = self.festival_data.films[2]
        third_film = self.festival_data.films[3]
        film_infos = self.festival_data.filminfos

        # Act.
        film_infos[1].combination_films.append(first_film)
        film_infos[1].combination_films.append(second_film)
        film_infos[2].combination_films.append(third_film)

        # Assert.
        self.assertEqual(film_infos[1].combination_films[0], first_film)

    def test_new_screened_film_screened_before(self):
        # Arrange.
        film = self.festival_data.films[0]
        film_id = film.filmid
        title = film.title
        film_info = film.film_info(self.festival_data)
        description = film_info.description
        sf_type = ScreenedFilmType.SCREENED_BEFORE

        # Act.
        screened_film = ScreenedFilm(film_id, title, description, sf_type)

        # Assert.
        self.assertEqual(screened_film.screened_film_type, ScreenedFilmType.SCREENED_BEFORE)

    def test_new_screened_film_screened_after(self):
        # Arrange.
        film = self.festival_data.films[0]
        film_id = film.filmid
        title = film.title
        film_info = film.film_info(self.festival_data)
        description = film_info.description
        sf_type = ScreenedFilmType.SCREENED_AFTER

        # Act.
        screened_film = ScreenedFilm(film_id, title, description, sf_type)

        # Assert.
        self.assertEqual(screened_film.screened_film_type.name, 'SCREENED_AFTER')


class CreateScreenTestCase(IffrBaseTestCase):
    def setUp(self):
        super().setUp()
        self.city = 'The Hague'

    def tearDown(self):
        super().tearDown()

    def test_new_screen_online(self):
        # Arrange.
        name = 'Online Program 42'
        screen_type = Screen.screen_types[1]  # OnLine

        # Act.
        screen = self.festival_data.get_screen(self.city, name)

        # Assert.
        return screen.type, screen_type

    def test_new_screen_ondemand(self):
        # Arrange.
        name = 'On Demand Theater'
        screen_type = Screen.screen_types[2]  # OnDemand

        # Act.
        screen = self.festival_data.get_screen(self.city, name)

        # Assert.
        return screen.type, screen_type

    def test_new_screen_physical(self):
        # Arrange.
        name = 'The Horse 666'
        screen_type = Screen.screen_types[0]  # Physical

        # Act.
        screen = self.festival_data.get_screen(self.city, name)

        # Assert.
        return screen.type, screen_type


class HandleUtfCodePointTestCas(unittest.TestCase):
    def test_fix_html_code_point(self):
        # Arrange.
        code_point_str = '\u003c'

        # Act.
        result_str = fix_json(code_point_str)

        # Assert.
        self.assertEqual(result_str, '<')

    def test_fix_html_code_point_str(self):
        # Arrange.
        code_point_str = "Steve McQueens vorige installatie, \u003cem\u003eYear 3\u003c/em\u003e, maakte hij in " \
                         "opdracht van Tate Britain in 2019."
        clean_str = "Steve McQueens vorige installatie, <em>Year 3</em>, maakte hij in opdracht van Tate Britain in " \
                    "2019."

        # Act.
        result_str = fix_json(code_point_str)

        # Assert.
        self.assertEqual(result_str, clean_str)


if __name__ == '__main__':
    unittest.main()
