#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 7 22:24:00 2022

@author: maartenroos
"""
import datetime
import inspect
import os
from html.parser import HTMLParser

from Shared.application_tools import comment, config, broadcast
from Shared.planner_interface import Screening, write_lists, AUDIENCE_PUBLIC


def try_parse_festival_sites(parser, festival_data, error_collector, debug_recorder, festival=None, counter=None):
    # Set defaults when necessary.
    festival = 'festival' if festival is None else festival

    # Try parsing the websites.
    write_film_list = False
    write_other_lists = True
    try:
        parser(festival_data)
    except KeyboardInterrupt:
        comment('Interrupted from keyboard... exiting')
        write_other_lists = False
    except Exception as e:
        debug_recorder.write_debug()
        comment('Debug info printed.')
        raise e
    else:
        write_film_list = True

    # Announce that parsing is done.
    comment(f'Done loading {festival} data.')
    debug_recorder.write_debug()

    # Display errors when found.
    if error_collector.error_count() > 0:
        comment('Encountered some errors:')
        print(error_collector)

    # Display custom statistics.
    if counter is not None:
        comment('Custom statistics')
        print(f'{counter}')

    # Write parsed information.
    write_lists(festival_data, write_film_list, write_other_lists)


class FileKeeper:
    basedir = os.path.expanduser(f'~/{config()["Paths"]["FestivalRootDirectory"]}')
    common_data_dir = os.path.expanduser(f'~/{config()["Paths"]["CommonDataDirectory"]}')

    def __init__(self, festival, year, basedir=None):
        """
        Exposes a standard structure to keep the data belonging to a film festival.
        :param festival: The basename of the festival the file structure belongs to
        :param year: The edition year of the festival
        :param basedir: Force the root directory to differ from the standard, esp. for testing.
        """
        # Define directories.
        self.basedir = basedir or self.basedir
        self.festival_dir = os.path.join(self.basedir, f'{festival}')
        self.documents_dir = os.path.join(self.festival_dir, f'{festival}{year}')
        self.webdata_dir = os.path.join(self.documents_dir, '_website_data')
        self.plandata_dir = os.path.join(self.documents_dir, '_planner_data')
        self.interface_dir = os.path.join(self.documents_dir, 'FestivalPlan')

        # Define formats.
        self.generic_numbered_file_format = '{:03}.html'
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

    def film_webdata_file(self, film_id):
        return self.film_file_format.format(film_id)

    def numbered_webdata_file(self, prefix, webdata_id):
        postfix = self.generic_numbered_file_format.format(webdata_id)
        return os.path.join(self.webdata_dir, f'{prefix}_{postfix}')

    def paged_numbered_webdata_file(self, prefix, webdata_id, page_number):
        path = f'{prefix}_{webdata_id:03}_{page_number:02}.html'
        return os.path.join(self.webdata_dir, path)


class BaseHtmlPageParser(HTMLParser):

    class StateStack:

        def __init__(self, print_debug, state):
            self.print_debug = print_debug
            self.stack = [state]
            self._print_debug(state)

        def __str__(self):
            head = f'States of HtmlParser in web_tools.py:\n'
            states = '\n'.join([str(s) for s in self.stack])
            return head + states

        def _print_debug(self, new_state):
            frame = inspect.currentframe().f_back
            caller = frame.f_code.co_name if frame.f_code is not None else 'code'
            self.print_debug(f'Parsing state after {caller:6} is {new_state}', '')

        def state(self):
            return self.stack[-1]

        def push(self, state):
            self.stack.append(state)
            self._print_debug(state)

        def pop(self, depth=1):
            self.stack[-depth:] = []
            self._print_debug(self.stack[-1])

        def change(self, state):
            self.stack[-1] = state
            self._print_debug(state)

        def state_is(self, state):
            return state == self.stack[-1]

        def state_in(self, states):
            return self.stack[-1] in states

        def is_at_bottom(self):
            return len(self.stack) == 1

    def __init__(self, debug_recorder, debug_prefix, debugging=False):
        HTMLParser.__init__(self)
        self.debug_recorder = debug_recorder
        self.debug_prefix = debug_prefix
        self.debugging = debugging

    @property
    def bar(self):
        return f'{40 * "-"} '

    @staticmethod
    def headed_bar(header=''):
        return f'{header:-^72}'

    def draw_headed_bar(self, header_str):
        header = self.headed_bar(header=header_str)
        broadcast(header, self.debug_recorder)

    def print_debug(self, str1, str2=''):
        if self.debugging:
            self.debug_recorder.add(f'{self.debug_prefix}  {str1} {str2}')

    def handle_starttag(self, tag, attrs):
        if len(attrs) > 0:
            sep = f'\n{self.debug_prefix}   '
            extra = sep + sep.join([f'attr:  {attr}' for attr in attrs])
        else:
            extra = ''
        self.print_debug(f'Encountered a start tag: \'{tag}\'', extra)

    def handle_endtag(self, tag):
        self.print_debug('Encountered an end tag :', f'\'{tag}\'')

    def handle_data(self, data):
        self.print_debug('Encountered some data  :', f'\'{data}\'')

    def handle_comment(self, data):
        self.print_debug('Comment  :', data)

    def handle_decl(self, data):
        self.print_debug('Decl     :', data)


class HtmlPageParser(BaseHtmlPageParser):

    festival_data = None

    def __init__(self, festival_data, debug_recorder, debug_prefix, debugging=False):
        BaseHtmlPageParser.__init__(self, debug_recorder, debug_prefix, debugging=debugging)
        self.festival_data = festival_data

        # Remember the screening.
        self.screening = None

        # Member variables to construct film article.
        self.description = None
        self.article_paragraphs = []
        self.article_paragraph = ''
        self.article = None

    @staticmethod
    def get_screening_date_times(start_date, start_time, end_time):
        end_date = start_date if end_time > start_time else start_date + datetime.timedelta(days=1)
        start_dt = datetime.datetime.combine(start_date, start_time)
        end_dt = datetime.datetime.combine(end_date, end_time)
        return start_dt, end_dt

    def add_screening_from_fields(self, film, screen, start_dt, end_dt, qa='', subtitles='', extra='',
                                  audience='', sold_out=None, program=None, display=True):

        screening = Screening(film, screen, start_dt, end_dt, qa, extra, audience, program, subtitles, sold_out)
        self.add_screening(screening, display=display)

    def add_screening(self, screening, display=True):

        # Set member screening.
        self.screening = screening

        # Print the screening properties.
        film = screening.film
        start_dt = screening.start_datetime
        end_dt = screening.end_datetime
        if display and screening.audience == AUDIENCE_PUBLIC:
            print()
            print(f"---SCREENING OF {film.title}")
            print(f"--  screen:     {screening.screen}")
            print(f"--  start time: {start_dt}")
            print(f"--  end time:   {end_dt}")
            print(f"--  duration:   film: {film.duration_str()}  screening: {end_dt - start_dt}")
            print(f"--  audience:   {screening.audience}")
            print(f"--  category:   {film.medium_category}")
            print(f"--  q and a:    {screening.q_and_a}")
            print(f"--  subtitles:  {screening.subtitles}")

        # Add the screening to the list.
        self.festival_data.screenings.append(screening)

    def add_article_text(self, data):
        self.article_paragraph += data.replace('\n', ' ')

    def add_paragraph(self):
        if self.article_paragraph:
            self.article_paragraphs.append(self.article_paragraph)
        self.article_paragraph = ''

    def set_article(self):
        self.add_paragraph()
        self.article = '\n\n'.join(self.article_paragraphs)

    def set_description_from_article(self, title):
        descr_threshold = 512

        if len(self.article_paragraphs) > 0:
            self.description = self.article_paragraphs[0]
            if len(self.description) > descr_threshold:
                self.description = self.description[:descr_threshold] + '…'
        else:
            self.description = self.description or title
            self.article = ''


if __name__ == "__main__":
    print("This module is not executable.")
