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
from Shared.parse_tools import FileKeeper, HtmlPageParser, try_parse_festival_sites
from Shared.planner_interface import FestivalData, Screening, Film, FilmInfo, ScreenedFilm, get_screen_from_parse_name, \
    ScreeningKey, AUDIENCE_PUBLIC
from Shared.web_tools import UrlFile, iri_slug_to_url

FESTIVAL = 'IDFA'
FESTIVAL_CITY = 'Amsterdam'
FESTIVAL_YEAR = 2025

HARDCODED_FILM_URLS = False
DEBUGGING = True
ALWAYS_DOWNLOAD = False
DISPLAY_SCREENING = True

# Files.
FILE_KEEPER = FileKeeper(FESTIVAL, FESTIVAL_YEAR)
PATHWAY_KEEPER = None
AZ_PAGE_COUNT = 1

# URL information.
FESTIVAL_HOSTNAME = 'https://festival.idfa.nl'
AZ_PATH = '/collectie/?A_TO_Z_TYPE=Publiek&A_TO_Z_TYPE=New+Media'       # '&page=9
# AZ_PATH = '/collectie/?A_TO_Z_TYPE=Publiek'
# PATHWAYS_PATH = 'https://festival.idfa.nl/festivalgids/wegwijzers/?utm_source=IDFA+Nieuwsbrieven&utm_campaign=da6f086be8-EMAIL_CAMPAIGN_2025_10_10_08_01&utm_medium=email&utm_term=0_-da6f086be8-69724581'
PATHWAYS_PATH = ('/festivalgids/wegwijzers/?utm_source=IDFA+Nieuwsbrieven'
                 '&utm_campaign=da6f086be8-EMAIL_CAMPAIGN_2025_10_10_08_01&utm_medium=email'
                 '&utm_term=0_-da6f086be8-69724581')
SECTIONS_PATH = '/festivalgids/competities-en-andere-programmas/'
SECTION_PATH = PATHWAYS_PATH
# SECTION_PATH = '/festivalgids/wegwijzers/'

# Application tools.
ERROR_COLLECTOR = ErrorCollector()
DEBUG_RECORDER = DebugRecorder(FILE_KEEPER.debug_file)
COUNTER = Counter()

COLOR_BY_SECTION_ID = {
    1: 'DodgerBlue',
    2: 'SpringGreen',
    3: 'red',
    4: 'BlueViolet',
    5: 'Teal',
    6: 'LightSalmon',
    7: 'HotPink',
    8: 'Khaki',
    9: 'LightSeaGreen',
    10: 'DarkSeaGreen',
    11: 'OliveDrab',
    12: 'Olive',
    13: 'hotPink',
    14: 'violet',
    15: 'limeGreen',
    16: 'fuchsia',
    17: 'DarkMagenta',
    18: 'IndianRed',
    19: 'PaleVioletRed',
    20: 'PaleVioletRed',
    21: 'CadetBlue',
    22: 'PapayaWhip',
    23: 'Orchid',
    24: 'royalBlue',
    25: 'rosyBrown',
    26: 'Bisque',
    27: 'PapayaWhip',
    28: 'PeachPuff',
    29: 'crimson',
    30: '',
}


def main():
    # Initialize a festival data object.
    comment('Creating festival data object.')
    festival_data = IdfaData(FILE_KEEPER.plandata_dir)

    # Setup counters.
    setup_counters()

    # Try parsing the websites.
    # PATHWAY_KEEPER = SectionsKeeper()
    try_parse_festival_sites(parse_idfa_sites, festival_data, ERROR_COLLECTOR, DEBUG_RECORDER, FESTIVAL, COUNTER)


def setup_counters():
    COUNTER.start('film URLs')
    COUNTER.start('film title')
    COUNTER.start('pathways')
    COUNTER.start('sections')
    COUNTER.start('subsection added')
    COUNTER.start('meta dicts')
    COUNTER.start('tickets available')

    # COUNTER.start('add film attempts')
    COUNTER.start('combinations')
    COUNTER.start('films')
    COUNTER.start('no description')
    COUNTER.start('articles')
    COUNTER.start('combination screenings')
    COUNTER.start('films not added')
    COUNTER.start('parsing failed')
    COUNTER.start('az-counters')

    # Counters that weren't active when hardcoding film URLs.
    COUNTER.start('sections with css data')
    COUNTER.start('corrected urls')
    COUNTER.start('improper dates')
    COUNTER.start('improper times')
    COUNTER.start('filminfo update')
    COUNTER.start('filminfo extended')


def parse_idfa_sites(festival_data):
    # if HARDCODED_FILM_URLS:
    #     comment(f'Parsing {FESTIVAL} {FESTIVAL_YEAR} pages.')
    #     parse_from_hardcoded_urls(festival_data)
    # else:

    # comment('Trying new AZ pege(s)')
    # load_az_pages(festival_data)

    # comment('Parsing section pages.')
    # get_pathways(festival_data, SECTIONS_PATH, 'sections.html')

    comment('Parsing pathway pages.')
    get_pathways(festival_data, PATHWAYS_PATH, 'pathways.html')

    comment(f'Listing the {len(SectionsKeeper.section_titles)} found sections')
    print(f'\n@@@ {"\n@@@ ".join([s for s in SectionsKeeper.section_titles])}')

    # comment('Parsing film pages')
    # FilmDetailsReader(festival_data).get_film_details()

    comment(f'Done parsing {FESTIVAL} {FESTIVAL_YEAR} pages.')
    # report_missing_films()


# def parse_from_hardcoded_urls(festival_data):
#     urls = [
#     ]
#     get_films(festival_data, urls)


# def report_missing_films():
#     for url, title in FilmEnumeratedPageParser.missing_film_by_url.items():
#         print(f'Not added: {title} ({url})')


def load_az_pages(festival_data):
    az_url_base = FESTIVAL_HOSTNAME + AZ_PATH
    for page_number in range(1, AZ_PAGE_COUNT + 1):
        debug_file = os.path.join(os.path.dirname(FILE_KEEPER.debug_file), f'debug_{page_number:02d}.txt')
        debugger = DebugRecorder(debug_file)
        az_file = FILE_KEEPER.az_file(page_number)
        az_url = az_url_base + f'&page={page_number}'
        url_file = UrlFile(az_url, az_file, ERROR_COLLECTOR, debugger)
        az_html = url_file.get_text(comment_at_download='Downloading AZ page.', always_download=ALWAYS_DOWNLOAD)
        if az_html:
            comment(f'Downloaded AZ page #{page_number}, encoding={url_file.encoding}, bytes={len(az_html)}')
            AzPageParser(festival_data, debugger).feed(az_html)
        debugger.write_debug()


