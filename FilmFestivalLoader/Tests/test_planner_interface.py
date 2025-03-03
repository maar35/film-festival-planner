import tempfile
import unittest
from datetime import timedelta

import Shared.application_tools as app_tools
from Shared.planner_interface import FestivalData, Section, Film, UnicodeMapper
from Tests.AuxiliaryClasses.test_film import BaseFilmTestCase


class SectionsTestCase(unittest.TestCase):
    def setUp(self):
        self.city = 'Venezia'
        self.temp_dir = tempfile.TemporaryDirectory()
        self.festival_data = FestivalData(self.city, self.temp_dir.name, self.temp_dir.name)
        self.festival_data.write_verbose = False

    def tearDown(self):
        self.temp_dir.cleanup()

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


class ScreensTestCase(unittest.TestCase):
    def setUp(self):
        app_tools.SUPPRESS_INFO_PRINTS = True
        self.city = 'Amsterdam'
        self.temp_dir = tempfile.TemporaryDirectory()
        self.festival_data = FestivalData(self.city, self.temp_dir.name, self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_screens_can_be_read(self):
        # Arrange.
        data = self.festival_data
        theater_name = 'Kriterion'
        screen_1 = data.get_screen(self.city, 'Kriterion Grote Zaal', theater_name)
        screen_2 = data.get_screen(self.city, 'Kriterion Kleine Zaal', theater_name)
        screen_1.abbr = 'krgr'
        screen_2.abbr = 'krkl'
        data.write_new_screens()

        # Act.
        data.read_screens()

        # Assert.
        self.assertEqual(len(data.screen_by_location), 2)
        self.assertEqual(len(data.theater_by_location), 1)


class PlannerInterfaceBaseTestCase(BaseFilmTestCase):
    def setUp(self):
        super().setUp()
        self.festival_data = FestivalData('Riga', self.file_keeper.plandata_dir)

    def tearDown(self):
        super().tearDown()
        del self.festival_data


class AddFilmTestCase(PlannerInterfaceBaseTestCase):
    def test_add_new_film(self):
        # Arrange.
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
        self.assertEqual(len(films), 1, 'Second film, with same title and url, should update the first')
        self.assertIsNotNone(film_1)
        self.assertEqual(films[0].duration, film_2.duration)
        self.assertEqual(films[0], film_2)

    def test_add_existing_url_film(self):
        # Arrange.
        url = 'https://iffr.com/nl/iffr/2024/films/ammore-e-malavita'
        film_args_1 = [
            'Love and Underworld',
            url,
        ]
        film_args_2 = [
            'Ammore e malavita',
            url,
        ]

        # Act.
        film_1 = self.festival_data.add_film(*film_args_1)
        film_2 = self.festival_data.add_film(*film_args_2)

        # Assert.
        films = self.festival_data.films
        self.assertEqual(len(films), 1, 'Second film, with same URL, should be refused')
        self.assertEqual(films[0], film_1)
        self.assertIsNone(film_2)

    def test_add_new_url_existing_title(self):
        # Arrange.
        title = 'The One Title'
        film_args_1 = [
            title,
            'https://iffr.com/nl/iffr/2024/films/the-one-title'
        ]
        film_args_2 = [
            title,
            'https://iffr.com/nl/iffr/2024/films/die-ene-titel'
        ]

        # Act.
        film_1 = self.festival_data.add_film(*film_args_1)
        film_2 = self.festival_data.add_film(*film_args_2)

        # Assert.
        films = self.festival_data.films
        self.assertEqual(len(films), 1, 'Second film, with same title, should be refused')
        self.assertEqual(films[0], film_1)
        self.assertIsNone(film_2)


class SortTitlesTestCase(PlannerInterfaceBaseTestCase):
    def setUp(self):
        super().setUp()
        self.input_chars_str = 'azüYéØ190æøåè€ÉíñúàBê'

    def test_dirty_sorting(self):
        """ Display characters as sorted without our tools """
        # Arrange.
        expected_sorted_str = '019BYazÉØàåæèéêíñøúü€'
        expected_sorted = [c for c in expected_sorted_str]

        # Act.
        sorted_characters = sorted(self.input_chars_str)

        # Assert.
        self.assertEqual(sorted_characters, expected_sorted)

    def test_normalized_sorting(self):
        """ Display normalized characters as sorted by our tool """
        # Arrange.
        expected_sorted_str = '019BEYaaaeeeinuuzØæø€'
        expected_sorted = [c for c in expected_sorted_str]
        mapper = UnicodeMapper()
        normalized_str = mapper.normalize(self.input_chars_str)

        # Act.
        sorted_characters = sorted(normalized_str)

        # Assert.
        self.assertEqual(sorted_characters, expected_sorted)

    def test_normalized_to_lower_sorting(self):
        """ Display lower case normalized characters as sorted by our tools """
        # Arrange.
        expected_sorted_str = '019aaabeeeeinuuyzæøø€'
        expected_sorted = [c for c in expected_sorted_str]

        film_args = [
            'Amphetamine',
            'https://iffr.com/nl/iffr/2024/films/amphetamine',
        ]
        film_kwargs = {
            'duration': timedelta(minutes=97),
        }
        self.festival_data.add_film(*film_args, **film_kwargs)
        film = self.festival_data.films[0]
        normalized_str = film.lower(self.input_chars_str)

        # Act.
        sorted_characters = sorted(normalized_str)

        # Assert.
        self.assertEqual(sorted_characters, expected_sorted)


if __name__ == '__main__':
    unittest.main()
