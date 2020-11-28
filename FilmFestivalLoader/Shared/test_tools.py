#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provides tools for unit testing.

Created on Wed Nov 25 23:51:46 2020

@author: maartenroos
"""


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


if __name__ == "__main__":
    print("This module is not executable.")