# def get_films(festival_data, urls):
#     for i, url in enumerate(urls):
#         COUNTER.increase('film URLs')
#         film_file = os.path.join(FILE_KEEPER.webdata_dir, f'enumerated_film_page_{i:03d}.html')
#         url_file = UrlFile(url, film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
#         comment_at_download = f'Downloading enumerated film page #{i}'
#         film_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
#         if film_html:
#             FilmEnumeratedPageParser(festival_data, url).feed(film_html)


def get_pathways(festival_data, theme_path, target_file):
    pathway_url = FESTIVAL_HOSTNAME + theme_path
    pathway_file = os.path.join(FILE_KEEPER.webdata_dir, target_file)
    url_file = UrlFile(pathway_url, pathway_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
    comment_ = f'Downloading {pathway_url}'
    pathway_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_)
    if pathway_html:
        comment(f'Analysing sections page, encoding={url_file.encoding}')
        PathwaysPageParser(festival_data).feed(pathway_html)


def get_films_by_pathway(festival_data, pathway_urls):
    """Read the films from each of the given pathway URLs."""
    for i, pathway_url in enumerate(pathway_urls):
        pathway_file = FILE_KEEPER.numbered_webdata_file('pathway', i)
        url_file = UrlFile(pathway_url, pathway_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
        comment_ = f'Downloading {pathway_url} as to find the sections of the encountered films'
        pathway_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_)
        if pathway_html:
            comment(f'Analysing pathway page {i}, encoding={url_file.encoding}')
            FilmsFromPathwayPageParser(festival_data, pathway_url).feed(pathway_html)


def get_one_film(festival_data, title, url):
    comment(f'Parsing film details of {title} from {url}')
    film = festival_data.create_film(title, url)
    if film is None:
        ERROR_COLLECTOR.add(f'Could not create film:', f'{title} ({url})')
    else:
        # Fill details.
        film_file = FILE_KEEPER.film_webdata_file(film.film_id)
        url = film.url
        url_file = UrlFile(url, film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
        film_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD,
                                      comment_at_download=f'Downloading {film.url}')
        if film_html:
            print(f'Analysing film page, encoding={url_file.encoding}')
            # corrected_url = None if url == film.url else url
            FilmPageParser(festival_data, film).feed(film_html)


def get_readable_pathway_str(pathway_url):
    pathway_str = pathway_url.split('/')[-2]  # .replace('_', ' ')
    return pathway_str


