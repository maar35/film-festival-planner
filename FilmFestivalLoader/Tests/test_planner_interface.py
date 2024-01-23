#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from datetime import timedelta
from unittest import skip

from Shared.planner_interface import FestivalData, Section, Film


class FestivalDataBaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.festival_data = FestivalData(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()


class SectionsTestCase(FestivalDataBaseTestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_sections_do_not_need_to_be_present(self):
        # Arrange.
        data = self.festival_data

        # Act.
        self.festival_data.read_sections()

        # Assert.
        self.assertEqual(len(data.section_by_name), 0)

    def test_subsections_do_not_need_to_be_present(self):
        # Arrange.
        data = self.festival_data

        # Act.
        data.read_subsections()

        # Assert.
        self.assertEqual(len(data.subsection_by_name), 0)

    def test_sections_can_be_read(self):
        # Arrange.
        data = self.festival_data
        section_1 = Section(1, 'Mainstream', 'blue')
        section_2 = Section(2, 'Arti Farti', 'dark_grey')
        data.section_by_id[section_1.section_id] = section_1
        data.section_by_id[section_2.section_id] = section_2
        data.write_sections()
        data.section_by_id = {}

        # Act.
        data.read_sections()

        # Assert.
        self.assertEqual(len(data.section_by_name), 2)


class TestDrivenDevAddFilmTestCase(FestivalDataBaseTestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_add_new_film(self):
        # Arrange.
        self.assertEqual(len(self.festival_data.films), 0)
        film_args = [
            'Amphetamine',
            'https://iffr.com/nl/iffr/2024/films/amphetamine',
        ]
        film_kwargs = {
            'duration': timedelta(minutes=97),
        }

        # Act.
        self.festival_data.add_film(*film_args, **film_kwargs)

        # Assert.
        films = self.festival_data.films
        self.assertEqual(len(films), 1)
        self.assertIsInstance(films[0], Film)

    def test_add_existing_title_film(self):
        # Arrange.
        film_args = [
            'Amphetamine',
            'https://iffr.com/nl/iffr/2024/films/amphetamine',
        ]
        film_kwargs_1 = {
            'duration': timedelta(minutes=11),
        }
        film_kwargs_2 = {
            'duration': timedelta(minutes=204),
        }

        # Act.
        film_1 = self.festival_data.add_film(*film_args, **film_kwargs_1)
        film_2 = self.festival_data.add_film(*film_args, **film_kwargs_2)

        # Assert.
        films = self.festival_data.films
        self.assertEqual(len(films), 1)
        self.assertEqual(films[0].duration, film_1.duration)
        self.assertEqual(films[0], film_1)
        self.assertIsNone(film_2)

    def test_add_existing_url_film(self):
        # Arrange.
        film_args_1 = [
            'Love and Underworld',
            'https://iffr.com/nl/iffr/2024/films/ammore-e-malavita',
        ]
        film_args_2 = {
            'Ammore e malavita',
            'https://iffr.com/nl/iffr/2024/films/ammore-e-malavita',
        }

        # Act.
        film_1 = self.festival_data.add_film(*film_args_1)
        film_2 = self.festival_data.add_film(*film_args_2)

        # Assert.
        films = self.festival_data.films
        self.assertEqual(len(films), 1, 'Second film, with same URL, should be refused')
        self.assertEqual(films[0], film_1)
        self.assertIsNone(film_2)

    @skip
    def test_add_new_title_existing_url(self):
        # Arrange.
        pass

        # Act.

        # Assert.

    @skip
    def test_add_new_url_existing_title(self):
        # Arrange.
        pass

        # Act.

        # Assert.


if __name__ == '__main__':
    unittest.main()
