#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct  7 15:13:21 2020

@author: maarten
"""

import datetime
#import parse_nff_html
import get_film_titles


def main():
    tests = [test_get_url,
             test_toascii]
    execute_tests(tests)

def execute_tests(tests):
    executed_count = 0
    succeeded_count = 0
    failed_count = 0
    for test in tests:
        executed_count += 1
        if test():
            succeeded_count += 1
        else:
            failed_count += 1
    print('\nTest results:')
    print('{:3d} tests executed.\n{:3d} tests succeeded.\n{:3d} tests failed.'.format(executed_count, succeeded_count, failed_count))

def equity_decorator(test_func):
    def add_result():
        gotten_string, expected_string = test_func()
        success = gotten_string == expected_string
        if success:
            print('Test {} succeeded!'.format(test_func.__name__))
        else:
            print('test {} failed :-('.format(test_func.__name__))
            print('Expected "{}"'.format(expected_string))
            print('Gotten   "{}"\n'.format(gotten_string))
        return success
    return add_result

@equity_decorator
def test_toascii():
    # Arrange.
    unicode_string = 'ñé²'
    
    # Act.
    ascii_string = get_film_titles.unicode_mapper.toascii(unicode_string)
    
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
    nff_film = get_film_titles.NffFilm(title, duration, description, directors, competitions)
    
    # Act.
    url = get_film_titles.FestivalData().get_url(nff_film.title)
    
    # Assert.
    return url, 'https://www.filmfestival.nl/en/films/more-moire²'


if __name__ == '__main__':
    main()