def get_section_from_pathway_film(festival_data, title, url, pathway_url):
    """Store the sections of a film that was found in a pathway page."""
    # Check if the fim is already not loaded.
    try:
        _ = festival_data.get_film_by_key(title, url)
    except ValueError:
        pass
    else:
        comment(f'Existing film {title} not parsed.')
        return

    # Load the pathway film.
    comment(f'Parsing film {title} and storing sections.')
    pathway_film_id = SectionsKeeper.get_new_pathway_film_id(url)
    pathway_film_file = FILE_KEEPER.numbered_webdata_file('pathway_film', pathway_film_id)
    url_file = UrlFile(url, pathway_film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
    comment_at_download = f'Downloading pathway film {title} data from {url}'
    film_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
    if film_html:
        pathway_str = get_readable_pathway_str(pathway_url)
        print(f'Analysing page of "{title}" from {pathway_str} pathway, encoding={url_file.encoding}')
        PathwayFilmParser(festival_data, pathway_str, title, url).feed(film_html)


class SectionsKeeper:
    """Uses films found in pathways to support finding sections."""
    section_titles = set()
    section_title_by_url = {}
    pathway_film_id_by_url = {}
    pathway_film_id = 0

    @classmethod
    def get_new_pathway_film_id(cls, film_url):
        cls.pathway_film_id += 1
        cls.pathway_film_id_by_url[film_url] = cls.pathway_film_id
        return cls.pathway_film_id

    @classmethod
    def add_section_props(cls, section_title):
        if section_title in cls.section_titles:
            return False
        cls.section_titles.add(section_title)
        # cls.section_title_by_url[] = section_title
        COUNTER.increase('sections')
        return True


class PathwayFilmParser(HtmlPageParser):
    """Finds section link(s) in HTML of a film found in a specific pathway."""
    class PathwayFilmPageParseState(Enum):
        IDLE = auto()
        AWAITING_TITLE = auto()
        IN_TITLE = auto()
        AWAITING_META_DICT = auto()
        IN_META_DICT = auto()
        IN_META_PROPERTY = auto()
        AWAITING_TICKETS = auto()
        AWAITING_ARTICLE = auto()
        IN_ARTICLE = auto()
        IN_PARAGRAPH = auto()
        AWAITING_SECTION_URL = auto()
        IN_SECTION_URL = auto()
        DONE = auto()

    def __init__(self, festival_data, pathway_str, film_title, film_url):
        super().__init__(festival_data, DEBUG_RECORDER, 'PFP', debugging=DEBUGGING)
        self.festival_data = festival_data
        self.film_title = film_title
        self.film_url = film_url
        self.film_property_by_label = {'sections': []}
        self.film = None
        self.metadata_key = None
        self.section_title = None
        self.section_url = None
        self.subsection = None
        Film.category_by_string['film'] = Film.category_films

        self.headed_bar(f'PathwayFilmParser pathway {pathway_str}, film {film_title}')
        self.state_stack = self.StateStack(self.print_debug, self.PathwayFilmPageParseState.IDLE)

    def feed(self, data):
        super().feed(data)
        comment('Add the sections found to the pathway keeper.')
        sections = self.film_property_by_label['sections'] if self.film_property_by_label else []
        print(f'{", ".join([s for s in sections]) if sections else["No sections found"]}')
        DEBUG_RECORDER.add(f'{len(sections)} SECTIONS: {sections or "None"}')
        for section_title in self.film_property_by_label['sections']:
            _ = SectionsKeeper.add_section_props(section_title)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.PathwayFilmPageParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'script', _]:
                stack.push(state.AWAITING_TITLE)
            case [state.AWAITING_TITLE, 'h1', _]:
                stack.change(state.IN_TITLE)
            case [state.AWAITING_META_DICT | state.IN_META_DICT, 'div', a] if a and a[0][0] == 'data-meta':
                self.metadata_key = a[0][1]
                stack.change(state.IN_META_PROPERTY)
            case [state.AWAITING_ARTICLE, 'a', a] if len(a) > 1 and a[1] == ('href', '#tickets'):
                COUNTER.increase('tickets available')
            case [state.AWAITING_ARTICLE, 'div', a] if a and a[0] == ('class', 'ey43j5h0 css-gu30tp-Body-Body'):
                stack.change(state.IN_ARTICLE)
            case [state.IN_ARTICLE, 'p', a] if a and a[0][0] == 'index':
                stack.push(state.IN_PARAGRAPH)
            case [state.AWAITING_SECTION_URL, 'a', a] if len(a) > 1 and a[1][0] == 'href':
                self.section_url = FESTIVAL_HOSTNAME + a[1][1]
                self._add_section()
                self._add_film()
                stack.change(state.DONE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        stack = self.state_stack
        state = self.PathwayFilmPageParseState
        match [stack.state(), tag]:
            case [state.IN_TITLE, 'h1']:
                stack.change(state.AWAITING_META_DICT)
            case [state.IN_META_PROPERTY, 'div']:
                stack.change(state.IN_META_DICT)
            case [state.IN_META_DICT, 'div']:
                stack.change(state.AWAITING_ARTICLE)
            case [state.IN_PARAGRAPH, 'p']:
                self.add_paragraph()
                stack.pop()
            case [state.IN_ARTICLE, 'div']:
                stack.change(state.AWAITING_SECTION_URL)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        stack = self.state_stack
        state = self.PathwayFilmPageParseState
        match stack.state():
            case state.IN_META_PROPERTY:
                self._add_film_property(data.strip())
            case state.IN_PARAGRAPH:
                self.add_article_text(data)

    def _add_film_property(self, data):
        if self.metadata_key == 'sections':
            DEBUG_RECORDER.add(f'FOUND SECTIONS {data}')
            section_titles = [section_title.strip() for section_title in data.split(sep=',')]
            self.film_property_by_label['sections'].extend(section_titles)
            self.section_title = section_titles[0]      # TODO: handle case that titles > 1
        else:
            self.film_property_by_label[self.metadata_key] = data

    def _add_section(self):
        DEBUG_RECORDER.add(f'ADD SECTION {self.section_title}, {self.section_url}')
        section = self.festival_data.get_section(self.section_title, color_by_id=COLOR_BY_SECTION_ID)
        if section:
            COUNTER.increase('subsection added')
            self.subsection = self.festival_data.get_subsection(self.section_title, self.section_url, section)

    def _add_film(self):
        self.film = self.festival_data.create_film(self.film_title, self.film_url)
        if self.film is None:
            ERROR_COLLECTOR.add("Couldn't create film", f'{self.film_title}, {self.film_url}')
        else:
            # Fill details.
            self.film.duration = self._get_duration()
            self.film.subsection = self.subsection
            self.film.medium_category = self._get_medium_category()

            # Add the film to the list.
            self.festival_data.films.append(self.film)

            # Get the film info.
            self._add_film_info()

    def _add_film_info(self):
        # Set metadata.
        metadata = self.film_property_by_label
        if not metadata:
            ERROR_COLLECTOR.add('No metadata', f'film {self.film_title}')
            raise RuntimeError(f'No metadata in film {self.film_title}')

        # Add description and article.
        self.set_article()
        self.set_description_from_article(self.film.title)

        # Add film info.
        COUNTER.increase('meta dicts')
        film_info = FilmInfo(self.film.film_id, self.description, self.article, metadata=metadata)
        self.festival_data.filminfos.append(film_info)

    def _get_duration(self):
        duration_str = self.film_property_by_label['length']        # "96 min"
        minutes = int(duration_str.split()[0])
        return datetime.timedelta(minutes=minutes)

    def _get_medium_category(self):
        category_str = self.film_url.split('/')[3]
        # return Film.category_by_string[category_str]
        category_by_str = {'film': 'films'}
        return category_by_str[category_str]

# class FilmEnumeratedPageParser(HtmlPageParser):
#     class FilmParseState(Enum):
#         IDLE = auto()
#         AWAITING_TITLE = auto()
#         AFTER_TITLE = auto()
#         AWAITING_COMBINATION = auto()
#         IN_DESCRIPTION = auto()
#         AWAITING_METADATA = auto()
#         IN_METADATA = auto()
#         IN_METADATA_ITEM = auto()
#         AWAITING_ARTICLE = auto()
#         IN_ARTICLE = auto()
#         IN_PARAGRAPH = auto()
#         IN_STYLE = auto()
#         AWAITING_SCREENINGS = auto()
#         IN_DATE = auto()
#         IN_TIMES = auto()
#         IN_SCREEN = auto()
#         DONE = auto()
#
#     missing_film_by_url = {}
#     category_key_by_subdir = {
#         'film': 'films',
#         'composition': 'combinations',
#     }
#     nl_month_by_name = {'november': 11}
#     re_times = re.compile(r'\d\d\.\d\d–\d\d\.\d\d')
#
#     def __init__(self, festival_data, url):
#         HtmlPageParser.__init__(self, festival_data, DEBUG_RECORDER, 'FE', debugging=DEBUGGING)
#         self.screened_films = None
#         self.film = None
#         self.url = url
#         self.article = None
#         self.title = None
#         self.metadata_label = None
#         self.film_property_by_label = {}
#         self.medium_category = None
#         self.subsection = None
#         self.screening_date_str = None
#         self.screening_times_str = None
#         self.screen_name = None
#         self.sorting_from_site = False
#
#         # Draw a bar with the url.
#         self.print_debug(self.bar, f'Analysing film URL {self.url}')
#
#         # Initialize the state stack.
#         self.state_stack = self.StateStack(self.print_debug, self.FilmParseState.IDLE)
#
#         # Store known title languages.
#         Film.language_by_title['El árbol'] = 'es'
#         Film.language_by_title['El enemigo'] = 'es'
#         Film.language_by_title['El mar la mar'] = 'es'
#         Film.language_by_title['La Bonita'] = 'es'
#         Film.language_by_title['La despedida'] = 'es'
#         Film.language_by_title['de Volkskrantdag'] = 'nl'
#         Film.language_by_title['Los niños lobo'] = 'es'
#         Film.language_by_title['Los viejos heraldos'] = 'es'
#
#     def set_title(self, attr_value):
#         self.title = attr_value
#         COUNTER.increase('film title')
#
#     def get_subsection_from_sections(self):
#         url = FESTIVAL_HOSTNAME + SECTION_PATH
#
#         sections = []
#         try:
#             sections_str = self.film_property_by_label['sections']
#         except KeyError:
#             sections_str = None
#
#         if sections_str:
#             sections = sections_str.strip("'").split(', ')
#
#         subsection_name = sections[-1] if sections else None
#         try:
#             subsection = self.festival_data.subsection_by_name[subsection_name]
#         except KeyError:
#             section = self.festival_data.get_section(subsection_name, color='azure')
#             subsection = self.festival_data.get_subsection(subsection_name, url, section)
#
#         return subsection
#
#     def add_film(self):
#         # Create a new film.
#         COUNTER.increase('add film attempts')
#         self.film = self.festival_data.create_film(self.title, self.url)
#         if self.film is None:
#             ERROR_COLLECTOR.add(f'Could not create film:', f'{self.title} ({self.url})')
#         else:
#             # Fill medium category.
#             self.film.subsection = None
#             category_subdir = self.url.split('/')[3]
#             self.film.medium_category = self.category_key_by_subdir[category_subdir]
#
#             # Fill duration.
#             if self.film.medium_category == 'films':
#                 minutes = int(self.film_property_by_label['length'].split()[0])     # 207 min
#                 COUNTER.increase('films')
#             else:
#                 minutes = 0
#                 COUNTER.increase('combinations')
#             self.film.duration = datetime.timedelta(minutes=minutes)
#
#             # Get subsection.
#             self.film.subsection = self.get_subsection_from_sections()
#
#             # Add the film to the list.
#             self.festival_data.films.append(self.film)
#
#     def add_film_info(self):
#         descr_threshold = 256
#
#         # Construct description.
#         self.description = (self.description or self.article or '')
#         self.description or COUNTER.increase('no description')
#         self.article = self.article or self.description
#         if len(self.description) > descr_threshold:
#             self.description = self.description[:descr_threshold] + '…'
#         if self.article:
#             COUNTER.increase('articles')
#         else:
#             self.article = ''
#
#         # Set metadata.
#         metadata = self.film_property_by_label
#         if metadata:
#             COUNTER.increase('meta dicts')
#
#         # Add film info.
#         film_info = FilmInfo(self.film.film_id, self.description, self.article, metadata=metadata)
#         self.festival_data.filminfos.append(film_info)
#
#     def add_idfa_screening(self):
#         # Set times.
#         parts = self.screening_date_str.split()                     # vr 22 november
#         start_date = datetime.date(FESTIVAL_YEAR, self.nl_month_by_name[parts[2]], int(parts[1]))
#         data = self.screening_times_str
#         start_time = datetime.time(int(data[:2]), int(data[3:5]))   # 14.00–15.28
#         end_time = datetime.time(int(data[6:8]), int(data[9:]))
#         start_dt, end_dt = self.get_screening_date_times(start_date, start_time, end_time)
#
#         # Set film duration if applicable.
#         if not self.film.duration.total_seconds():
#             self.film.duration = end_dt - start_dt
#
#         # Set screen.
#         screen = IdfaScreening.get_idfa_screen(self.festival_data, self.screen_name)
#
#         # Add screening.
#         audience = Screening.audience_type_public
#         screening = IdfaScreening(self.film, screen, start_dt, end_dt, audience=audience)
#         self.add_screening(screening, display=DISPLAY_SCREENING)
#
#     def set_metadata_item(self, data):
#         self.film_property_by_label[self.metadata_label] = data
#
#     def handle_starttag(self, tag, attrs):
#         HtmlPageParser.handle_starttag(self, tag, attrs)
#         state = self.FilmParseState
#
#         match [self.state_stack.state(), tag, attrs]:
#             case [state.IDLE, 'title', _]:
#                 self.state_stack.push(state.AWAITING_TITLE)
#             case [state.AWAITING_TITLE, 'img', a] if a[0][0] == 'alt':
#                 self.set_title(attrs[0][1])
#                 self.state_stack.change(state.AFTER_TITLE)
#             case [state.AFTER_TITLE, 'div', a] if a[0] == ('variant', '3'):
#                 self.screened_films = []
#                 self.state_stack.change(state.AWAITING_COMBINATION)
#             case [state.AWAITING_COMBINATION, 'div', _]:
#                 self.state_stack.change(state.IN_DESCRIPTION)
#             case [state.AFTER_TITLE | state.IN_METADATA, 'div', a] if a and a[0][0] == 'data-meta':
#                 self.metadata_label = a[0][1]
#                 self.state_stack.change(state.IN_METADATA)
#                 self.state_stack.push(state.IN_METADATA_ITEM)
#             case [state.IDLE, 'p', a] if a and a[0] == ('index', '0'):
#                 self.state_stack.push(state.IN_ARTICLE)
#                 self.state_stack.push(state.IN_PARAGRAPH)
#             case [state.IN_ARTICLE, 'p', _]:
#                 self.state_stack.push(state.IN_PARAGRAPH)
#             case [state.IN_PARAGRAPH, 'style', _]:
#                 self.state_stack.push(state.IN_STYLE)
#             case [state.IDLE, 'div', a] if a and ('data-scheme-neutral', 'true') in a:
#                 self.state_stack.push(state.AWAITING_SCREENINGS)
#                 if not self.film:
#                     self.add_film()
#                     self.add_film_info()
#             case [state.AWAITING_SCREENINGS, 'div', a] if a and a[0] == ('variant', '4'):
#                 self.state_stack.push(state.IN_DATE)
#             case [state.AWAITING_SCREENINGS, 'div', a] if a and ('data-scheme-neutral', 'true') in a:
#                 self.state_stack.pop()
#             case [state.AWAITING_SCREENINGS, 'footer', _]:
#                 if not self.film:
#                     self.add_film()
#                     self.add_film_info()
#                 self.state_stack.pop()
#                 self.state_stack.change(state.DONE)
#             case [state.IDLE, 'footer', _]:
#                 if not self.film:
#                     self.add_film()
#                     self.add_film_info()
#                 self.state_stack.change(state.DONE)
#
#     def handle_endtag(self, tag):
#         HtmlPageParser.handle_endtag(self, tag)
#
#         match [self.state_stack.state(), tag]:
#             case [self.FilmParseState.IN_STYLE, 'style']:
#                 self.state_stack.pop()
#             case [self.FilmParseState.IN_PARAGRAPH, 'p']:
#                 if not self.article_paragraphs:
#                     self.description = self.article_paragraph
#                 self.add_paragraph()
#                 self.state_stack.pop()
#             case [self.FilmParseState.IN_ARTICLE, 'div']:
#                 self.set_article()
#                 self.state_stack.pop()
#             case [self.FilmParseState.IN_METADATA_ITEM, 'div']:
#                 self.state_stack.pop()
#             case [self.FilmParseState.IN_METADATA, 'div']:
#                 self.state_stack.pop()
#             case [state, 'footer'] if state != self.FilmParseState.DONE:
#                 if self.film:
#                     COUNTER.increase('parsing failed')
#                 else:
#                     COUNTER.increase('films not added')
#                     self.missing_film_by_url[self.url] = self.title
#
#     def handle_data(self, data):
#         HtmlPageParser.handle_data(self, data)
#         state = self.FilmParseState
#
#         match self.state_stack.state():
#             case state.IN_DESCRIPTION:
#                 self.description = data
#                 self.state_stack.pop()
#             case state.IN_METADATA_ITEM:
#                 self.set_metadata_item(data)
#             case state.IN_PARAGRAPH:
#                 self.article_paragraph += data
#             case state.IN_DATE:
#                 self.screening_date_str = data
#                 self.state_stack.change(state.IN_TIMES)
#             case state.IN_TIMES if self.re_times.match(data):
#                 self.screening_times_str = data
#                 self.state_stack.change(state.IN_SCREEN)
#             case state.IN_SCREEN if not data.startswith('.css'):
#                 self.screen_name = data
#                 self.add_idfa_screening()
#                 self.state_stack.pop()


class AzPageParser(HtmlPageParser):
    class AzParseState(Enum):
        IDLE = auto()
        IN_ARTICLE = auto()

    def __init__(self, festival_data, debugger=None):
        HtmlPageParser.__init__(self, festival_data, debugger or DEBUG_RECORDER, 'AZ', debugging=DEBUGGING)
        self.sorting_from_site = False
        self.film = None
        self.state_stack = self.StateStack(self.print_debug, self.AzParseState.IDLE)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.AzParseState.IDLE) and tag == 'article':
            self.state_stack.push(self.AzParseState.IN_ARTICLE)
            COUNTER.increase('az-counters')

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_is(self.AzParseState.IN_ARTICLE) and tag == 'article':
            self.state_stack.pop()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)


