import unittest

from MTMF.parse_mtmf_html import FilmPageParser, MtmfData, counter
from Shared.parse_tools import FileKeeper


class ApplyCombinationsTestCase(unittest.TestCase):
    def setUp(self):
        file_keeper = FileKeeper('MTMF', 2023)
        self.festival_data = MtmfData(file_keeper.plandata_dir)
        self.test_films = []
        counter.start('screened films assigned')
        counter.start('combinations assigned')
        self.add_test_films()

    def add_test_film(self, title, minutes, url, description,
                      subs='EN', combi_program_urls=None, combi_part_urls=None):
        parser = FilmPageParser(self.festival_data, url)
        parser.title = title
        parser.film_property_by_label['Duur'] = f'{minutes} minuten'
        parser.film_property_by_label['Ondertiteling'] = subs
        parser.description = description
        parser.article = ''
        parser.combination_urls = combi_program_urls or []
        parser.screened_film_urls = combi_part_urls or []
        parser.add_film()
        self.test_films.append(parser.film)
        return parser.film

    def add_test_films(self):
        part_urls = ['https://moviesthatmatter.nl/festival/film/over-mij/',
                     'https://moviesthatmatter.nl/festival/film/marko/']
        self.combi_film = self.add_test_film(
            'The Combination', 45, 'https://moviesthatmatter.nl/festival/film/under-the-lake/',
            'This unforgettable film combines several films in one program',
            combi_part_urls=part_urls
        )
        self.combi_part_1 = self.add_test_film(
            'Parts Part 1', 20, part_urls[0],
            'You will not find a better first part than this one',
            combi_program_urls=[self.combi_film.url]
        )
        self.combi_part_2 = self.add_test_film(
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


if __name__ == '__main__':
    unittest.main()
