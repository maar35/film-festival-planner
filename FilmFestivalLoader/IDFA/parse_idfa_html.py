#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load films, film information, screens and screenings from the IDFA 2020
website.

Created on Wed Nov  4 20:36:18 2020

@author: maarten
"""

import datetime
import os
import re
from enum import Enum, auto
from typing import Dict
from urllib.parse import urlparse

from Shared.application_tools import ErrorCollector, DebugRecorder, comment, Counter
from Shared.parse_tools import FileKeeper, HtmlPageParser, ScreeningKey, try_parse_festival_sites
from Shared.planner_interface import FestivalData, Screening, Film, FilmInfo, ScreenedFilm
from Shared.web_tools import UrlFile, iri_slug_to_url

# Parameters.
festival = 'IDFA'
festival_city = 'Amsterdam'
festival_year = 2023

# Files.
fileKeeper = FileKeeper(festival, festival_year)
debug_file = fileKeeper.debug_file

# URL information.
festival_hostname = 'https://festival.idfa.nl'
az_path = '/programma/?page=11&tabIndex=1'
section_path = '/programma/?page=1&tabIndex=2'
specials_path = '/nl/info/idfa-specials'

# Application tools.
error_collector = ErrorCollector()
debug_recorder = DebugRecorder(debug_file)
counter = Counter()

DEBUGGING = True
ALWAYS_DOWNLOAD = False


def main():
    # Initialize a festival data object.
    comment('Creating festival data object.')
    festival_data = IdfaData(fileKeeper.plandata_dir)

    # Set-up counters.
    counter.start('sections')
    counter.start('pathways')
    counter.start('film URLs')
    counter.start('film title')
    counter.start('sections with css data')
    counter.start('no description')

    # Try parsing the websites.
    try_parse_festival_sites(parse_idfa_sites, festival_data, error_collector, debug_recorder, festival, counter)


def parse_idfa_sites(festival_data):
    comment('Parsing section pages and film pages.')
    get_films(festival_data)

    # comment('Parsing special programs page.')
    # get_specials(festival_data)


def get_films(festival_data):
    section_url = festival_hostname + section_path
    section_file = os.path.join(fileKeeper.webdata_dir, 'sections.html')
    url_file = UrlFile(section_url, section_file, error_collector, debug_recorder, byte_count=200)
    section_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=f'Downloading {section_url}')
    if section_html:
        comment(f'Analysing sections page, encoding={url_file.encoding}')
        SectionsPageParser(festival_data).feed(section_html)


def get_films_by_section(festival_data, section_urls):
    for i, section_url in enumerate(section_urls):
        section_file = fileKeeper.numbered_webdata_file('section', i)
        url_file = UrlFile(section_url, section_file, error_collector, debug_recorder, byte_count=200)
        section_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD,
                                         comment_at_download=f'Downloading {section_url}')
        if section_html:
            comment(f'Analysing section page, encoding={url_file.encoding}')
            FilmsFromSectionPageParser(festival_data, section_url).feed(section_html)


class SectionsPageParser(HtmlPageParser):
    class SectionParseState(Enum):
        AWAITING_URL = auto()
        DONE = auto()

    def __init__(self, festival_date):
        super().__init__(festival_date, debug_recorder, 'S', debugging=DEBUGGING)
        self.section_urls = []
        self.pathway_urls = []
        self.stateStack = self.StateStack(self.print_debug, self.SectionParseState.AWAITING_URL)

    def add_section(self, url):
        self.section_urls.append(url)
        counter.increase('sections')

    def add_pathway(self, url):
        self.pathway_urls.append(url)
        counter.increase('pathways')

    def add_theme(self, slug):
        url = iri_slug_to_url(festival_hostname, slug)
        print(f'{url=}')
        theme = slug.split('/')[1]
        if theme == 'section':
            self.add_section(url)
        elif theme == 'pathways':
            self.add_pathway(url)
        else:
            error_collector.add('Unexpected theme', f'{theme}')

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.SectionParseState.AWAITING_URL):
            if tag == 'a':
                if len(attrs) == 2 and attrs[0][0] == 'class' and attrs[0][1] == 'css-avil9w' and attrs[1][0] == 'href':
                    self.add_theme(attrs[1][1])
            elif tag == 'footer':
                self.stateStack.change(self.SectionParseState.DONE)
                get_films_by_section(self.festival_data, self.section_urls)


class FilmsFromSectionPageParser(HtmlPageParser):
    class FilmsParseState(Enum):
        AWAITING_TITLE = auto()
        IN_TITLE = auto()
        AWAITING_DESCR = auto()
        IN_DESCR = auto()
        AWAITING_FILM_URL = auto()
        IN_FILM_URL = auto()
        AWAITING_FILM_TITLE = auto()
        IN_FILM_TITLE = auto()
        IN_FILM_PROPERTIES = auto()
        IN_FILM_PROPERTY = auto()
        DONE = auto()

    color_by_section_id = {
        1: 'DodgerBlue',
        2: 'PeachPuff',
        3: 'PeachPuff',
        4: 'DodgerBlue',
        5: 'PaleVioletRed',
        6: 'LightSalmon',
        7: 'HotPink',
        8: 'Khaki',
        9: 'SpringGreen',
        10: 'DarkSeaGreen',
        11: 'OliveDrab',
        12: 'Olive',
        13: 'SpringGreen',
        14: 'PeachPuff',
        15: 'DodgerBlue',
        16: 'PeachPuff',
        17: 'DarkMagenta',
        18: 'IndianRed',
        19: 'PaleVioletRed',
        20: 'SpringGreen',
        21: 'CadetBlue',
        22: 'PapayaWhip',
        23: 'Orchid',
        24: 'DarkSeaGreen',
        25: 'PaleVioletRed',
    }
    sections_by_film = {}

    def __init__(self, festival_data, section_url):
        super().__init__(festival_data, debug_recorder, 'FS', debugging=DEBUGGING)
        self.section_url = section_url
        self.section_name = None
        self.subsection = None

        # Initialize film data.
        self.film_url = None
        self.film_title = None
        self.film = None
        self.film_duration = None
        self.film_property_by_label = None
        self.metadata_key = None
        self.init_film_data()

        # Draw a bar with section info.
        url_obj = urlparse(section_url)
        url_parts = url_obj.path.split('/')
        theme_type = url_parts[1]
        slug = url_parts[3]
        print(f'{theme_type} {self.headed_bar(header=slug)}')
        self.print_debug(self.headed_bar(header=slug))

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.FilmsParseState.AWAITING_TITLE)

    def init_film_data(self):
        self.film_url = None
        self.film_title = None
        self.film = None
        self.film_duration = None
        self.film_property_by_label = {}
        self.metadata_key = None

    def reset_film_parsing(self):
        self.state_stack.pop()
        self.set_duration()
        self.add_film()
        self.init_film_data()

    def get_subsection(self, section_description=None):
        if self.section_name:
            section = self.festival_data.get_section(self.section_name)
            try:
                section.color = self.color_by_section_id[section.section_id]
            except KeyError as e:
                error_collector.add(e, f'No color for section {section.name}')
            subsection = self.festival_data.get_subsection(section.name, self.section_url, section)
            subsection.description = section_description or section.name
            print(f'{subsection=}')
            return subsection
        return None

    def add_film(self):
        # Create a new film.
        self.film = self.festival_data.create_film(self.film_title, self.film_url)
        if self.film is None:
            try:
                self.film = self.festival_data.get_film_by_key(self.film_title, self.film_url)
            except KeyError:
                error_collector.add(f'Could not create film:', f'{self.film_title} ({self.film_url})')
            else:
                self.sections_by_film[self.film].append(self.subsection)
        else:
            # Fill details.
            self.film.duration = self.film_duration
            self.film.subsection = self.subsection
            self.film.medium_category = Film.category_string_films
            self.sections_by_film[self.film] = [self.subsection]

            # Add the film to the list.
            print(f'Created film {self.film}')
            self.festival_data.films.append(self.film)

    def set_duration(self):
        try:
            film_length = self.film_property_by_label['length']
        except KeyError:
            minutes = 0
        else:
            minutes = int(film_length.split(' ')[0])  # '84 min'
        self.film_duration = datetime.timedelta(minutes=minutes)

    def add_sections_property(self):
        for film, sections in self.sections_by_film.items():
            self.film_property_by_label['sections'] = sections  # TODO: make this usefull.

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.FilmsParseState.AWAITING_TITLE) and tag == 'meta' and len(attrs) == 2:
            if attrs[0] == ('property', 'og:description') and attrs[1][0] == 'content':
                self.state_stack.change(self.FilmsParseState.IN_TITLE)
        elif self.state_stack.state_is(self.FilmsParseState.IN_TITLE) and tag == 'span' and len(attrs):
            if attrs[0][0] == 'title':
                self.section_name = attrs[0][1].strip()
                self.state_stack.change(self.FilmsParseState.AWAITING_DESCR)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_DESCR) and tag == 'div' and len(attrs) == 1:
            if attrs[0] == ('class', 'ey43j5h0 css-uu0j5i-Body-Body'):
                self.state_stack.change(self.FilmsParseState.IN_DESCR)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_FILM_URL) and tag == 'article' and len(attrs):
            if attrs[0] == ('class', 'eqiw4yk1 css-scrfvs-Container-Container'):
                self.state_stack.push(self.FilmsParseState.IN_FILM_URL)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_DESCR) and tag == 'article' and len(attrs):
            if attrs[0] == ('class', 'eqiw4yk1 css-scrfvs-Container-Container'):
                self.subsection = self.get_subsection()
                counter.increase('no description')
                self.state_stack.push(self.FilmsParseState.IN_FILM_URL)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_URL) and tag == 'a' and len(attrs):
            if attrs[0][0] == 'href':
                slug = attrs[0][1]
                self.film_url = iri_slug_to_url(festival_hostname, slug)
                counter.increase('film URLs')
                self.state_stack.change(self.FilmsParseState.AWAITING_FILM_TITLE)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_FILM_TITLE) and tag == 'h2' and len(attrs) == 3:
            if attrs[0] == ('variant', '4') and attrs[1] == ('clamp', '2'):
                self.state_stack.change(self.FilmsParseState.IN_FILM_TITLE)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTIES):
            if tag == 'div' and len(attrs) and attrs[0][0] == 'data-meta':
                self.metadata_key = attrs[0][1]
                self.state_stack.change(self.FilmsParseState.IN_FILM_PROPERTY)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_FILM_URL) and tag == 'footer':
            self.state_stack.change(self.FilmsParseState.DONE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTY) and tag == 'div':
            self.state_stack.change(self.FilmsParseState.IN_FILM_PROPERTIES)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTIES) and tag == 'div':
            self.reset_film_parsing()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.FilmsParseState.IN_DESCR):
            if not data.startswith('.css'):
                section_description = data
                self.subsection = self.get_subsection(section_description)
                self.state_stack.change(self.FilmsParseState.AWAITING_FILM_URL)
            else:
                counter.increase('sections with css data')
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_TITLE):
            self.film_title = data
            counter.increase('film title')
            self.state_stack.change(self.FilmsParseState.IN_FILM_PROPERTIES)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTY):
            self.film_property_by_label[self.metadata_key] = data


class AzPageParser(HtmlPageParser):
    class AzParseState(Enum):
        IDLE = auto()
        IN_FILM_SECTION = auto()

    def __init__(self, festival_data):
        super().__init__(festival_data, debug_recorder, 'AZ', debugging=DEBUGGING)
        self.film = None
        self.title = None
        self.url = None
        self.duration = None
        self.description = None
        self.stateStack = self.StateStack(self.print_debug, self.AzParseState.IDLE)
        self.init_film_data()

    def init_film_data(self):
        self.film = None
        self.title = None
        self.url = None
        self.duration = None
        self.description = None

    def add_filminfo(self, film, description, article, screened_films=None):
        if screened_films is None:
            screened_films = []
        if description is not None or article is not None:
            filminfo = FilmInfo(film.filmid, description, article, screened_films)
            self.festival_data.filminfos.append(filminfo)

    def get_film(self):
        get_film_details(self.festival_data, self.url)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.AzParseState.IDLE) and tag == 'article':
            self.stateStack.push(self.AzParseState.IN_FILM_SECTION)
        if self.stateStack.state_is(self.AzParseState.IN_FILM_SECTION) and tag == 'a':
            if len(attrs) > 1 and attrs[0][1] == 'collectionitem-module__link___2NQ6Q':
                slug = attrs[1][1]
                self.url = iri_slug_to_url(festival_hostname, slug)
                self.get_film()

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)


class FilmPageParser(HtmlPageParser):
    class FilmParseState(Enum):
        IDLE = auto()
        AWAITING_DICT = auto()
        IN_DICT = auto()
        AWAITING_TITLE = auto()
        IN_TITLE = auto()
        AWAITING_ARTICLE = auto()
        IN_ARTICLE = auto()
        AWAITING_SCREENINGS = auto()
        IN_SCREENINGS = auto()
        IN_SCREENING = auto()
        AWAITING_LOCATION = auto()
        IN_LOCATION = auto()
        IN_AUDIENCE = auto()
        DONE = auto()

    nl_month_by_name: Dict[str, int] = {'nov.': 11}
    re_dict = re.compile(r'"runtime":(?P<duration>\d+),')

    def __init__(self, festival_data, film_id, url, debug_prefix='F'):
        super().__init__(festival_data, debug_recorder, debug_prefix, debugging=DEBUGGING)
        self.film_id = film_id
        self.url = url
        self.title = None
        self.duration = None
        self.film = None

        self.start_dt = None
        self.end_dt = None
        self.screen = None
        self.audience_categories = None
        self.audience = None
        self.state_stack = self.StateStack(self.print_debug, self.FilmParseState.IDLE)
        self.init_screening_data()

    def init_screening_data(self):
        self.start_dt = None
        self.end_dt = None
        self.screen = None
        self.audience_categories = []
        self.audience = None

    def get_properties_from_dict(self, data):
        matches = self.re_dict.search(data)
        minutes = int(matches.group('duration')) if matches else 0
        self.duration = datetime.timedelta(minutes=minutes)

    def add_film(self):
        # Create a new film.
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            error_collector.add(f'Could not create film:', '{self.title} ({self.url})')
        else:
            # Fill details.
            self.film.duration = self.duration
            self.film.medium_category = Film.category_string_films

            # Add the film to the list.
            print(f'Created film {self.film}')
            self.festival_data.films.append(self.film)

    def add_paragraph(self):
        paragraph = self.article_paragraph
        if len(paragraph) > 0:
            self.article_paragraphs.append(paragraph.strip())
        self.article_paragraph = ''

    def set_article(self):
        self.article = '\n\n'.join(self.article_paragraphs)
        self.set_description_from_article(self.film.title)

    def add_film_info(self):
        film_info = FilmInfo(self.film.filmid, self.description, self.article)
        self.festival_data.filminfos.append(film_info)

    def set_screening_times(self, data):
        self.start_dt, self.end_dt = get_screening_times(data)

    def get_screen(self, data):
        screen_name = data.strip()
        screen = self.festival_data.get_screen(festival_city, screen_name)
        return screen

    def get_audience(self):
        no_audience_categories = len(self.audience_categories) == 0
        return Screening.audience_type_public if no_audience_categories else '|'.join(self.audience_categories)

    def add_idfa_screening(self, display=False):
        HtmlPageParser.add_screening_from_fields(self, self.film, self.screen, self.start_dt, self.end_dt,
                                                 audience=self.audience, display=display)
        self.init_screening_data()

    def handle_starttag(self, tag, attrs):
        ahead_audience = 'color:var(--background-color);background-color:var(--text-color)'

        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.FilmParseState.IDLE) and tag == 'script':
            self.state_stack.push(self.FilmParseState.IN_DICT)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_TITLE) and tag == 'h1':
            self.state_stack.change(self.FilmParseState.IN_TITLE)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_ARTICLE) and tag == 'section':
            if len(attrs) > 0 and attrs[0] == ('class', 'contentpanel-module__section___1qeQt'):
                self.state_stack.change(self.FilmParseState.IN_ARTICLE)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_SCREENINGS) and tag == 'section':
            if len(attrs) > 1 and attrs[0] == ('class', 'tickets-module__ticketBlock___3ROpA'):
                self.state_stack.change(self.FilmParseState.IN_SCREENINGS)
        elif self.state_stack.state_is(self.FilmParseState.IN_SCREENINGS):
            if tag == 'div' and len(attrs) > 0 and attrs[0][1] == 'table-module__name___3d5Hi':
                self.state_stack.push(self.FilmParseState.IN_SCREENING)
            elif tag == 'span' and len(attrs) > 1 and attrs[1] == ('style', ahead_audience):
                self.state_stack.push(self.FilmParseState.IN_AUDIENCE)
            elif tag == 'svg' and len(attrs) > 0 and attrs[0][0] == 'xmlns':
                self.audience = self.get_audience()
                self.add_idfa_screening()
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_LOCATION) and tag == 'div':
            if len(attrs) > 0 and attrs[0][1] == 'tickets-module__location___3qPel':
                self.state_stack.change(self.FilmParseState.IN_LOCATION)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_is(self.FilmParseState.IN_DICT):
            self.state_stack.change(self.FilmParseState.AWAITING_TITLE)
        elif self.state_stack.state_is(self.FilmParseState.IN_ARTICLE):
            if tag == 'p':
                self.add_paragraph()
            elif tag == 'section':
                self.set_article()
                self.add_film_info()
                self.state_stack.change(self.FilmParseState.AWAITING_SCREENINGS)
        elif self.state_stack.state_is(self.FilmParseState.IN_SCREENINGS) and tag == 'section':
            self.state_stack.change(self.FilmParseState.DONE)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.FilmParseState.IN_DICT):
            self.get_properties_from_dict(data)
        elif self.state_stack.state_is(self.FilmParseState.IN_TITLE):
            self.title = data
            self.add_film()
            self.state_stack.change(self.FilmParseState.AWAITING_ARTICLE)
        elif self.state_stack.state_is(self.FilmParseState.IN_ARTICLE):
            self.article_paragraph += data
        elif self.state_stack.state_is(self.FilmParseState.IN_SCREENING):
            self.set_screening_times(data)
            self.state_stack.change(self.FilmParseState.AWAITING_LOCATION)
        elif self.state_stack.state_is(self.FilmParseState.IN_LOCATION):
            self.screen = self.get_screen(data)
            self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmParseState.IN_AUDIENCE):
            self.audience_categories.append(data)
            self.state_stack.pop()


class SpecialsPageParser(HtmlPageParser):
    class SpecialsParseState(Enum):
        IDLE = auto()
        IN_SPECIALS = auto()
        IN_SPECIAL = auto()
        IN_TITLE = auto()
        IN_DESCRIPTION = auto()
        DONE = auto()

    combination_programs = []
    category_by_slug_part = {
        'film': Film.category_string_films,
        'shows': Film.category_string_combinations,
        'set': Film.category_string_combinations,
    }

    def __init__(self, festival_data):
        super().__init__(festival_data, debug_recorder, 'SP', debugging=DEBUGGING)
        self.title = None
        self.combination_program = None
        self.combination_type = None
        self.url = None
        self.state_stack = self.StateStack(self.print_debug, self.SpecialsParseState.IDLE)

    def init_combination_data(self):
        self.title = None
        self.description = None
        self.combination_program = None
        self.combination_type = None
        self.url = None

    def process_combination_slug(self, slug):
        parts = slug.split('/')[1:]
        combination_type = parts[1]
        if combination_type != 'info':
            self.url = iri_slug_to_url(festival_hostname, slug)
            self.combination_type = combination_type if parts[0] == 'nl' else None

    def add_combination(self):
        if self.url is not None:
            print(f'Adding combination program {self.title} ({self.url})')
            self.combination_program = self.festival_data.create_film(self.title, self.url)
            if self.combination_program is None:
                error_data = f'{self.title} ({self.url})'
                error_collector.add(f'Could not create combination program:', error_data)
            else:
                self.combination_program.duration = datetime.timedelta(seconds=0)
                self.combination_program.medium_category = self.category_by_slug_part[self.combination_type]
                self.combination_programs.append(self.combination_program)

                # Add the combination program to the list.
                self.festival_data.films.append(self.combination_program)

                # Add the film info.
                self.add_combination_info()

    def add_combination_info(self):
        article = ''
        if self.description is None:
            error_collector.add('Empty description', f'combination={self.combination_program}')
            return
        film_info = FilmInfo(self.combination_program.filmid, self.description, article)
        if film_info is None:
            error_collector.add('No film info created', f'Combination{self.combination_program}')
        else:
            self.festival_data.filminfos.append(film_info)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.SpecialsParseState.IDLE) and tag == 'div':
            if len(attrs) > 0 and attrs[0][1].endswith('module__navBlocks___x53JR'):
                self.state_stack.change(self.SpecialsParseState.IN_SPECIALS)
        elif self.state_stack.state_is(self.SpecialsParseState.IN_SPECIALS) and tag == 'h3':
            self.init_combination_data()
            self.state_stack.push(self.SpecialsParseState.IN_SPECIAL)
            self.state_stack.push(self.SpecialsParseState.IN_TITLE)
        elif self.state_stack.state_is(self.SpecialsParseState.IN_SPECIAL) and tag == 'p':
            self.state_stack.push(self.SpecialsParseState.IN_DESCRIPTION)
        elif self.state_stack.state_is(self.SpecialsParseState.IN_SPECIAL) and tag == 'a':
            if len(attrs) > 1 and attrs[1][0] == 'href':
                self.process_combination_slug(attrs[1][1])
                self.add_combination()
                self.init_combination_data()
                self.state_stack.pop()
        elif self.state_stack.state_is(self.SpecialsParseState.IN_SPECIALS) and tag == 'div':
            if len(attrs) > 0 and attrs[0][1].startswith('layout-module__wrapper'):
                self.state_stack.change(self.SpecialsParseState.DONE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.SpecialsParseState.IN_TITLE):
            self.title = data
            self.state_stack.pop()
        elif self.state_stack.state_is(self.SpecialsParseState.IN_DESCRIPTION):
            self.description = data
            self.state_stack.pop()


class SpecialFeaturePageParser(FilmPageParser):
    class FeatureParseState(Enum):
        IDLE = auto()
        IN_DESCRIPTION = auto()
        AWAITING_SCREENINGS = auto()
        IN_TIMES = auto()
        IN_LOCATION = auto()
        AWAITING_SCREENED_FILMS = auto()
        IN_SCREENED_FILMS = auto()
        IN_SCREENED_TITLE = auto()
        AWAITING_SCREENED_DESCRIPTION = auto()
        IN_SCREENED_DESCRIPTION = auto()
        AWAITING_SCREENED_URL = auto()
        DONE = auto()

    compilation_by_title = {}
    film_id_by_title = {}

    def __init__(self, festival_data, film):
        super().__init__(festival_data, film.filmid, film.url, 'SF')
        if not self.debugging:
            raise ValueError('Debugging not set')
        self.festival_data = festival_data
        self.film = film
        self.film_info = self.film.film_info(self.festival_data)
        self.compilation_url = film.url
        self.duration = None
        self.film_article = None
        self.screenings = []
        self.screened_films = []
        self.screened_description = None
        self.screened_title = None
        self.screened_url = None
        self.state_stack = self.StateStack(self.print_debug, self.FeatureParseState.IDLE)
        self.init_screened_film()
        self.film_id_by_title = {title: film_id for film_id, title in self.festival_data.title_by_film_id.items()}

    def init_screened_film(self):
        self.screened_title = None
        self.screened_description = None
        self.screened_url = None

    def add_film_article(self, article):
        self.film_info.article = article

    def add_screened_film(self):
        try:
            film = self.festival_data.get_film_by_key(self.screened_title, self.screened_url)
        except KeyError as key_error:
            try:
                film_id = self.film_id_by_title[self.screened_title]
            except KeyError:
                err_text = 'Title not found'
            else:
                f = self.festival_data.get_film_by_id(film_id)
                if f is not None:
                    err_text = f'film id={film_id}, title={f.title} url={f.url}'
                else:
                    err_text = f'Found a film id({film_id}), but it refers to nothing'
            error_collector.add(repr(key_error), f'Result of searching by title: {err_text}')
        except ValueError as value_error:
            error_collector.add(repr(value_error), f'Film ID found, but no corresponding film found in list')
        else:
            screened_film = ScreenedFilm(film.filmid, self.screened_title, self.screened_description)
            self.screened_films.append(screened_film)

    def add_screened_films(self):
        self.film_info.screened_films = self.screened_films
        for screened_film in self.screened_films:
            film_id = screened_film.filmid
            film = self.festival_data.get_film_by_id(film_id)
            film_info = film.film_info(self.festival_data)
            film_info.combination_films.append(self.film)
        screened_films_str = '\n'.join([str(screened_film) for screened_film in self.screened_films])
        print(f'Combination {self.film} linked to screened films:\n{screened_films_str}')

    def set_screening_times(self, data):
        self.start_dt, self.end_dt = get_screening_times(data)
        zero_td = datetime.timedelta(minutes=0)
        if self.film.duration is None or self.film.duration == zero_td:
            self.film.duration = self.end_dt - self.start_dt

    def handle_starttag(self, tag, attrs):
        ahead_screened_films = 'contentpanel-module__sectionTitle___Z2ucG contentpanel-module__collectionTitle___26a79'
        ahead_screened_film = 'collectionitem-module__title___1Cpb- type-module__title___2UQhK'
        ahead_screened_url = 'ButtonText__Container-sc-yfgqnf-0 kpnqEd'
        ahead_screened_description = 'collectionitem-module__description___2o688 type-module__copySmall___29O6A'

        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.FeatureParseState.IDLE) and tag == 'meta':
            if len(attrs) > 2 and attrs[1] == ('name', 'description') and attrs[2][0] == 'content':
                self.article = attrs[2][1]
                self.add_film_article(self.article)
                self.state_stack.change(self.FeatureParseState.AWAITING_SCREENINGS)
        elif self.state_stack.state_is(self.FeatureParseState.AWAITING_SCREENINGS) and tag == 'div':
            if len(attrs) > 0 and attrs[0] == ('class', 'table-module__name___3d5Hi'):
                self.state_stack.push(self.FeatureParseState.IN_TIMES)
        elif self.state_stack.state_is(self.FeatureParseState.AWAITING_SCREENED_FILMS) and tag == 'h2':
            if len(attrs) > 0 and attrs[0] == ('class', ahead_screened_films):
                self.state_stack.change(self.FeatureParseState.IN_SCREENED_FILMS)
        elif self.state_stack.state_is(self.FeatureParseState.IN_SCREENED_FILMS) and tag == 'h2':
            if len(attrs) > 0 and attrs[0] == ('class', ahead_screened_film):
                self.state_stack.push(self.FeatureParseState.IN_SCREENED_TITLE)
            elif len(attrs) == 0:
                self.add_screened_films()
                self.state_stack.pop()
                self.state_stack.change(self.FeatureParseState.DONE)
        elif self.state_stack.state_is(self.FeatureParseState.AWAITING_SCREENED_DESCRIPTION) and tag == 'p':
            if len(attrs) > 0 and attrs[0] == ('class', ahead_screened_description):
                self.state_stack.change(self.FeatureParseState.IN_SCREENED_DESCRIPTION)
        elif self.state_stack.state_is(self.FeatureParseState.AWAITING_SCREENED_URL) and tag == 'a':
            if len(attrs) > 2 and attrs[1] == ('class', ahead_screened_url) and attrs[2][0] == 'href':
                slug = attrs[2][1]
                self.screened_url = iri_slug_to_url(festival_hostname, slug)
                self.add_screened_film()
                self.init_screened_film()
                self.state_stack.pop()

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.FeatureParseState.IN_TIMES):
            self.set_screening_times(data)
            self.state_stack.change(self.FeatureParseState.IN_LOCATION)
        elif self.state_stack.state_is(self.FeatureParseState.IN_LOCATION):
            self.screen = self.get_screen(data)
            self.audience = self.get_audience()
            self.add_idfa_screening(display=True)
            self.state_stack.change(self.FeatureParseState.AWAITING_SCREENED_FILMS)
        elif self.state_stack.state_is(self.FeatureParseState.IN_SCREENED_TITLE):
            self.screened_title = data
            self.state_stack.change(self.FeatureParseState.AWAITING_SCREENED_DESCRIPTION)
        elif self.state_stack.state_is(self.FeatureParseState.IN_SCREENED_DESCRIPTION):
            self.screened_description = data
            self.state_stack.change(self.FeatureParseState.AWAITING_SCREENED_URL)


def get_films_az(festival_data):
    az_url = festival_hostname + az_path
    az_file = fileKeeper.az_file()
    url_file = UrlFile(az_url, az_file, error_collector, debug_recorder, byte_count=200)
    az_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=f'Downloading {az_url}', repeat=18)
    if az_html is not None:
        comment(f'Analysing az page, encoding={url_file.encoding}')
        AzPageParser(festival_data).feed(az_html)


def get_film_details(festival_data, url):
    comment(f'Parsing film detail url {url}')
    film_id = festival_data.new_film_id(url)
    film_file = fileKeeper.film_webdata_file(film_id)
    url_file = UrlFile(url, film_file, error_collector, debug_recorder, byte_count=200)
    film_html = url_file.get_text(f'Downloading film with ID {film_id} from {url}')
    if film_html is not None:
        print(f'Analysing HTML text, encoding={url_file.encoding}')
        FilmPageParser(festival_data, film_id, url, 'F').feed(film_html)
    else:
        error_collector.add('HTML text not found', f'Trying to add new film with ID {film_id}')


def get_specials(festival_data):
    # Read special features as films.
    specials_file = os.path.join(fileKeeper.webdata_dir, 'specials.html')
    specials_url = festival_hostname + specials_path
    url_file = UrlFile(specials_url, specials_file, error_collector, debug_recorder, byte_count=200)
    specials_html = url_file.get_text()
    if specials_html is not None:
        comment(f'Analysing specials page from {specials_file}, encoding={url_file.encoding}')
        SpecialsPageParser(festival_data).feed(specials_html)

    # Get details for all special features.
    combinations = SpecialsPageParser.combination_programs
    for combination in combinations:
        if combination.medium_category != Film.category_string_films:
            get_special_feature_details(festival_data, combination)

    # Print a summary.
    feature_count = len(combinations)
    features = '\n'.join([str(film) for film in combinations])
    comment(f'Found {feature_count} special features:\n{features}')


def get_special_feature_details(festival_data, combination_program):
    combination_file = fileKeeper.film_webdata_file(combination_program.filmid)
    url_file = UrlFile(combination_program.url, combination_file, error_collector, debug_recorder, byte_count=500)
    combination_html = url_file.get_text()
    if combination_html is not None:
        comment(f'Analysing special feature {combination_program}, encoding={url_file.encoding}')
        SpecialFeaturePageParser(festival_data, combination_program).feed(combination_html)


def get_screening_times(data):
    parts = data.split()  # 13 nov. 13:00 - 15:00 (14:00 - 16:00 AMS)
    day = int(parts[0])
    month = int(FilmPageParser.nl_month_by_name[parts[1]])
    start_time = datetime.time.fromisoformat(parts[5].strip('('))
    end_time = datetime.time.fromisoformat(parts[7])
    start_date = datetime.date(year=festival_year, month=month, day=day)
    end_date = start_date if end_time > start_time else start_date + datetime.timedelta(days=1)
    start_dt = datetime.datetime.combine(start_date, start_time)
    end_dt = datetime.datetime.combine(end_date, end_time)
    return start_dt, end_dt


class IdfaFilm(Film):

    def __init__(self, film):
        super().__init__(film.seqnr, film.filmid, film.title, film.url)
        self.section = None
        self.pathway = None

    def __lt__(self, other):
        self_is_alpha = self.re_alpha.match(self.sortstring) is not None
        other_is_alpha = self.re_alpha.match(other.sortstring) is not None
        if self_is_alpha and not other_is_alpha:
            return True
        if not self_is_alpha and other_is_alpha:
            return False
        return self.sortstring < other.sortstring


class IdfaScreening(Screening):
    def __init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience, combination_program_url):
        super().__init__(film, screen, start_datetime, end_datetime, qa, extra, audience)
        self.combination_program_url = combination_program_url


class IdfaData(FestivalData):

    def __init__(self, directory):
        super().__init__(directory, festival_city)
        self.compilation_by_url = {}

    def film_key(self, title, url):
        return url

    def is_coinciding(self, screening):
        # Get the film info.
        film_info = screening.film.film_info(self)

        # Check if the film is a combination program.
        screened_films = film_info.screened_films
        if len(screened_films):
            return False

        # Check if the film is screened as part of a combination
        # program.
        combination_films = film_info.combination_films
        if len(combination_films):
            key = ScreeningKey(screening)
            for combination_film in combination_films:
                for combination_screening in combination_film.screenings(self):
                    if key == ScreeningKey(combination_screening):
                        return True

        # This screening doesn't coincide with a combination program.
        return False

    def screening_can_go_to_planner(self, screening):
        can_go = screening.is_public()
        if can_go:
            can_go = not self.is_coinciding(screening)
        return can_go

    def film_can_go_to_planner(self, film_id):
        return True


if __name__ == "__main__":
    main()