# class FilmDetailsReader:
#     def __init__(self, festival_data):
#         self.festival_data = festival_data
#
#     def get_film_details(self):
#         always_download = ALWAYS_DOWNLOAD
#         for film, sections in FilmsFromPathwayPageParser.sections_by_film.items():
#             comment(f'Parsing film details of {film.title}')
#             film_file = FILE_KEEPER.film_webdata_file(film.film_id)
#             url = film.url
#             url_file = UrlFile(url, film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
#             film_html = url_file.get_text(always_download=always_download,
#                                           comment_at_download=f'Downloading {film.url}')
#             if film_html:
#                 print(f'Analysing film page, encoding={url_file.encoding}')
#                 corrected_url = None if url == film.url else url
#                 FilmPageParser(self.festival_data, film, sections, corrected_url=corrected_url).feed(film_html)


class PathwaysPageParser(HtmlPageParser):
    """Parse the pathway overview page for pathway URLs."""
    class PathwayParseState(Enum):
        AWAITING_URL = auto()
        DONE = auto()

    def __init__(self, festival_date):
        super().__init__(festival_date, DEBUG_RECORDER, 'PW', debugging=DEBUGGING)
        self.section_urls = []
        self.pathway_urls = []
        self.state_stack = self.StateStack(self.print_debug, self.PathwayParseState.AWAITING_URL)

    def feed(self, data):
        super().feed(data)
        # comment('Finding films per section')
        # get_films_by_section(self.festival_data, self.section_urls)
        comment('Finding films per pathway')
        get_films_by_pathway(self.festival_data, self.pathway_urls)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        stack = self.state_stack
        state = self.PathwayParseState
        url_start = 'https://festival.idfa.nl/pathways'
        url_start_alt = 'https://festival.idfa.nl/nl/pathways'
        match [stack.state(), tag, attrs]:
            case [state.AWAITING_URL, 'a', a] if len(a) > 1 and a[1][1].startswith(url_start):
                self._add_theme(a[1][1])
            case [state.AWAITING_URL, 'a', a] if len(a) > 1 and a[1][1].startswith(url_start_alt):
                self._add_theme(a[1][1])
            case [state.AWAITING_URL, 'footer', _]:
                stack.change(state.DONE)

    def _add_pathway(self, url):
        self.pathway_urls.append(url)
        DEBUG_RECORDER.add(f'ADDING PATHWAY URL {url}')
        COUNTER.increase('pathways')

    def _add_section(self, url):
        self.section_urls.append(url)
        COUNTER.increase('sections')

    def _add_theme(self, url):
        theme = url.split('/')[-3]
        if theme == 'section':
            self._add_section(url)
        elif theme == 'pathways':
            self._add_pathway(url)
        else:
            ERROR_COLLECTOR.add('Unexpected theme', f'{theme}')


