import unittest
from unittest import TestCase

from MTMF.parse_mtmf_html import FilmPageParser, MtmfData, FilmUrlFinder, COUNTER, setup_counters
from Tests.AuxiliaryClasses.test_film import BaseFilmTestCase


class ApplyCombinationsTestCase(BaseFilmTestCase):
    film_id = 0

    def setUp(self):
        super().setUp()
        self.festival_data = MtmfData(self.file_keeper.plandata_dir)
        setup_counters()
        FilmPageParser.combination_urls_by_film_id = {}
        self.film_property_by_label = {}
        self.add_test_films()

    def add_mtmf_test_film(self, title, minutes, url, description,
                           subs='EN', combi_program_urls=None):
        combination_urls = combi_program_urls or []
        self.film_property_by_label['Ondertiteling'] = subs

        # Add the film to festival data.
        self.add_test_film(title, minutes, url, description)
        film = self.festival_data.films[-1]

        # Setup global data that apply_combinations() uses.
        if combination_urls:
            FilmPageParser.combination_urls_by_film_id[film.film_id] = combination_urls

        return film

    def add_test_films(self):
        self.combi_film = self.add_mtmf_test_film(
            'The Combination', 45, 'https://moviesthatmatter.nl/film/under-the-lake/',
            'This unforgettable film combines several films in one program',
        )

        self.combi_part_1 = self.add_mtmf_test_film(
            'Parts Part 1', 20, 'https://moviesthatmatter.nl/film/over-mij/',
            'You will not find a better first part than this one',
            combi_program_urls=[self.combi_film.url]
        )

        self.combi_part_2 = self.add_mtmf_test_film(
            'Parts Part 2', 18, 'https://moviesthatmatter.nl/film/marko/',
            'Parts Part 2 covers both zebras and aardvarks',
            combi_program_urls=[self.combi_film.url]
        )

    def test_screened_films_linked_to_combination(self):
        # Arrange.
        combi_film_info = self.combi_film.film_info(self.festival_data)

        # Act.
        FilmPageParser.apply_combinations(self.festival_data)

        # Assert.
        self.assertEqual(len(combi_film_info.screened_films), 2, "Screened film count")

    def test_combination_linked_to_screened_films(self):
        # Arrange.
        combi_part_info = self.combi_part_1.film_info(self.festival_data)

        # Act.
        FilmPageParser.apply_combinations(self.festival_data)

        # Assert.
        self.assertEqual(len(combi_part_info.combination_films), 1, "Combination count")


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

    def test_set_nl_url(self):
        """ The Dutch version of a festival page can be derived from the English language version """
        # Arrange.
        en_url = 'https://moviesthatmatter.nl/en/festival/film/vlam/'
        nl_url = 'https://moviesthatmatter.nl/festival/film/vlam/'
        counter_label = 'EN url fixed'
        COUNTER.start(counter_label)

        # Act.
        result_url = FilmUrlFinder.set_nl_url(en_url)

        # Assert.
        self.assertEqual(result_url, nl_url)
        self.assertEqual(COUNTER.count_by_label[counter_label], 1)

    def test_set_nl_url_from_nl(self):
        """ When deriving the Dutch version of a festival page, a Dutch URL is returned unchanged """
        # Arrange.
        nl_url = 'https://moviesthatmatter.nl/festival/film/weight-of-light-the/'
        counter_label = 'EN url fixed'
        COUNTER.start(counter_label)

        # Act.
        result_url = FilmUrlFinder.set_nl_url(nl_url)

        # Assert.
        self.assertEqual(result_url, nl_url)
        self.assertEqual(COUNTER.count_by_label[counter_label], 0)


if __name__ == '__main__':
    unittest.main()
