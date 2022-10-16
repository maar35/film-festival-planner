#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 20 22:11:21 2020

@author: maarten
"""

from datetime import datetime
import inspect


def comment(text):
    print(f"\n{datetime.now()}  - {text}")


class ErrorCollector:

    def __init__(self):
        self.errors = []

    def __str__(self):
        return "\n".join(self.errors) + "\n"

    def add(self, err, msg):
        frame = inspect.currentframe().f_back
        lineno = frame.f_lineno
        caller = frame.f_code.co_name if frame.f_code is not None else 'code'
        error = f"{datetime.now()} - ERROR {err} in {caller} line {lineno} - {msg}"
        print(error)
        self.errors.append(error)

    def error_count(self):
        return len(self.errors)


class DebugRecorder:

    def __init__(self, debug_file):
        self.debug_file = debug_file
        self.debug_lines = []

    def __str__(self):
        return "\n".join(self.debug_lines) + "\n"

    def add(self, line):
        self.debug_lines.append(line)

    def write_debug(self):
        if len(self.debug_lines) > 0:
            time_stamp = datetime.now().isoformat(' ') + '\n'
            with open(self.debug_file, 'w') as f:
                f.write(time_stamp + str(self))
            print(f"Debug text written to {self.debug_file}.")
        else:
            print(f"No debug text, nothing written to {self.debug_file}.")


if __name__ == "__main__":
    print("This module is not executable.")
