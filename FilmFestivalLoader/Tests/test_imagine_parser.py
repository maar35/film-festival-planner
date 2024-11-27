#!/usr/bin/env python3

import datetime
import unittest

from Imagine.parse_imagine_html import ImagineData, AzPageParser, FilmPageParser
from Shared.planner_interface import Film
from Tests.AuxiliaryClasses.test_film import BaseTestCase


class BaseImagineTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.festival_data = ImagineData(self.file_keeper.plandata_dir)


class ImagineAzParserTestCase(BaseImagineTestCase):
    def setUp(self):
        super().setUp()
        self.parser = AzPageParser(self.festival_data)

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

    def test_get_title_and_qa(self):
        """
        The data found in IN_TITLE state can be parsed into a title and a Q&A indicator.
        """
        # Arrange.
        data = 'The Menu + Q&A'

        # Act.
        title = self.parser.get_title(data)

        # Assert.
        self.assertEqual(title, 'The Menu')
        self.assertEqual(self.parser.qa, 'Q&A')

    def test_get_title(self):
        """
        The data found in IN_TITLE state can be parsed into a title without Q&A indicator.
        """
        # Arrange.
        data = 'Things to Come: Human Augmentation'

        # Act.
        title = self.parser.get_title(data)

        # Assert.
        self.assertEqual(title, data)
        self.assertEqual(self.parser.qa, '')


class ImagineFilmPageParserTestCase(BaseImagineTestCase):
    def setUp(self):
        super().setUp()
        url = 'https://www.imaginefilmfestival.nl/film/the-menu/'
        film = Film(1, 1, 'The Big Deal', url)
        film.duration = datetime.timedelta(minutes=90)
        film.medium_category = 'films'
        self.parser = FilmPageParser(self.festival_data, film)

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