class FilmsFromPathwayPageParser(HtmlPageParser):
    """Laad the films from given pathway URL. Find the sections in each film."""
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

    sections_by_film = {}

    def __init__(self, festival_data, pathway_url):
        super().__init__(festival_data, DEBUG_RECORDER, 'FFP', debugging=DEBUGGING)
        self.pathway_url = pathway_url

        # Initialize film data.
        self.film_url = None
        self.film_title = None
        self.section_title = None
        self.section_name = None
        self.subsection = None
        self.film_property_by_label = None
        self.metadata_key = None
        # self.film = None
        # self.film_duration = None
        # self._init_film_data()

        # Draw a bar with section info.
        self.draw_headed_bar(get_readable_pathway_str(pathway_url))

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.FilmsParseState.AWAITING_TITLE)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        stack = self.state_stack
        state = self.FilmsParseState
        match [stack.state(), tag, attrs]:
            case [state.AWAITING_TITLE, 'title', _]:
                stack.change(state.IN_TITLE)
            case [state.AWAITING_DESCR, 'meta', a] if len(a) > 1 and a[0][1] == 'description':
                self.description = a[1][1]
                stack.change(state.AWAITING_FILM_URL)
            case [state.AWAITING_FILM_URL, 'a', a] if a and a[0][0] == 'href' and a[0][1].startswith(FESTIVAL_HOSTNAME):
                self.film_url = a[0][1]
                COUNTER.increase('film URLs')
                stack.change(state.AWAITING_FILM_TITLE)
            case [state.AWAITING_FILM_TITLE, 'img', a] if len(a) > 2 and a[0][0] == 'alt':
                self.film_title = a[0][1]
                self._read_film()
                stack.change(state.AWAITING_FILM_URL)
            case [state.AWAITING_FILM_URL, 'footer', _]:
                stack.change(state.DONE)

        # if stack.state_is(state.AWAITING_TITLE) and tag == 'meta' and len(attrs) == 2:
        #     if attrs[0] == ('property', 'og:description') and attrs[1][0] == 'content':
        #         stack.change(state.IN_TITLE)
        # elif stack.state_is(state.IN_TITLE) and tag == 'span' and len(attrs):
        #     if attrs[0][0] == 'title':
        #         self.section_name = attrs[0][1].strip()
        #         stack.change(state.AWAITING_DESCR)
        # elif stack.state_is(state.AWAITING_DESCR) and tag == 'div' and len(attrs) == 1:
        #     if attrs[0] == ('class', 'ey43j5h0 css-uu0j5i-Body-Body'):
        #         stack.change(state.IN_DESCR)
        # elif stack.state_is(state.AWAITING_FILM_URL) and tag == 'article' and len(attrs):
        #     if attrs[0] == ('class', 'eqiw4yk1 css-scrfvs-Container-Container'):
        #         stack.push(state.IN_FILM_URL)
        # elif stack.state_is(state.AWAITING_DESCR) and tag == 'article' and len(attrs):
        #     if attrs[0] == ('class', 'eqiw4yk1 css-scrfvs-Container-Container'):
        #         self.subsection = self.get_subsection()
        #         COUNTER.increase('no description')
        #         stack.push(state.IN_FILM_URL)
        # elif stack.state_is(state.IN_FILM_URL) and tag == 'a' and len(attrs):
        #     if attrs[0][0] == 'href':
        #         slug = attrs[0][1]
        #         self.film_url = FESTIVAL_HOSTNAME + slug    # Use literal slug, iri codes are not well understood.
        #         # COUNTER.increase('film URLs')
        #         stack.change(state.AWAITING_FILM_TITLE)
        # elif stack.state_is(state.AWAITING_FILM_TITLE) and tag == 'h2' and len(attrs) == 3:
        #     if attrs[0] == ('variant', '4') and attrs[1] == ('clamp', '2'):
        #         stack.change(state.IN_FILM_TITLE)
        # elif stack.state_is(state.IN_FILM_PROPERTIES):
        #     if tag == 'div' and len(attrs) and attrs[0][0] == 'data-meta':
        #         self.metadata_key = attrs[0][1]
        #         stack.change(state.IN_FILM_PROPERTY)
        # elif stack.state_is(state.AWAITING_FILM_URL) and tag == 'footer':
        #     stack.change(state.DONE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        stack = self.state_stack
        state = self.FilmsParseState
        match [stack.state(), tag]:
            case [state.IN_TITLE, 'title']:
                stack.change(state.AWAITING_DESCR)

        if stack.state_is(state.IN_FILM_PROPERTY) and tag == 'div':
            stack.change(state.IN_FILM_PROPERTIES)
        elif stack.state_is(state.IN_FILM_PROPERTIES) and tag == 'div':
            self.reset_film_parsing()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        stack = self.state_stack
        state = self.FilmsParseState
        match stack.state():
            case state.IN_TITLE:
                self.section_title = data.split('|')[-1].strip()

        # if stack.state_is(state.IN_DESCR):
        #     if not data.startswith('.css'):
        #         section_description = data
        #         self.subsection = self._get_subsection(section_description)
        #         stack.change(state.AWAITING_FILM_URL)
        #     else:
        #         COUNTER.increase('sections with css data')
        # elif stack.state_is(state.IN_FILM_TITLE):
        #     self.film_title = data
        #     COUNTER.increase('film title')
        #     stack.change(state.IN_FILM_PROPERTIES)
        # elif stack.state_is(state.IN_FILM_PROPERTY):
        #     self.film_property_by_label[self.metadata_key] = data

    def _read_film(self):
        comment(f'About to parse film {self.film_title} from {self.film_url}')
        # get_one_film(self.festival_data, self.film_title, self.film_url)
        get_section_from_pathway_film(self.festival_data, self.film_title, self.film_url, self.pathway_url)
        self._init_film_data()

    def _init_film_data(self):
        self.film_url = None
        self.film_title = None
        self.section_title = None
        self.section_name = None
        self.subsection = None
        self.film_property_by_label = {}
        self.metadata_key = None
        # self.film = None
        # self.film_duration = None

    def reset_film_parsing(self):
        DEBUG_RECORDER.add('RESET FILM PARSING, is pop() OK?')
        self.state_stack.pop()
        # self.set_duration()
        # self.add_film()
        self._init_film_data()

    def draw_headed_bar(self, section_str):
        print(f'{self.headed_bar(header=section_str)}')
        self.print_debug(self.headed_bar(header=section_str))

    def _get_subsection(self, section_description=None):
        if self.section_name:
            section = self.festival_data.get_section(self.section_name)
            try:
                section.color = COLOR_BY_SECTION_ID[section.section_id]
            except KeyError as e:
                ERROR_COLLECTOR.add(e, f'No color for section {section.name}')
            subsection = self.festival_data.get_subsection(section.name, self.pathway_url, section)
            subsection.description = section_description or section.name
            return subsection
        return None

    # def add_film(self):
    #     # Create a new film.
    #     self.film = self.festival_data.create_film(self.film_title, self.film_url)
    #     if self.film is None:
    #         try:
    #             self.film = self.festival_data.get_film_by_key(self.film_title, self.film_url)
    #         except KeyError:
    #             ERROR_COLLECTOR.add(f'Could not create film:', f'{self.film_title} ({self.film_url})')
    #         else:
    #             self.sections_by_film[self.film].append(self.subsection)
    #     else:
    #         # Fill details.
    #         self.film.duration = self.film_duration
    #         self.film.subsection = self.subsection
    #         self.film.medium_category = Film.category_by_string['films']
    #         self.sections_by_film[self.film] = [self.subsection]
    #
    #         # Add the film to the list.
    #         self.festival_data.films.append(self.film)

    # def set_duration(self):
    #     try:
    #         film_length = self.film_property_by_label['length']
    #     except KeyError:
    #         minutes = 0
    #     else:
    #         minutes = int(film_length.split(' ')[0])  # '84 min'
    #     self.film_duration = datetime.timedelta(minutes=minutes)


