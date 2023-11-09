#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide unit tests for IDFA loader.

Created on Tue Nov 24 16:18:02 2020

@author: maartenroos
"""

import datetime
import unittest

from IDFA.parse_idfa_html import IdfaData, plandata_dir, IdfaFilm, FilmPageParser
from Shared.planner_interface import FilmTitleError, ScreenedFilm


class TestFilm:

    def __init__(self, title, url, minutes):
        self.title = title
        self.url = url
        self.duration = datetime.timedelta(minutes=minutes)


class CompareIdfaFilmsTestCase(unittest.TestCase):
    def setUp(self):
        self.idfa_data = IdfaData(plandata_dir)
        self.idfa_films = []
        self.arrange_test_films()

    def arrange_test_films(self):
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
            film = self.idfa_data.create_film(test_film.title, test_film.url)
            film.duration = test_film.duration
            self.idfa_films.append(IdfaFilm(film))

    def test_compare_alpha_digit(self):
        # Arrange.
        alpha_film = self.idfa_films[0]
        digit_film = self.idfa_films[1]

        # Act.
        less = alpha_film < digit_film

        # Assert.
        self.assertEqual(True, less, f'"{alpha_film.title}" sorts after "{digit_film.title}"')

    def test_compare_digit_alpha(self):
        # Arrange.
        alpha_film = self.idfa_films[0]
        digit_film = self.idfa_films[1]

        # Act.
        greater = alpha_film > digit_film

        # Assert.
        self.assertEqual(False, greater, f'"{digit_film.title}" sorts before "{alpha_film.title}"')

    def test_compare_alpha_other(self):
        # Arrange.
        alpha_film = self.idfa_films[0]
        other_film = self.idfa_films[2]

        # Act.
        less = alpha_film < other_film

        # Assert.
        self.assertEqual(True, less, f'"{alpha_film.title}" sorts before "{other_film.title}"')

    def test_compare_digit_digtit(self):
        # Arrange.
        digit_film_1 = self.idfa_films[1]
        digit_film_2 = self.idfa_films[3]

        # Act.
        less = digit_film_1 < digit_film_2

        # Assert.
        self.assertEqual(True, less, f'"{digit_film_1.title}" sorts before "{digit_film_2.title}"')


class ScreenedFilmTestCase(unittest.TestCase):
    def setUp(self):
        self.idfa_data = IdfaData(plandata_dir)

    def test_screened_film_title_error(self):
        # Arrange.
        screened_title = None
        screened_description = "Boyi-biyo vertelt het verhaal van Shilo, die in de Centraal-Afrikaanse Republiek"
        screened_description += " met zijn gezin maar net kan rondkomen van zijn werk als vleeskoerier. Ondanks"
        screened_description += " vele obstakels blijft hij ondertussen dromen van een carrière als marathonloper."
        combination_url = 'https://www.idfa.nl/nl/shows/82f713ed-7812-4e2f-a8f5-9de4ceba3daf/boyi-biyo-red-card'
        combination_title = 'Boyi-biyo @ Red Card'
        combination_film = self.idfa_data.create_film(combination_title, combination_url)

        # Act/Assert.
        with self.assertRaises(FilmTitleError):
            _ = ScreenedFilm(combination_film.filmid, screened_title, screened_description)


class IdfaFilmPageParserTestCase(unittest.TestCase):
    def setUp(self):
        festival_data = IdfaData(plandata_dir)
        url = 'https://www.idfa.nl/nl/film/45a9aaa6-36a2-4172-8816-6753a1435ac5/alis'
        film_id = festival_data.film_id_by_url[url]
        self.parser = FilmPageParser(festival_data, film_id, url, debug_prefix='T', debugging=False)

    def test_set_duration(self):
        # Arrange.
        data = '"runtime":128,'
        expected_duration = datetime.timedelta(minutes=128)

        # Act.
        self.parser.get_properties_from_dict(data)

        # Assert.
        self.assertEqual(expected_duration, self.parser.duration)


if __name__ == '__main__':
    unittest.main()
