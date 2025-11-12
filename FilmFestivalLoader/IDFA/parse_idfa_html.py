#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load films, film information, screens and screenings from the IDFA 2020
website.

Created on Wed Nov  4 20:36:18 2020

@author: maarten
"""
import csv
import datetime
import os
import re
from enum import Enum, auto
from typing import Dict

from Shared.application_tools import ErrorCollector, DebugRecorder, comment, Counter
from Shared.parse_tools import FileKeeper, HtmlPageParser, try_parse_festival_sites
from Shared.planner_interface import FestivalData, Screening, FilmInfo, ScreenedFilm, get_screen_from_parse_name, \
    AUDIENCE_PUBLIC
from Shared.web_tools import UrlFile

FESTIVAL = 'IDFA'
FESTIVAL_CITY = 'Amsterdam'
FESTIVAL_YEAR = 2025

DEBUGGING = True
TRY_AZ_PAGES = False
ALWAYS_DOWNLOAD = False
DISPLAY_ADDED_SCREENING = False

# Files.
FILE_KEEPER = FileKeeper(FESTIVAL, FESTIVAL_YEAR)
AZ_PAGE_COUNT = 11
COMBI_DATA_PATH = os.path.join(FILE_KEEPER.plandata_dir, 'combination_data.csv')

# URL information.
FESTIVAL_HOSTNAME = 'https://festival.idfa.nl'
AZ_PATH = ('/collectie/?SHOW_TYPE=Publiek&SHOW_TYPE=New+Media&page=1&tabIndex=1'
           '&A_TO_Z_TYPE=Publiek&A_TO_Z_TYPE=New+Media')
PATHWAYS_PATH = ('/festivalgids/wegwijzers/?utm_source=IDFA+Nieuwsbrieven'
                 '&utm_campaign=da6f086be8-EMAIL_CAMPAIGN_2025_10_10_08_01&utm_medium=email'
                 '&utm_term=0_-da6f086be8-69724581')
SECTIONS_PATH = '/collectie/?SHOW_TYPE=Publiek&page=1&tabIndex=2'

# Application tools.
ERROR_COLLECTOR = ErrorCollector()
DEBUG_RECORDER = DebugRecorder(FILE_KEEPER.debug_file)
COUNTER = Counter()

URL_PATH_BY_COMBINATION_TITLE = {
    'Shorts: Current Future – My Other Universe': '/composition/e3f5df85-615e-4a0a-9989-2dd64e4d7d3e/'
                                                  'shorts:-current-future-my-other-universe/',
    'Shorts: All Eyes On ...': '/composition/cbf7e566-4284-488f-95f2-9c1c62a431d7/shorts:-all-eyes-on-...',
    'Shorts: Passages': '/composition/9a65302c-0f2d-41f5-82ee-36fc75e7e201/shorts:-passages/',
    'Shorts: Inhospitable Landscapes': '/composition/83822564-582e-4e4f-9baf-3723c9e50711/'
                                       'shorts:-inhospitable-landscapes/',
    'VPRO Previewdag': '/composition/5fa798cc-e1d7-41fe-8d76-4bd169ecebb2/vpro-previewdag/',
    'de Volkskrantdag': '/composition/a2952457-010e-4075-8c32-7adb2a336b6d/de-volkskrantdag/',
    'de Groene Amsterdammerdag': '/composition/3f214e7d-1063-40ee-8138-fcd8970ca5c6/de-groene-amsterdammerdag/',
    'Lessons from a Calf & Pride of Place': '/composition/6e52c5e7-97f9-451e-b53f-166cf5ab3cda/'
                                            'lessons-from-a-calf-and-pride-of-place/',
    'Shorts: Paradocs': '/composition/425558f7-1df8-474e-bb96-8bb26acbd3bc/shorts:-paradocs/',
}

CATEGORY_BY_STR = {
    'film': 'films',
    'composition': 'combinations',
}

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
    10: 'DarkOliveGreen',
    11: 'OliveDrab',
    12: 'Olive',
    13: 'YellowGreen',
    14: 'DarkSeaGreen',
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
    30: 'hotPink',
    31: 'violet',
}


def main():
    # Initialize a festival data object.
    comment('Creating festival data object.')
    festival_data = IdfaData(FILE_KEEPER.plandata_dir)

    # Setup counters.
    setup_counters()

    # Try parsing the websites.
    try_parse_festival_sites(parse_idfa_sites, festival_data, ERROR_COLLECTOR, DEBUG_RECORDER, FESTIVAL, COUNTER)


def setup_counters():
    COUNTER.start('film URLs')
    COUNTER.start('films')
    COUNTER.start('pathways')
    COUNTER.start('sections')
    COUNTER.start('meta dicts')
    COUNTER.start('funny location')
    COUNTER.start('combinations')
    COUNTER.start('screening parse error')

    # Counters for A-Z parsing.
    if TRY_AZ_PAGES:
        COUNTER.start('az-counters')


def parse_idfa_sites(festival_data):
    if TRY_AZ_PAGES:
        comment('Trying new AZ pege(s)')
        load_az_pages(festival_data)

    comment(f'Parsing combination films.')
    for title, path in URL_PATH_BY_COMBINATION_TITLE.items():
        url = FESTIVAL_HOSTNAME + path
        get_film_from_theme_part_page(festival_data, title, url, 'combinations/', use_section_keeper=False)

    comment('Parsing section pages.')
    get_theme_parts(festival_data, SECTIONS_PATH, 'sections.html')

    comment('Parsing pathway pages.')
    get_theme_parts(festival_data, PATHWAYS_PATH, 'pathways.html')

    comment(f'Write combination data to {COMBI_DATA_PATH}.')
    CombinationsKeeper.write_combination_data(festival_data)
    print(f'{len(CombinationsKeeper.combination_props_list)} combination date records written.')

    comment(f'Done parsing {FESTIVAL}{FESTIVAL_YEAR} pages.')


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


def get_theme_parts(festival_data, theme_path, target_file):
    theme_url = FESTIVAL_HOSTNAME + theme_path
    theme_file = os.path.join(FILE_KEEPER.webdata_dir, target_file)
    url_file = UrlFile(theme_url, theme_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
    theme_str = target_file.split('.')[0]
    comment_ = f'Downloading {theme_str} theme from {theme_url}'
    theme_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_)
    if theme_html:
        comment(f'Analysing {theme_str} theme page, encoding={url_file.encoding}')
        ThemePartsPageParser(festival_data, theme_str).feed(theme_html)


def get_films_by_theme(festival_data, theme_urls, theme_str):
    """Read the films from each of the given pathway URLs."""
    comment(f'Finding films per {theme_str} theme ({len(theme_urls)} {theme_str}s)')
    for i, theme_url in enumerate(theme_urls):
        theme_file = FILE_KEEPER.numbered_webdata_file(theme_str, i)
        url_file = UrlFile(theme_url, theme_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
        comment_ = f'Downloading {theme_url} as to find the {theme_str} parts of the encountered films'
        theme_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_)
        if theme_html:
            comment(f'Analysing {theme_str} page {i}, encoding={url_file.encoding}')
            match theme_str:
                case('sections'):
                    FilmsFromSectionPageParser(festival_data, theme_url).feed(theme_html)
                case(_):
                    FilmsFromPathwayPageParser(festival_data, theme_url).feed(theme_html)


def get_readable_theme_str(pathway_url):
    pathway_str = pathway_url.split('/')[-2]  # .replace('_', ' ')
    return pathway_str


def get_film_from_theme_part_page(festival_data, film_title, film_url, theme_part_url, use_section_keeper=True):
    """Store the sections of a film that was found in the given theme page."""
    # Check if the film is already loaded.
    try:
        _ = festival_data.get_film_by_key(film_title, film_url)
    except KeyError:
        DEBUG_RECORDER.add('New film.')
    except ValueError:
        DEBUG_RECORDER.add('Known film not yet parsed.')
    else:
        comment(f'Existing film {film_title} not parsed.')
        return

    # Load the pathway film.
    theme_str = get_readable_theme_str(theme_part_url)
    comment(f'Parsing film "{film_title}" with theme "{theme_str}".')
    # TODO in 2026: Stop using a "section keeper" to bookkeep film ID's.
    if use_section_keeper:
        film_id = SectionsKeeper.get_new_film_id(film_url)
    else:
        film_id = festival_data.new_film_id(festival_data.film_key(film_title, film_url)) + 1000
    theme_film_file = FILE_KEEPER.film_webdata_file(film_id)
    url_file = UrlFile(film_url, theme_film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
    comment_at_download = f'Downloading "{theme_str}" film "{film_title}" data from {film_url}'
    film_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
    if film_html:
        message = (f'Analysing page of "{film_title}" from theme "{theme_str}", '
                   f'parsed from "{theme_film_file}" encoding={url_file.encoding}')
        print(message)
        DEBUG_RECORDER.add(message)
        if use_section_keeper:
            FilmPageParser(festival_data, theme_str, film_title, film_url).feed(film_html)
        else:
            CombinationFilmPageParser(festival_data, theme_str, film_title, film_url).feed(film_html)


class AzPageParser(HtmlPageParser):
    class AzParseState(Enum):
        IDLE = auto()
        IN_ARTICLE = auto()

    def __init__(self, festival_data, debugger=None):
        super().__init__(festival_data, debugger or DEBUG_RECORDER, 'AZ', debugging=DEBUGGING)
        self.sorting_from_site = False
        self.film = None
        self.state_stack = self.StateStack(self.print_debug, self.AzParseState.IDLE)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        if self.state_stack.state_is(self.AzParseState.IDLE) and tag == 'article':
            self.state_stack.push(self.AzParseState.IN_ARTICLE)
            COUNTER.increase('az-counters')

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        if self.state_stack.state_is(self.AzParseState.IN_ARTICLE) and tag == 'article':
            self.state_stack.pop()

    def handle_data(self, data):
        super().handle_data(data)


class ThemePartsPageParser(HtmlPageParser):
    """Parse the given theme overview page for theme URLs."""
    class ThemePartsParseState(Enum):
        AWAITING_URL = auto()
        AWAITING_THEME_PART_TITLE = auto()
        AFTER_THEME_PART_TITLE = auto()
        DONE = auto()

    def __init__(self, festival_data, theme_str):
        super().__init__(festival_data, DEBUG_RECORDER, 'TP', debugging=DEBUGGING)
        self.theme_str = theme_str
        self.theme_urls = []
        self.theme_name_by_url = {}
        self.theme_url = None
        self.theme_name = None
        self.print_debug(self.headed_bar(header=f'THEME {theme_str}'))
        self.state_stack = self.StateStack(self.print_debug, self.ThemePartsParseState.AWAITING_URL)

    def feed(self, data):
        super().feed(data)
        get_films_by_theme(self.festival_data, self.theme_urls, self.theme_str)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.ThemePartsParseState
        match [stack.state(), tag, attrs]:
            case [state.AWAITING_URL, 'a', a] if len(a) > 1 and a[1][1].startswith('/section/'):
                self.theme_url = FESTIVAL_HOSTNAME + a[1][1]
                self.theme_urls.append(self.theme_url)
                stack.push(state.AWAITING_THEME_PART_TITLE)
            case [state.AWAITING_THEME_PART_TITLE, 'img', a] if a and a[0][0] == 'alt':
                self.theme_name = a[0][1]
                _ = SectionsKeeper.add_section_props(self.theme_name)
                self.theme_name_by_url[self.theme_url] = self.theme_name
                self._add_section()
            case [state.AWAITING_URL, 'footer', _]:
                stack.change(state.DONE)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        stack = self.state_stack
        state = self.ThemePartsParseState
        match [stack.state(), tag]:
            case [state.AWAITING_THEME_PART_TITLE, 'img']:
                stack.change(state.AFTER_THEME_PART_TITLE)
            case [state.AFTER_THEME_PART_TITLE, 'a']:
                self._init_theme_part()
                stack.pop()

    def _init_theme_part(self):
        self.theme_url = None
        self.theme_name = None

    def _add_section(self):
        DEBUG_RECORDER.add(f'ADD SECTION {self.theme_name}, {self.theme_url}')
        section = self.festival_data.get_section(self.theme_name, color_by_id=COLOR_BY_SECTION_ID)
        if section:
            self.subsection = self.festival_data.get_subsection(self.theme_name, self.theme_url, section)


class FilmsFromSectionPageParser(HtmlPageParser):
    """Laad the films from given pathway URL. Find the sections in each film."""
    class SectionFilmsParseState(Enum):
        IDLE = auto()
        AWAITING_SECTION_TITLE = auto()
        IN_SECTION_NAME = auto()
        AWAITING_SECTION_DESCRIPTION = auto()
        IN_SECTION_DESCRIPTION_ALT = auto()
        IN_SECTION_DESCRIPTION = auto()
        AWAITING_FILM = auto()
        IN_FILM = auto()
        IN_FILM_URL = auto()
        IN_FILM_TITLE = auto()
        DONE = auto()

    def __init__(self, festival_data, section_url):
        super().__init__(festival_data, DEBUG_RECORDER, 'FFS', debugging=DEBUGGING)
        self.section_url = section_url
        self.section_name = None
        self.section_description = None

        # Initialize film properties.
        self.film_url = None
        self.film_title = None

        self.draw_headed_bar(get_readable_theme_str(section_url))
        self.state_stack = self.StateStack(self.print_debug, self.SectionFilmsParseState.IDLE)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.SectionFilmsParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'a', a] if a and a[0][1].startswith('/section/'):
                stack.change(state.AWAITING_SECTION_TITLE)
            case [state.AWAITING_SECTION_TITLE, 'span', a] if a:
                self.section_name = a[0][1]
                stack.change(state.AWAITING_SECTION_DESCRIPTION)
            case [state.AWAITING_SECTION_DESCRIPTION, 'p', a] if a and a[0] == ('index', '0'):
                stack.change(state.IN_SECTION_DESCRIPTION)
            case [state.AWAITING_SECTION_DESCRIPTION, 'div', a] if a and a[0][1] == 'ey43j5h0 css-uu0j5i-Body-Body':
                stack.change(state.IN_SECTION_DESCRIPTION_ALT)
            case [state.AWAITING_FILM, 'article', _]:
                stack.push(state.IN_FILM)
            case [state.IN_FILM, 'a', a] if a and a[0][0] == 'href':
                self.film_url = FESTIVAL_HOSTNAME + a[0][1]
                stack.push(state.IN_FILM_URL)
            case [state.IN_FILM_URL, 'img', a] if a and a[0][0] == 'alt':
                self.film_title = a[0][1]
                stack.push(state.IN_FILM_TITLE)
            case [state.AWAITING_FILM, 'footer', _]:
                stack.change(state.DONE)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        stack = self.state_stack
        state = self.SectionFilmsParseState
        match [stack.state(), tag]:
            case [state.IN_SECTION_DESCRIPTION, 'p']:
                stack.change(state.AWAITING_FILM)
            case [state.IN_SECTION_DESCRIPTION_ALT, 'div']:
                stack.change(state.AWAITING_FILM)
            case [state.IN_FILM_TITLE, 'img']:
                stack.pop()
            case [state.IN_FILM_URL, 'a']:
                stack.pop()
            case [state.IN_FILM, 'article']:
                comment(f'Ready to read film "{self.film_title}" from {self.film_url}')
                self._read_film()
                stack.pop()

    def handle_data(self, data):
        super().handle_data(data)

        stack = self.state_stack
        state = self.SectionFilmsParseState
        match stack.state():
            case state.IN_SECTION_DESCRIPTION | state.IN_SECTION_DESCRIPTION_ALT:
                self.section_description = data

    def _init_film_props(self):
        self.film_url = None
        self.film_title = None

    def _read_film(self):
        comment(f'About to parse film "{self.film_title}" from {self.film_url}')
        get_film_from_theme_part_page(self.festival_data, self.film_title, self.film_url, self.section_url)
        self._init_film_props()


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

        # Draw a bar with section info.
        self.draw_headed_bar(get_readable_theme_str(pathway_url))

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

    def _read_film(self):
        comment(f'About to parse film {self.film_title} from {self.film_url}')
        get_film_from_theme_part_page(self.festival_data, self.film_title, self.film_url, self.pathway_url)
        self._init_film_data()

    def _init_film_data(self):
        self.film_url = None
        self.film_title = None
        self.section_title = None
        self.section_name = None
        self.subsection = None
        self.film_property_by_label = {}
        self.metadata_key = None

    def reset_film_parsing(self):
        DEBUG_RECORDER.add('RESET FILM PARSING, is pop() OK?')
        self.state_stack.pop()
        self._init_film_data()

    def draw_headed_bar(self, section_str):
        print(f'{self.headed_bar(header=section_str)}')
        self.print_debug(self.headed_bar(header=section_str))


class FilmPageParser(HtmlPageParser):
    """Parse the page of a film of which title and url were found in a specific theme page."""
    class PathwayFilmPageParseState(Enum):
        IDLE = auto()
        AWAITING_TITLE = auto()
        IN_TITLE = auto()
        AWAITING_META_DICT = auto()
        IN_META_DICT = auto()
        IN_META_PROPERTY = auto()
        AWAITING_TICKETS = auto()
        AWAITING_ARTICLE = auto()
        NEAR_ARTICLE = auto()
        IN_ARTICLE = auto()
        IN_PARAGRAPH = auto()
        AWAITING_SCREENINGS = auto()
        IN_SCREENING = auto()
        IN_DATE = auto()
        AWAITING_TIME = auto()
        IN_COMBINATION_PROGRAM = auto()
        IN_TIME = auto()
        IN_LOCATION = auto()
        IN_SUBTITLES = auto()
        IN_SUB_HEADER = auto()
        AWAITING_SECTION_URL = auto()
        IN_SECTION_URL = auto()
        DONE = auto()

    nl_month_by_name: Dict[str, int] = {'november': 11}

    def __init__(self, festival_data, theme_str, film_title, film_url, debug_prefix=None):
        debug_prefix = debug_prefix or 'PFP'
        super().__init__(festival_data, DEBUG_RECORDER, debug_prefix, debugging=DEBUGGING)
        self.festival_data = festival_data
        self.film_title = film_title
        self.film_url = film_url
        self.film_property_by_label = {'sections': []}
        self.film = None
        self.metadata_key = None
        self.section_title = None
        self.section_url = None
        self.subsection = None
        self.film_info = None
        self.screened_films = set()
        self.combination_films = set()

        # Screening properties.
        self.start_date = None
        self.start_dt = None
        self.end_dt = None
        self.theater = None
        self.screen = None
        self.subtitles = None
        self.qa = None
        self.combi_program = None
        self.combi_props = None
        self.screening = None

        self.draw_headed_bar(f'{theme_str} - {film_title}')
        self.state_stack = self.StateStack(self.print_debug, self.PathwayFilmPageParseState.IDLE)

    def feed(self, data):
        super().feed(data)

        comment('Add the sections found to the sections keeper.')
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
            case [state.AWAITING_ARTICLE, 'div', a] if a and a[0] == ('class', 'ey43j5h0 css-gu30tp-Body-Body'):
                stack.change(state.IN_ARTICLE)
            case [state.IN_ARTICLE, 'p', a] if a and a[0][0] == 'index':
                stack.push(state.IN_PARAGRAPH)
            case [state.AWAITING_SCREENINGS, 'article', _]:
                stack.push(state.IN_SCREENING)
            case [state.IN_SCREENING, 'div', a] if a and a[0] == ('variant', '4'):
                stack.push(state.IN_DATE)
            case [state.AWAITING_TIME, 'div', a] if a and a[0][1] == 'ey43j5h0 css-1cky3te-Body-Body':
                stack.push(state.IN_COMBINATION_PROGRAM)
            case [state.AWAITING_TIME, 'span', _]:
                stack.change(state.IN_TIME)
            case [state.IN_LOCATION, 'div', a] if a and a[0][1] == 'ey43j5h0 css-mog33i-Body-Body':
                stack.push(state.IN_SUBTITLES)
            case [state.AWAITING_SCREENINGS, 'a', a] if len(a) > 1 and a[1][0] == 'href' and a[1][1].startswith('/section/'):
                self.section_url = FESTIVAL_HOSTNAME + a[1][1]
                self._add_section()
                self._add_combinations()
                stack.change(state.DONE)
            case [state.AWAITING_SCREENINGS, 'footer', _]:
                self._add_combinations()
                stack.change(state.DONE)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

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
                self._add_film()
                stack.change(state.AWAITING_SCREENINGS)
            case [state.IN_DATE, 'div']:
                stack.change(state.AWAITING_TIME)
            case [state.IN_COMBINATION_PROGRAM, 'div']:
                stack.pop()
            case [state.IN_TIME, 'span']:
                stack.change(state.IN_LOCATION)
            case [state.IN_SUBTITLES, 'div']:
                stack.pop()

    def handle_data(self, data):
        super().handle_data(data)

        stack = self.state_stack
        state = self.PathwayFilmPageParseState
        match stack.state():
            case state.IN_META_PROPERTY:
                self._add_film_property(data.strip())
            case state.IN_PARAGRAPH:
                self.add_article_text(data)
            case state.IN_DATE:
                self._set_screening_date(data)
            case state.IN_COMBINATION_PROGRAM:
                self._handle_combination_data(data)
            case state.IN_TIME:
                self._set_screening_times(data)
            case state.IN_LOCATION:
                if self._set_idfa_screen(data):
                    self._add_screening()
                    DEBUG_RECORDER.add(f'SCREEN: {data=}, {self.screen=}')
                    stack.pop(2)  # Pop stack twice to get back to "AWAITING_SCREENINGS".
            case state.IN_SUBTITLES:
                self.subtitles = data.strip()

    def add_article_text(self, data):
        if not data.startswith('.css'):
            super().add_article_text(data)

    def _exit_screening(self, except_code):
        COUNTER.increase('screening parse error')
        error, message = f'{except_code} in {self.film_title}', 'Proceeding to next film'
        ERROR_COLLECTOR.add(error, message)
        DEBUG_RECORDER.add(f'{error=}, {message=}')
        self.state_stack.change(self.PathwayFilmPageParseState.DONE)

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
            self.subsection = self.festival_data.get_subsection(self.section_title, self.section_url, section)
            self.film.subsection = self.subsection

    def _get_medium_category(self):
        category_str = self.film_url.split('/')[3]
        return CATEGORY_BY_STR[category_str]

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
            COUNTER.increase('films')
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
        self.film_info = FilmInfo(self.film.film_id, self.description, self.article, metadata=metadata)
        self.festival_data.filminfos.append(self.film_info)

    def _add_screening(self):
        # Create an IDFA screening from the gathered data.
        self.screening = IdfaScreening(self.film,
                                       self.screen,
                                       self.start_dt,
                                       self.end_dt,
                                       qa=self.qa,
                                       audience=AUDIENCE_PUBLIC,
                                       combi_program=self.combi_program
                                       )
        self.add_screening(self.screening, DISPLAY_ADDED_SCREENING)

        # Add combination data.
        if self.combi_props:
            self.combi_props['screening_str'] = f'{self.screening}'
            CombinationsKeeper.add_row(list(self.combi_props.values()))

        # Initialize the next round of parsing.
        self._init_screening_props()

    def _init_screening_props(self):
        self.start_date = None
        self.start_dt = None
        self.end_dt = None
        self.theater = None
        self.screen = None
        self.subtitles = None
        self.qa = None
        self.combi_program = None
        self.combi_props = None
        self.screening = None

    def _get_duration(self):
        try:
            duration_str = self.film_property_by_label['length']        # "96 min"
        except KeyError:
            duration_str = '0'
        minutes = int(duration_str.split()[0])
        return datetime.timedelta(minutes=minutes)

    def _set_screening_date(self, data):
        parts = data.split()  # 'ma 17 november'
        try:
            day = int(parts[1])
            month = int(self.nl_month_by_name[parts[2]])
        except ValueError as e:
            self._exit_screening(e)
        else:
            self.start_date = datetime.date(day=day, month=month, year=FESTIVAL_YEAR)

    def _set_screening_times(self, data):
        def _time(time_str):
            """Get time from strings as '17.15–18.48' or '18-11-2025, 21.45 – 19-11-2025, 00.08'"""
            hh_dot_mm = time_str.split(',')[-1].strip()
            return hh_dot_mm

        times = data.split('–')     # '17.15–18.48' or '18-11-2025, 21.45 – 19-11-2025, 00.08'

        start_time_str = _time(times[0])
        start_hour, start_minute = start_time_str.split('.')
        start_time = datetime.time(hour=int(start_hour), minute=int(start_minute))

        end_hour_str = _time(times[1])
        end_hour, end_minute = end_hour_str.split('.')
        end_time = datetime.time(hour=int(end_hour), minute=int(end_minute))

        self.start_dt, self.end_dt = self.get_screening_date_times(self.start_date, start_time, end_time)

    def _handle_combination_data(self, data):
        # Find a combination title in the data.
        re_title = re.compile(r'Onderdeel van (.*)')    # "Onderdeel van Shorts: Manufactured Control"
        m = re_title.match(data)
        if m:
            combi_title = m.group(1)
            COUNTER.increase('combinations')
        else:
            combi_title = None

        # Try to get a combination URL.
        try:
            combi_url = FESTIVAL_HOSTNAME + URL_PATH_BY_COMBINATION_TITLE[combi_title]
        except KeyError:
            combi_url = None

        self.combi_props = {
            'film_id': self.film.film_id,
            'screening_str': None,
            'combination_data': combi_title,
            'combination_url': combi_url,
        }

        # Get the combination program if possible and add it to the set of combination programs.
        if combi_url:
            combi_program = self.festival_data.get_film_by_key(combi_title, combi_url)
            self.combination_films.add(combi_program)

    def _add_combinations(self):
        for combi_program in self.combination_films:
            # Set this film as screened film in the combination program.
            combi_info = combi_program.film_info(self.festival_data)
            if self.film.film_id not in [sf.film_id for sf in combi_info.screened_films]:
                screened_film = ScreenedFilm(self.film.film_id, self.film.title, self.description)
                combi_info.screened_films.append(screened_film)

            # Set the combination program of this film.
            self.film_info.combination_films.append(combi_program)

    def _set_idfa_screen(self, data):
        if data.startswith('.css'):
            COUNTER.increase('funny location')
            return False
        elif data.startswith('Loading') or data.startswith('Inloggen'):
            self._exit_screening(f'Missed a screening while parsing "{self.film_title}"')
            return False

        screen_parse_name = data.strip()
        splitter = LocationSplitter.split_location
        self.screen = get_screen_from_parse_name(self.festival_data, screen_parse_name, splitter)
        return True


class CombinationFilmPageParser(FilmPageParser):
    """Get minimal information to create a combination film."""
    def __init__(self, festival_data, theme_str, film_title, film_url):
        super().__init__(festival_data, theme_str, film_title, film_url, debug_prefix='CFP')

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        stack = self.state_stack
        state = self.PathwayFilmPageParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'meta', a] if len(a) > 1 and a[0] == ('property', 'og:description'):
                self.description = a[1][1]
            case [state.IDLE, 'div', a] if len(a) > 1 and a[1] == ('clamp', '3'):
                stack.change(state.IN_TITLE)
            case [state.AWAITING_ARTICLE, 'div', a] if a and a[0] == ('variant', '3'):
                stack.change(state.NEAR_ARTICLE)
            case [state.IN_ARTICLE, 'p', a] if a and a[0][0] == 'index':
                stack.push(state.IN_PARAGRAPH)
            case [state.AWAITING_SCREENINGS, 'article', _]:
                stack.push(state.IN_SCREENING)
            case [state.IN_SCREENING, 'div', a] if a and a[0] == ('variant', '4'):
                stack.push(state.IN_DATE)
            case [state.AWAITING_TIME, 'div', a] if a and a[0][1] == 'ey43j5h0 css-1cky3te-Body-Body':
                stack.push(state.IN_COMBINATION_PROGRAM)
            case [state.AWAITING_TIME, 'span', _]:
                stack.change(state.IN_TIME)
            case [state.AWAITING_SCREENINGS, 'div', a] if a and a[0] == ('variant', '3'):
                stack.push(state.IN_SUB_HEADER)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        stack = self.state_stack
        state = self.PathwayFilmPageParseState
        match [stack.state(), tag]:
            case [state.IN_TITLE, 'div']:
                stack.change(state.AWAITING_ARTICLE)
            case [state.NEAR_ARTICLE, 'div']:
                stack.change(state.IN_ARTICLE)
            case [state.IN_PARAGRAPH, 'p']:
                self.add_paragraph()
                stack.pop()
            case [state.IN_ARTICLE, 'div']:
                self._add_film()
                stack.change(state.AWAITING_SCREENINGS)
            case [state.IN_DATE, 'div']:
                stack.change(state.AWAITING_TIME)
            case [state.IN_COMBINATION_PROGRAM, 'div']:
                stack.pop()
            case [state.IN_TIME, 'span']:
                stack.change(state.IN_LOCATION)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        stack = self.state_stack
        state = self.PathwayFilmPageParseState
        match stack.state():
            case state.IN_TITLE:
                self.film_title = data.strip()
            case state.IN_PARAGRAPH:
                self.add_article_text(data)
            case state.IN_DATE:
                self._set_screening_date(data)
            case state.IN_TIME:
                self._set_screening_times(data)
            case state.IN_LOCATION:
                if self._set_idfa_screen(data):
                    self._add_screening()
                    DEBUG_RECORDER.add(f'SCREEN: {data=}, {self.screen=}')
                    stack.pop(2)  # Pop stack twice to get back to "AWAITING_SCREENINGS".
            case state.IN_SUB_HEADER:
                if data == 'Tickets & Tijden':
                    stack.pop()
                else:
                    self._add_combinations()
                    stack.change(state.DONE)  # TODO: This could be the starting point for parsing screened films.


class LocationSplitter:
    num_screen_re = re.compile(r'^(?P<theater>.*?) (?P<number>\d+)$')

    @classmethod
    def split_location(cls, location):
        city_name = FESTIVAL_CITY
        theater_parse_name = location
        default_screen_abbreviation = 'zaal'
        num_match = cls.num_screen_re.match(location)

        location_words = location.split()
        screen_abbreviation = ''
        location_words.extend(['', '', ''])
        match [location_words[0], location_words[1], location_words[2], location_words[3]]:
            case ['De', 'Balie:', 'Grote', 'Zaal']:
                theater_parse_name = 'De Balie'
                screen_abbreviation = 'groot'
            case ['OT', '301', '', '']:
                theater_parse_name = 'OT 301'
            case ['SPUI', '25', '', '']:
                theater_parse_name = location
                screen_abbreviation = default_screen_abbreviation
            case ['OBA', 'Oosterdok', 'OBA', 'Theater']:
                theater_parse_name = ' '.join(location_words[:2])
                screen_abbreviation = ' '.join(location_words[2:])
            case [_, _, _, _] if num_match:
                theater_parse_name = num_match.group(1)
                screen_abbreviation = num_match.group(2)
            case _:
                screen_abbreviation = default_screen_abbreviation

        return city_name, theater_parse_name, screen_abbreviation or default_screen_abbreviation


class CombinationsKeeper:
    combination_props_header = ['film_id', 'screening_str', 'combination_str', 'combination_url']
    combination_props_list = []

    @classmethod
    def add_row(cls, prop_row):
        cls.combination_props_list.append(prop_row)

    @classmethod
    def write_combination_data(cls, festival_data):
        dialect = festival_data.dialect
        header = cls.combination_props_header
        rows = cls.combination_props_list
        with open(COMBI_DATA_PATH, 'w') as csvfile:
            csv_writer = csv.writer(csvfile, dialect=dialect)
            csv_writer.writerow(header)
            csv_writer.writerows(rows)


class SectionsKeeper:
    """Uses films found in pathways to support finding sections."""
    section_titles = set()
    film_id = 0

    @classmethod
    def get_new_film_id(cls, film_url):
        cls.film_id += 1
        return cls.film_id

    @classmethod
    def add_section_props(cls, section_title):
        if section_title in cls.section_titles:
            return False
        cls.section_titles.add(section_title)
        COUNTER.increase('sections')
        return True


class IdfaScreening(Screening):
    re_num_screen = re.compile(r'^(?P<theater>.*?)\s+(?P<number>\d+)$')
    re_colon_screen = re.compile(r'^(?P<theater>.*?):\s+(?P<room>.+)$')

    def __init__(self, film, screen, start_datetime, end_datetime, qa='', extra='',
                 audience=None, combi_program=None):
        super().__init__(film, screen, start_datetime, end_datetime, qa or '', extra, audience,
                         combination_program=combi_program)

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


if __name__ == "__main__":
    main()
