#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 7 22:24:00 2022

@author: maartenroos
"""
import inspect
import os
from html.parser import HTMLParser

from Shared.application_tools import comment
from Shared.planner_interface import Screening, write_lists


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
        for label, count in counter.count_by_label.items():
            print(f'{label}: {count}')

    # Write parsed information.
    write_lists(festival_data, write_film_list, write_other_lists)


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


class Counter:

    count_by_label = {}

    def __init__(self):
        pass

    def start(self, label):
        self.count_by_label[label] = 0

    def increase(self, label, do_raise=True):
        try:
            self.count_by_label[label] += 1
        except KeyError as e:
            if do_raise:
                raise e
            else:
                self.count_by_label[label] = 1

    def get(self, label, description=None):
        count = self.count_by_label[label]
        return f'{label}: {count}' if description is None else f'{count} {description}'


class ScreeningKey:

    def __init__(self, screening):
        self.screen = screening.screen
        self.start_dt = screening.start_datetime
        self.end_dt = screening.end_datetime

    def __str__(self):
        return "{} {}-{} in {}".format(
            self.start_dt.date().isoformat(),
            self.start_dt.time().isoformat(timespec='minutes'),
            self.end_dt.time().isoformat(timespec='minutes'),
            self.screen)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash((self.screen, self.start_dt, self.end_dt))


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

        def push(self, state):
            self.stack.append(state)
            self._print_debug(state)

        def pop(self):
            self.stack[-1:] = []
            self._print_debug(self.stack[-1])

        def change(self, state):
            self.stack[-1] = state
            self._print_debug(state)

        def state_is(self, state):
            return state == self.stack[-1]

        def state_in(self, states):
            return self.stack[-1] in states

    def __init__(self, debug_recorder, debug_prefix, debugging=False):
        HTMLParser.__init__(self)
        self.debug_recorder = debug_recorder
        self.debug_prefix = debug_prefix
        self.debugging = debugging

    @property
    def bar(self):
        return f'{40 * "-"} '

    def print_debug(self, str1, str2):
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

    def __init__(self, festival_data, debug_recorder, debug_prefix, debugging=False):
        BaseHtmlPageParser.__init__(self, debug_recorder, debug_prefix, debugging=debugging)
        self.festival_data = festival_data

        # Member variables to construct film article.
        self.description = None
        self.article_paragraphs = []
        self.article_paragraph = ''
        self.article = None

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

    def add_paragraph(self):
        self.article_paragraphs.append(self.article_paragraph)
        self.article_paragraph = ''

    def set_article(self):
        self.article = '\n\n'.join(self.article_paragraphs)

    def set_description_from_article(self, title):
        descr_threshold = 512

        if len(self.article_paragraphs) > 0:
            self.description = self.article_paragraphs[0]
            if len(self.description) > descr_threshold:
                self.description = self.description[:descr_threshold] + '…'
        else:
            self.description = title
            self.article = ''


if __name__ == "__main__":
    print("This module is not executable.")