class FilmPageParser(HtmlPageParser):
    class FilmParseState(Enum):
        IDLE = auto()
        AWAITING_TITLE = auto()
        IN_TITLE = auto()
        AWAITING_META_DICT = auto()
        IN_META_DICT = auto()
        IN_META_PROPERTY = auto()
        AWAITING_PAGE_SECTION = auto()
        IN_PAGE_SECTION = auto()
        AWAITING_ARTICLE = auto()
        IN_ARTICLE = auto()
        AWAITING_SCREENINGS = auto()
        IN_SCREENINGS = auto()
        IN_SCREENING_DATE = auto()
        AWAITING_SCREENING_INFO = auto()
        IN_SCREENING_INFO = auto()
        AWAITING_TIMES = auto()
        IN_TIMES = auto()
        AWAITING_LOCATION = auto()
        IN_LOCATION = auto()
        AWAITING_CREDITS = auto()
        IN_DICT = auto()
        IN_PROPERTY = auto()
        DONE = auto()

    # Instead of developing a new SpecialsPageParser, link special titles
    # and urls by hand.
    url_by_combi_title = {
    }

    re_desc = re.compile(r'(?P<title>.*), (?P<desc>[A-Z].*\.)$')
    re_num_screen = re.compile(r'^(?P<theater>.*?)\s+(?P<number>\d+)$')
    re_colon_screen = re.compile(r'^(?P<theater>.*?):\s+(?P<room>.+)$')
    nl_month_by_name: Dict[str, int] = {'november': 11}

    # def __init__(self, festival_data, film, sections, debug_prefix='F', corrected_url=None):
    def __init__(self, festival_data, empty_film, debug_prefix='F', corrected_url=None):
        super().__init__(festival_data, DEBUG_RECORDER, debug_prefix, debugging=DEBUGGING)
        self.title = empty_film.title
        self.film_title = empty_film.title
        self.film_url = empty_film.url
        self.film = empty_film
        # self.film = film
        # self.sections = sections
        self.corrected_url = corrected_url
        self.film_property_by_label = {}
        self.film_info = None
        self.duration = None

        # Initialize screening data.
        self.metadata_key = None
        self.start_date = None
        self.start_dt = None
        self.end_dt = None
        self.screen = None
        self.qa = None
        self.audience = None
        self.extra = None
        self.combi_title = None
        self._init_screening_data()

        # Draw a bar with section info.
        self.print_debug(self.headed_bar(header=self.film_title))
        # self.print_debug(self.headed_bar(header=str(self.film)))
        if corrected_url:
            COUNTER.increase('corrected urls')

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.FilmParseState.IDLE)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        stack = self.state_stack
        state = self.FilmParseState
        if stack.state_is(state.IDLE) and tag == 'script':
            stack.push(state.AWAITING_TITLE)
        elif stack.state_is(state.AWAITING_TITLE) and tag == 'h1':
            stack.change(state.IN_TITLE)
        elif stack.state_in([
                state.AWAITING_META_DICT,
                state.IN_META_DICT,
                state.AWAITING_CREDITS]):
            if tag == 'div' and len(attrs) and attrs[0][0] == 'data-meta':
                self.metadata_key = attrs[0][1]
                stack.change(state.IN_META_PROPERTY)
        elif stack.state_is(state.AWAITING_PAGE_SECTION) and tag in ['div', 'h2']:
            if len(attrs) == 2 and attrs[0] == ('variant', '3'):
                if attrs[1] == ('class', 'e10q2t3u0 css-1bg59lt-Heading-Heading-Heading'):
                    stack.push(state.IN_PAGE_SECTION)
        elif stack.state_is(state.AWAITING_ARTICLE) and tag == 'p':
            stack.change(state.IN_ARTICLE)
        elif stack.state_is(state.AWAITING_SCREENINGS) and tag == 'div':
            if len(attrs) == 2 and attrs[0] == ('variant', '4'):
                stack.change(state.IN_SCREENINGS)
                stack.push(state.IN_SCREENING_DATE)
        elif stack.state_is(state.AWAITING_SCREENING_INFO) and tag == 'div':
            if len(attrs) and attrs[0] == ('class', 'ey43j5h0 css-1cky3te-Body-Body'):
                stack.change(state.IN_SCREENING_INFO)
        elif stack.state_is(state.AWAITING_TIMES) and tag == 'span':
            stack.change(state.IN_TIMES)
        elif stack.state_is(state.IN_SCREENINGS) and tag == 'div' and len(attrs) == 2:
            if attrs[0] == ('variant', '4'):
                stack.push(state.IN_SCREENING_DATE)
            elif attrs[0] == ('variant', '3'):
                stack.change(state.IN_PAGE_SECTION)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        stack = self.state_stack
        state = self.FilmParseState
        if stack.state_is(state.IN_META_PROPERTY) and tag == 'div':
            stack.change(state.IN_META_DICT)
        elif stack.state_is(state.IN_META_DICT) and tag == 'div':
            print(f'{self.film_property_by_label=}')
            self.print_debug('FOUND DICT', f'{self.film_property_by_label=}')
            stack.change(state.AWAITING_PAGE_SECTION)
        elif stack.state_is(state.IN_DICT):
            stack.change(state.AWAITING_TITLE)
        elif stack.state_is(state.IN_ARTICLE):
            if tag == 'p':
                self.add_paragraph()
            elif tag == 'div':
                self.set_article()
                self.add_film_info()
                stack.pop()
        elif stack.state_is(state.IN_SCREENING_INFO) and tag == 'div':
            stack.change(state.AWAITING_TIMES)
        elif stack.state_is(state.AWAITING_LOCATION) and tag == 'svg':
            stack.change(state.IN_LOCATION)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        stack = self.state_stack
        state = self.FilmParseState
        if stack.state_is(state.IN_TITLE):
            self.title = data
            if self.film_title != self.title:
                error_desc = f'"{self.title}" while parsing "{self.film_title}"'
                debug_text = '\n'.join([
                    error_desc,
                    f'{"registered url":-<20}{self.film_url}',
                    f'{"corrected url":-<20}{self.corrected_url}',
                ])
                ERROR_COLLECTOR.add('DIFFERENT TITLE', error_desc)
                self.print_debug(f'DIFFERENT TITLE: {debug_text}')
            stack.change(state.AWAITING_META_DICT)
        elif stack.state_is(state.IN_META_PROPERTY):
            self.film_property_by_label[self.metadata_key] = data
        elif stack.state_is(state.IN_PAGE_SECTION):
            if data == 'Synopsis':
                stack.change(state.AWAITING_ARTICLE)
            elif data.startswith('Tickets'):
                stack.change(state.AWAITING_SCREENINGS)
            elif data == 'Credits':
                stack.change(state.AWAITING_CREDITS)
            elif data == 'Stills':
                self.update_film_info()
                stack.change(state.DONE)
        elif stack.state_is(state.IN_SCREENING_INFO):
            self.process_screening_info(data)
        elif stack.state_is(state.IN_ARTICLE):
            if not data.startswith('.css'):
                self.article_paragraph += data
        elif stack.state_is(state.IN_SCREENING_DATE):
            if self.set_screening_date(data):
                stack.change(state.AWAITING_SCREENING_INFO)
            else:
                stack.pop()
        elif stack.state_is(state.IN_TIMES):
            if self.set_screening_times(data):
                stack.change(state.AWAITING_LOCATION)
            else:
                stack.pop()
        elif stack.state_is(state.IN_LOCATION):
            self.screen = self.get_idfa_screen(data)
            self.add_idfa_screening(True)
            stack.pop()

    def add_paragraph(self):
        paragraph = self.article_paragraph
        if len(paragraph) > 0:
            self.article_paragraphs.append(paragraph.strip())
        self.article_paragraph = ''

    def set_article(self):
        self.article = '\n\n'.join(self.article_paragraphs)
        self.set_description_from_article(self.film_title)
        COUNTER.increase('articles')

    def _init_screening_data(self):
        self.metadata_key = None
        self.start_date = None
        self.start_dt = None
        self.end_dt = None
        self.screen = None
        self.qa = ''
        self.audience = AUDIENCE_PUBLIC
        self.extra = ''
        self.combi_title = None

    def add_film_info(self):
        self.film_info = FilmInfo(self.film.film_id, self.description, self.article)
        self.festival_data.filminfos.append(self.film_info)

    def update_film_info(self):
        COUNTER.increase('filminfo update')
        if self.film_property_by_label:
            COUNTER.increase('meta dicts')
            properties = [f'{key}: {value}' for (key, value) in self.film_property_by_label.items()]
            metadata = '\n'.join(properties)
            self.film_info.article += f'\n\n{metadata}'
            COUNTER.increase('filminfo extended')

    def set_screening_date(self, data):
        parts = data.split()  # '10 november'
        try:
            day = int(parts[0])
            month = int(FilmPageParser.nl_month_by_name[parts[1]])
        except ValueError as e:
            COUNTER.increase('improper dates')
            self.print_debug(f'{e} in {self.film_title}', 'Proceeding to next page section')
            return False
        else:
            self.start_date = datetime.date(day=day, month=month, year=FESTIVAL_YEAR)
        return True

    def set_screening_times(self, data):
        try:
            start_time = datetime.time(int(data[:2]), int(data[3:5]))   # '14.00–15.28'
            end_time = datetime.time(int(data[6:8]), int(data[9:]))
        except ValueError as e:
            COUNTER.increase('improper times')
            self.print_debug(f'{e} in times of {self.film} screening', 'Proceeding to next page section')
            return False
        else:
            start_date = self.start_date
            self.start_dt, self.end_dt = self.get_screening_date_times(start_date, start_time, end_time)
        return True

    def get_idfa_screen(self, data):
        screen_parse_name = data.strip()
        return get_screen_from_parse_name(self.festival_data, screen_parse_name, self.split_location)

    def split_location(self, location):
        city_name = FESTIVAL_CITY
        theater_parse_name = location
        screen_abbreviation = 'zaal'
        colon_match = self.re_colon_screen.match(location)
        if colon_match:
            theater_parse_name = colon_match.group(1)
            screen_abbreviation = colon_match.group(2)
        else:
            num_match = self.re_num_screen.match(location)
            if num_match:
                theater_parse_name = num_match.group(1)
                screen_abbreviation = num_match.group(2)
        return city_name, theater_parse_name, screen_abbreviation

    def process_screening_info(self, data):
        qa_words = ['gesprek', 'Q&amp;A', 'Talk', 'nagesprek']
        private_words = ['Exclusief', 'Pashouders']
        part_of_prefix = 'Onderdeel van'
        self.qa = 'QA' if len([w for w in qa_words if w in data]) else ''
        self.audience = 'private' if len([w for w in private_words if w in data]) else AUDIENCE_PUBLIC
        if data.startswith(part_of_prefix):
            self.combi_title = data[len(part_of_prefix):].strip()
            self.print_debug('FOUND COMBINATION TITLE', f'{self.combi_title}')

    def add_idfa_screening(self, display=False):
        # Create an IDFA screening from the gathered data.
        self.screening = IdfaScreening(self.film, self.screen, self.start_dt, self.end_dt,
                                       qa=self.qa, audience=self.audience, extra=self.extra,
                                       combi_title=self.combi_title)
        self.add_screening(self.screening, display=display)

        # Prepare combination film data if applicable.
        if self.combi_title in self.url_by_combi_title.keys():
            self.screening.combi_url = self.url_by_combi_title[self.combi_title]
            m = re.match(self.re_desc, self.combi_title)
            if m:
                g = m.groupdict()
                self.combi_title = g['title']
                print(f"{g['title']:-<80}{g['desc']}")
            self.set_combination(self.screening)

        # Reset data as to find the next screening.
        self._init_screening_data()

    def set_combination(self, screening):
        combi_url = screening.combi_url

        # Get the combination film or create it.
        combi_film = self.festival_data.create_film(self.combi_title, combi_url)
        if combi_film is None:
            try:
                combi_film = self.festival_data.get_film_by_key(self.combi_title, combi_url)
            except KeyError:
                ERROR_COLLECTOR.add(f'Could not create combination film:', f'{self.combi_title} ({combi_url})')
                return
        else:
            combi_film.duration = screening.end_datetime - screening.start_datetime
            combi_film.medium_category = Film.category_by_string['combinations']
            self.festival_data.films.append(combi_film)
        combi_screening = IdfaScreening(
            combi_film, screening.screen, screening.start_datetime, screening.end_datetime, audience=AUDIENCE_PUBLIC
        )
        if combi_screening not in combi_film.screenings(self.festival_data):
            self.festival_data.screenings.append(combi_screening)
            COUNTER.increase('combination screenings')

        # Update the combination film info.
        combi_film_info = combi_film.film_info(self.festival_data)
        screened_film_info = self.film.film_info(self.festival_data)
        if not combi_film_info.film_id:
            combi_film_info.film_id = combi_film.film_id
            combi_film_info.description = self.combi_title
            self.festival_data.filminfos.append(combi_film_info)
        if self.film.film_id not in [sf.film_id for sf in combi_film_info.screened_films]:
            screened_film = ScreenedFilm(self.film.film_id, self.film_title, screened_film_info.description)
            combi_film_info.screened_films.append(screened_film)

        # Update the screened film info.
        if combi_film.film_id not in [cf.film_id for cf in screened_film_info.combination_films]:
            screened_film_info.combination_films.append(combi_film)


