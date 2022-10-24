#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 7 22:24:00 2022

@author: maartenroos
"""

import os

import Shared.web_tools as web_tools
from Shared.planner_interface import Screening


class FileKeeper:
    def __init__(self, festival, year):
        # Define directories.
        self.base_dir = os.path.expanduser(f'~/Documents/Film')
        self.festival_dir = os.path.join(self.base_dir, f'{festival}')
        self.documents_dir = os.path.join(self.festival_dir, f'{festival}{year}')
        self.webdata_dir = os.path.join(self.documents_dir, '_website_data')
        self.plandata_dir = os.path.join(self.documents_dir, '_planner_data')
        self.interface_dir = os.path.join(self.documents_dir, 'FestivalPlan')

        # Define formats.
        self.az_file_format = os.path.join(self.webdata_dir, "az_page_{:02}.html")
        self.film_file_format = os.path.join(self.webdata_dir, "film_page_{:03d}.html")
        self.screenings_file_format = os.path.join(self.webdata_dir, "screenings_{:03d}_{:02d}.html")
        self.details_file_format = os.path.join(self.webdata_dir, "details_{:03d}_{:02d}.html")

        # Define filenames.
        self.az_file_unnumbered = os.path.join(self.webdata_dir, "azpage.html")
        self.debug_file = os.path.join(self.plandata_dir, "debug.txt")

        # Make sure that relevant directories exist.
        if not os.path.isdir(self.festival_dir):
            os.mkdir(self.festival_dir)
        if not os.path.isdir(self.documents_dir):
            os.mkdir(self.documents_dir)
        if not os.path.isdir(self.webdata_dir):
            os.mkdir(self.webdata_dir)
        if not os.path.isdir(self.plandata_dir):
            os.mkdir(self.plandata_dir)
        if not os.path.isdir(self.interface_dir):
            os.mkdir(self.interface_dir)

    def az_file(self, seq_nr=None):
        if seq_nr is not None:
            return self.az_file_format.format(seq_nr)
        return self.az_file_unnumbered

    def filmdata_file(self, film_id):
        return self.film_file_format.format(film_id)


class HtmlPageParser(web_tools.HtmlPageParser):

    def __init__(self, festival_data, debug_recorder, debug_prefix, debugging=False, encoding=None):
        web_tools.HtmlPageParser.__init__(self, debug_recorder, debug_prefix)
        self.debugging = debugging
        self.festival_data = festival_data
        if encoding is not None:
            self.print_debug(f'Encoding: {encoding}', '')

    def add_screening(self, film, screen, start_dt, end_dt, qa='', subtitles='', extra='',
                      audience='', program=None, display=True):

        # Print the screening properties.
        if display and audience == 'publiek':
            print()
            print(f"---SCREENING OF {film.title}")
            print(f"--  screen:     {screen}")
            print(f"--  start time: {start_dt}")
            print(f"--  end time:   {end_dt}")
            print(f"--  duration:   film: {film.duration_str()}  screening: {end_dt - start_dt}")
            print(f"--  audience:   {audience}")
            print(f"--  category:   {film.medium_category}")
            print(f"--  q and a:    {qa}")
            print(f"--  subtitles:  {subtitles}")

        # Create a new screening object.
        screening = Screening(film, screen, start_dt, end_dt, qa, extra, audience, program, subtitles)

        # Add the screening to the list.
        self.festival_data.screenings.append(screening)


if __name__ == "__main__":
    print("This module is not executable.")
