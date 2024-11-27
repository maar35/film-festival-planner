import csv
import os
import unittest

from IDFA.parse_idfa_html import IdfaData, IdfaScreening, FESTIVAL_CITY
from Shared.planner_interface import ScreenedFilm, FilmTitleError
from Tests.AuxiliaryClasses.test_film import BaseTestCase


class BaseIdfaTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        common_data_dir = os.path.join(self.file_keeper.basedir, 'common_data')
        os.mkdir(common_data_dir)
        self.festival_data = IdfaData(self.file_keeper.plandata_dir, common_data_dir=common_data_dir)


class ScreenedFilmTestCase(BaseIdfaTestCase):
    def test_screened_film_title_error(self):
        # Arrange.
        screened_title = ''
        screened_description = "Boyi-biyo vertelt het verhaal van Shilo, die in de Centraal-Afrikaanse Republiek"
        screened_description += " met zijn gezin maar net kan rondkomen van zijn werk als vleeskoerier. Ondanks"
        screened_description += " vele obstakels blijft hij ondertussen dromen van een carrière als marathonloper."
        combination_url = 'https://www.idfa.nl/nl/shows/82f713ed-7812-4e2f-a8f5-9de4ceba3daf/boyi-biyo-red-card'
        combination_title = 'Boyi-biyo @ Red Card'
        combination_film = self.festival_data.create_film(combination_title, combination_url)

        # Act/Assert.
        with self.assertRaises(FilmTitleError):
            _ = ScreenedFilm(combination_film.film_id, screened_title, screened_description)


class NewScreenTestCase(BaseIdfaTestCase):
    def test_numbered_screen(self):
        """
        A location name can be parsed into a theater name and a screen number.
        """
        # Arrange.
        data = 'LAB111 15'

        # Act.
        screen = IdfaScreening.get_idfa_screen(self.festival_data, data)

        # Assert.
        self.assertEqual(screen.theater.city.name, FESTIVAL_CITY)
        self.assertEqual(screen.theater.name, 'LAB111')
        self.assertEqual(screen.name, data)

    def test_new_named_screen(self):
        """
        A location nme can be parsaed into a theater name and a screen name.
        """
        # Arrange.
        data = 'Rembrandt Theater: Grote Zaal'

        # Act.
        screen = IdfaScreening.get_idfa_screen(self.festival_data, data)

        # Assert.
        self.assertEqual(screen.theater.city.name, FESTIVAL_CITY)
        self.assertEqual(screen.theater.name, 'Rembrandt Theater')
        self.assertEqual(screen.abbr, 'grotezaal')


class KnownScreenTestCase(BaseIdfaTestCase):
    def setUp(self):
        super().setUp()
        self.cities_file = self.festival_data.cities_file
        self.theaters_file = self.festival_data.theaters_file
        self.screens_file = self.festival_data.screens_file
        self.csv_dialect = self.festival_data.dialect

    def arrange_write_file(self, file, rows):
        with open(file, 'w') as csvfile:
            csv_writer = csv.writer(csvfile, self.csv_dialect)
            csv_writer.writerows(rows)

    def arrange_read_theater_data(self):
        self.festival_data.read_cities()
        self.festival_data.read_theaters()
        self.festival_data.read_screens()

    def test_known_screen(self):
        """
        A known screen object can be recognized when parsing a location name.
        """
        # Arrange.
        data = 'Rembrandt Theater: Grote Zaal'
        city_row = [1, FESTIVAL_CITY, 'nl']
        theater_row = [1, 1, 'Rembrandt Theater', 'rem', 2]
        screen_row = [1, 1, data, '-groot', 3]
        self.arrange_write_file(self.cities_file, [city_row])
        self.arrange_write_file(self.theaters_file, [theater_row])
        self.arrange_write_file(self.screens_file, [screen_row])
        self.arrange_read_theater_data()

        # Act.
        screen = IdfaScreening.get_idfa_screen(self.festival_data, data)

        # Assert.
        self.assertEqual(screen.theater.city.name, FESTIVAL_CITY)
        self.assertEqual(screen.theater.name, 'Rembrandt Theater')
        self.assertEqual(screen.theater.abbr, 'rem')
        self.assertEqual(screen.abbr, '-groot')
        self.assertEqual(str(screen), 'rem-groot')

    def test_known_numbered_screen(self):
        """
        A known screen object can be recognized when parsing a location name with screen number.
        """
        data = 'LAB111 15'
        city_row = [1, FESTIVAL_CITY, 'nl']
        theater_row = [1, 1, 'LAB111', 'lab', 2]
        screen_row = [1, 1, data, '15', 3]
        self.arrange_write_file(self.cities_file, [city_row])
        self.arrange_write_file(self.theaters_file, [theater_row])
        self.arrange_write_file(self.screens_file, [screen_row])
        self.arrange_read_theater_data()

        # Act.
        screen = IdfaScreening.get_idfa_screen(self.festival_data, data)

        # Assert.
        self.assertEqual(screen.theater.city.name, FESTIVAL_CITY)
        self.assertEqual(screen.theater.name, 'LAB111')
        self.assertEqual(screen.theater.abbr, 'lab')
        self.assertEqual(screen.abbr, '15')
        self.assertEqual(str(screen), 'lab15')


if __name__ == '__main__':
    unittest.main()
