#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provides tools for unit testing.

Created on Wed Nov 25 23:51:46 2020

@author: maartenroos
"""


class TextColors:
    green = '\u001b[32m'
    red = ' \u001b[31m'
    reset = '\u001b[0m'


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
    color = TextColors.green if failed_count == 0 else TextColors.red
    roloc = TextColors.reset
    print(f'{executed_count:3d} tests executed.\n{succeeded_count:3d} tests succeeded.\n{color}{failed_count:3d} tests failed{roloc}.')


def equity_decorator(test_func):
    def add_result():
        gotten_string, expected_string = test_func()
        success = gotten_string == expected_string
        if success:
            print(f'Test {test_func.__name__} {TextColors.green}succeeded{TextColors.reset}!')
        else:
            print(f'Test {test_func.__name__} {TextColors.red}failed{TextColors.reset} :-(')
            print('Expected "{}"'.format(expected_string))
            print('Gotten   "{}"\n'.format(gotten_string))
        return success
    return add_result


if __name__ == "__main__":
    print("This module is not executable.")
