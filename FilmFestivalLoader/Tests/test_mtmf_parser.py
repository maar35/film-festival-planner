import datetime
import unittest
from unittest import TestCase

from MTMF.parse_mtmf_html import FilmPageParser, MtmfData, FilmUrlFinder
from Shared.planner_interface import FilmInfo
from Tests.AuxiliaryClasses.test_film import BaseFilmTestCase


class ApplyCombinationsTestCase(BaseFilmTestCase):
    film_id = 0
    film_page_parser = None

    def setUp(self):
        super().setUp()
        self.festival_data = MtmfData(self.file_keeper.plandata_dir)
        self.film_property_by_label = {}
        self.add_test_films()

    def add_mtmf_test_film(self, title, minutes, url, description,
                           subs='EN', combi_program_urls=None, combi_part_urls=None):
        combination_urls = combi_program_urls or []
        screened_film_urls = combi_part_urls or []
        self.film_property_by_label['Ondertiteling'] = subs

        # Add the film to festival data.
        self.add_test_film(title, minutes, url, description)
        film = self.festival_data.films[-1]

        # Set-up global data that apply_combinations() uses.
        if self.film_page_parser is None:
            self.film_page_parser = FilmPageParser(self.festival_data, url)
        self.film_page_parser.combination_urls_by_film_id[film.filmid] = combination_urls
        self.film_page_parser.screened_film_urls_by_film_id[film.filmid] = screened_film_urls

        return film

    def add_test_films(self):
        part_urls = ['https://moviesthatmatter.nl/film/over-mij/',
                     'https://moviesthatmatter.nl/film/marko/']
        self.combi_film = self.add_mtmf_test_film(
            'The Combination', 45, 'https://moviesthatmatter.nl/film/under-the-lake/',
            'This unforgettable film combines several films in one program',
            combi_part_urls=part_urls
        )
        self.combi_part_1 = self.add_mtmf_test_film(
            'Parts Part 1', 20, part_urls[0],
            'You will not find a better first part than this one',
            combi_program_urls=[self.combi_film.url]
        )
        self.combi_part_2 = self.add_mtmf_test_film(
            'Parts Part 2', 18, part_urls[1],
            'Parts Part 2 covers both zebras and aardvarks',
            combi_program_urls=[self.combi_film.url]
        )

    def test_screened_films_linked_to_combination(self):
        # Arrange.
        combi_film_info = self.combi_film.film_info(self.festival_data)

        # Act.
        FilmPageParser.apply_combinations(self.festival_data)

        # Assert.
        self.assertEqual(len(combi_film_info.screened_films), 2)

    def test_combination_linked_to_screened_films(self):
        # Arrange.
        combi_part_info = self.combi_part_1.film_info(self.festival_data)

        # Act.
        FilmPageParser.apply_combinations(self.festival_data)

        # Assert.
        self.assertEqual(len(combi_part_info.combination_films), 1)


class UrlHandlingTestCase(TestCase):
    def test_section_base_with_space(self):
        # Arrange.
        section = 'short compilations'

        # Act.
        url = FilmUrlFinder.section_base(section)

        # Assert.
        self.assertEqual(url, 'https://moviesthatmatter.nl/festival/short%20compilations')

    def test_section_base_with_international_char(self):
        # Arrange.
        section = 'el niño'

        # Act.
        url = FilmUrlFinder.section_base(section)

        # Assert.
        self.assertEqual(url, 'https://moviesthatmatter.nl/festival/el%20ni%C3%B1o')


if __name__ == '__main__':
    unittest.main()
