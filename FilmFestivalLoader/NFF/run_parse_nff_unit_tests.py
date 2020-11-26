#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide unit tests for NFF loader.

Created on Wed Oct  7 15:13:21 2020

@author: maarten
"""

import datetime
import sys
import os
import parse_nff_html

prj_dir = os.path.expanduser("~/Projects/FilmFestivalPlanner/film-festival-planner.git")
shared_dir = os.path.join(prj_dir, "film-festival-planner/FilmFestivalLoader/Shared")
sys.path.insert(0, shared_dir)
import test_tools


def main():
    tests = [test_get_url,
             test_toascii]
    test_tools.execute_tests(tests)


@test_tools.equity_decorator
def test_toascii():
    # Arrange.
    unicode_string = 'ñé²'

    # Act.
    ascii_string = parse_nff_html.unicode_mapper.toascii(unicode_string)

    # Assert.
    return ascii_string, 'ne²'


@test_tools.equity_decorator
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
