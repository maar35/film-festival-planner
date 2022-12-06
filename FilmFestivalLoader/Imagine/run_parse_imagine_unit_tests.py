#!/usr/bin/env python3

import datetime
import unittest

from Imagine.parse_imagine_html import ImagineData, AzPageParser, FilmPageParser
from Shared.application_tools import DebugRecorder
from Shared.parse_tools import FileKeeper
from Shared.planner_interface import Film

# Initialize globals.
file_keeper = FileKeeper('Imagine', 2022)
debug_file = file_keeper.debug_file
debug_recorder = DebugRecorder(debug_file)


class ImagineAzParserTestCase(unittest.TestCase):
    def setUp(self):
        festival_data = ImagineData(file_keeper.plandata_dir)
        self.parser = AzPageParser(festival_data)

    def test_get_duration(self):
        # Arranged in setUp().

        # Act.
        duration = self.parser.get_duration('106 min.')

        # Assert.
        expected_duration = datetime.timedelta(minutes=106)
        self.assertEqual(duration, expected_duration)

    def test_get_subtitles(self):
        # Arranged in setUp().

        # Act.
        subs = self.parser.get_subtitles('Spaans (Engels ondertiteld)')

        # Assert.
        expected_subs = 'Engels ondertiteld'
        self.assertEqual(expected_subs, subs)


class ImagineFilmPageParserTestCase(unittest.TestCase):
    def setUp(self):
        festival_data = ImagineData(file_keeper.plandata_dir)
        url = min(festival_data.film_id_by_url.keys())
        film = Film(1, 1, 'The Big Deal', url)
        film.duration = datetime.timedelta(minutes=90)
        film.medium_category = 'films'
        self.parser = FilmPageParser(festival_data, film)

    def test_set_article(self):
        # Arrange.
        self.parser.article_paragraphs = [
            'No big deal is less important than this one.',
            'This inspiring, poetry-like, abstract, and a-synchronous biopic will bore you BAR.',
            'A master piece, only acknowledged by higher jury members.'
        ]

        # Act.
        self.parser.set_article()

        # Assert.
        self.assertEqual(3, len(self.parser.article.split('\n\n')))


if __name__ == '__main__':
    unittest.main()
