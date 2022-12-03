#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide unit tests for NFF loader.

Created on Wed Oct  7 15:13:21 2020

@author: maarten
"""

import datetime

import parse_nff_html
from Shared.test_tools import execute_tests, equity_decorator


def main():
    tests = [test_get_url,
             test_toascii]
    execute_tests(tests)


@equity_decorator
def test_toascii():
    # Arrange.
    unicode_string = 'ñé²'

    # Act.
    ascii_string = parse_nff_html.unicode_mapper.toascii(unicode_string)

    # Assert.
    return ascii_string, 'ne²'


@equity_decorator
def test_get_url():
    # Arrange.
    title = 'More Moiré²'
    duration = datetime.timedelta(minutes=7)
    description = """Enter a 360-degree capsule and reset your senses, bathed in light, sound and smell. The immersive installatio
n More Moiré2 creates an overwhelming filmic experience in a panoramic space, resetting your senses with landscapes of ligh
t, sound and moving moiré patterns."""
    directors = 'Philip Vermeulen'
    competitions = 'Gouden Kalf Competitie'
    nff_film = parse_nff_html.NffFilm(title, duration, description, directors, competitions)

    # Act.
    url = parse_nff_html.NffData("/tmp").get_url(nff_film.title)

    # Assert.
    return url, 'https://www.filmfestival.nl/en/films/more-moire²'


if __name__ == '__main__':
    main()
