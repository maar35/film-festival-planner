#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 24 16:18:02 2020

@author: maartenroos
"""


import datetime
import parse_idfa_html as idfa


def main():
    tests = [compare_a0,
             compare_0a,
             compare_a_,
             compare_00]
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
            print('Test {} failed :-('.format(test_func.__name__))
            print('Expected "{}"'.format(expected_string))
            print('Gotten   "{}"\n'.format(gotten_string))
        return success
    return add_result


class TestFilm:

    def __init__(self, title, url, minutes):
        self.title = title
        self.url = url
        self.duration = datetime.timedelta(minutes=minutes)


class TestList:

    test_films = []
    test_films.append(TestFilm(
        'Zappa',
        'https://www.idfa.nl/nl/film/4c62c61a-5d03-43f1-b3fd-1acc5fe74b2c/zappa%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        129))
    test_films.append(TestFilm(
        '100UP',
        'https://www.idfa.nl/nl/film/904e10e4-2b45-49ab-809a-bdac8e8950d1/100up%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        93))
    test_films.append(TestFilm(
        '’Til Kingdom Come',
        'https://www.idfa.nl/nl/film/c0e65192-b1a9-4fbe-b380-c74002cee909/til-kingdom-come%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        76))
    test_films.append(TestFilm(
        '48',
        'Films;https://www.idfa.nl/nl/film/ecf51812-683c-4811-be3d-175d97d6e583/48%3Ffilters%5Bedition.year%5D%3D2020%26collectionType%3Didfa',
        93))
    idfa_data = idfa.IdfaData(idfa.plandata_dir)
    for film in test_films:
        idfa.AzPageParser.add_film(idfa_data, film.title, film.url, film.duration)

    def __init(self):
        pass


@equity_decorator
def compare_a0():
    # Arrange.
    films = TestList.idfa_data.films

    # Act.
    less = films[0] < films[1]

    # Assert.
    return less, True


@equity_decorator
def compare_0a():
    # Arrange.
    films = TestList.idfa_data.films

    # Act.
    greater = films[0] > films[1]

    # Assert.
    return greater, False


@equity_decorator
def compare_a_():
    # Arrange.
    films = TestList.idfa_data.films

    # Act.
    less = films[0] < films[2]

    # Assert.
    return less, True


@equity_decorator
def compare_00():
    # Arrange.
    films = TestList.idfa_data.films

    # Act.
    less = films[1] < films[3]

    # Assert.
    return less, True


if __name__ == '__main__':
    main()