class IdfaScreening(Screening):
    re_num_screen = re.compile(r'^(?P<theater>.*?)\s+(?P<number>\d+)$')
    re_colon_screen = re.compile(r'^(?P<theater>.*?):\s+(?P<room>.+)$')

    def __init__(self, film, screen, start_datetime, end_datetime, qa='', extra='', audience=None,
                 combi_url=None, combi_title=None):
        super().__init__(film, screen, start_datetime, end_datetime, qa, extra, audience)
        self.in_combi = None

        # Support potentially usable code.
        self.combi_title = combi_title
        self.combi_url = combi_url

    @classmethod
    def get_idfa_screen(cls, festival_data, data):
        screen_parse_name = data.strip()
        return get_screen_from_parse_name(festival_data, screen_parse_name, cls.split_location)

    @classmethod
    def split_location(cls, location):
        city_name = FESTIVAL_CITY
        theater_parse_name = location
        screen_abbreviation = 'zaal'
        colon_match = cls.re_colon_screen.match(location)
        if colon_match:
            theater_parse_name = colon_match.group(1)
            screen_abbreviation = colon_match.group(2)
        else:
            num_match = cls.re_num_screen.match(location)
            if num_match:
                theater_parse_name = num_match.group(1)
                screen_abbreviation = num_match.group(2)
        return city_name, theater_parse_name, screen_abbreviation

    def film_is_combi(self):
        return self.film.medium_category == 'combinations'


class IdfaData(FestivalData):
    duplicates_by_screening = {}

    def __init__(self, directory, common_data_dir=None):
        super().__init__(FESTIVAL_CITY, directory, common_data_dir=common_data_dir)
        self.compilation_by_url = {}

    def film_key(self, title, url):
        return url

    def film_can_go_to_planner(self, film_id):
        return True

    def screening_can_go_to_planner(self, screening):
        can_go = screening.is_public()

        if can_go:
            try:
                self.duplicates_by_screening[screening] += 1
            except KeyError:
                self.duplicates_by_screening[screening] = 0

        if can_go:
            included = self.included_in_combi(screening)
            can_go = not included

        return can_go

    def included_in_combi(self, screening):
        if screening.film_is_combi():
            return False
        coinciding_screenings = [s for s in self.screenings if s.film_is_combi() and screening.is_part_of(s)]
        return coinciding_screenings

    def is_coinciding_with_combination(self, screening):
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


if __name__ == "__main__":
    main()
