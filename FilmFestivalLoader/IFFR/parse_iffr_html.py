#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import re
from enum import Enum, auto
from ftplib import FTP
from typing import Dict
from urllib.error import HTTPError

import pysftp

from Shared.application_tools import ErrorCollector, DebugRecorder, comment, Config, Counter
from Shared.parse_tools import FileKeeper, try_parse_festival_sites, HtmlPageParser
from Shared.planner_interface import FilmInfo, Screening, ScreenedFilmType, FestivalData, Film, \
    get_screen_from_parse_name, link_screened_film, ScreeningKey
from Shared.web_tools import UrlFile, iri_slug_to_url, fix_json, paths_eq

ALWAYS_DOWNLOAD = True
DEBUGGING = True
DISPLAY_ADDED_SCREENING = True
COMBINATION_TITLE_BY_ABBREVIATION = {
    'The Battle Of Chile': 'The Battle Of Chile (Part 1): The Insurrection of the Bourgeoisie',
    'Extranjeros': 'Extranjeros (Främlingar)',
    '': 'Cloud Migration',
}
COMBINATION_EVENT_TITLES = ['Babyfilmclub']
DUPLICATE_EVENTS_TITLES_BY_MAIN = {
    'Head South': ['Opening Night 2024: Head South'],
    'La Luna': ['Closing Night: La Luna (film only)', 'Closing Night: La Luna & Party'],
    'How to Have Sex': ['IFFR x EUR: How to Have Sex'],
    'Blackbird Blackbird Blackberry': ['IFFR Young Selectors: Blackbird Blackbird Blackberry'],
}
REVIEWER_BY_ALIAS = {
    'Cristina Kolozsváry-Kiss': 'Cristina Kolozsváry-Kiss',
    '­Callum McLean': 'Callum McLean',
    'Cristina Álvarez López': 'Cristina Álvarez-López',
}
REVIEWER_MAX_LENGTH = 44
MAX_PAGES = 42

FESTIVAL = 'IFFR'
FESTIVAL_YEAR = 2025
FESTIVAL_CITY = 'Rotterdam'

# Files.
FILE_KEEPER = FileKeeper(FESTIVAL, FESTIVAL_YEAR)

# URL information.
IFFR_HOSTNAME = "https://iffr.com"

# Application tools.
ERROR_COLLECTOR = ErrorCollector()
DEBUG_RECORDER = DebugRecorder(FILE_KEEPER.debug_file)
COUNTER = Counter()


def main():
    # Initialize a festival data object.
    festival_data: IffrData = IffrData(FILE_KEEPER.plandata_dir)

    # Add film category keys.
    Film.category_by_string['films'] = Film.category_films
    Film.category_by_string['events'] = Film.category_events
    # Film.category_by_string['CombinedProgram'] = Film.category_combinations

    # Set-up counters.
    setup_counters()

    # Try parsing the websites.
    try_parse_festival_sites(parse_iffr_sites, festival_data, ERROR_COLLECTOR, DEBUG_RECORDER, FESTIVAL, COUNTER)


def setup_counters():
    COUNTER.start('film urls in az')
    COUNTER.start('no description')
    COUNTER.start('subsections with films')
    COUNTER.start('not found urls')
    COUNTER.start('films')
    COUNTER.start('screenings')
    COUNTER.start('articles')
    COUNTER.start('metadata')
    COUNTER.start('unexpected sentinel')
    # COUNTER.start('CombinedProgram')
    # COUNTER.start('OtherProgram')
    # COUNTER.start('feature films')
    # COUNTER.start('shorts')
    # COUNTER.start('duplicate events')
    # COUNTER.start('combination events')
    # COUNTER.start('public')
    # COUNTER.start('industry')
    # COUNTER.start('combinations from screenings')
    # for screened_film_type in ScreenedFilmType:
    #     COUNTER.start(screened_film_type.name)
    # COUNTER.start('wrong_title')


def parse_iffr_sites(festival_data):
    """
    Callback method to pass to try_parse_festival_sites().
    :param festival_data: planner_interface.festival_data object.
    :return: None
    """
    # comment('Trying FTP!')
    # try_ftp()

    comment('Parsing AZ pages.')
    get_films(festival_data)

    comment('Parsing subsection pages.')
    get_subsection_details(festival_data)

    # comment('Parsing combination programs.')
    # get_combination_programs(festival_data)

    comment('Parsing events.')
    get_events(festival_data)

    comment('Parsing regular film pages.')
    get_regular_films(festival_data)

    # comment('Constructing combinations from screening data')
    # set_combinations_from_screening_data(festival_data)


def try_ftp():
    host = 'iffr.com'
    path = 'nl/iffr/2025/films'
    user = 'guest'  # 'anonymous'
    timeout = 15

    ftp_kwargs = {
        'host': host,
        'user': user,
        'passwd': 'guest',
        'timeout': timeout,
    }
    # print(f'@@ Starting ftp on {host}')
    # with FTP(**ftp_kwargs) as ftp:
    #     print(f'@@ Logged in, cwd to {path}')
    #     ftp.cwd('nl/iffr/2025/films')
    #     print(f'@@ ')
    #     ftp.dir()

    print(f'@@ Starting sftp on {host}')
    with pysftp.Connection(host, username=user, private_key='guest') as sftp:
        print(f'@@ Logged in, cd to {path}')
        with sftp.cd(path):
            print(f'@@ Listing "."')
            d = sftp.listdir('.')
    print(f'@@ Done.')
    print(f'{d=}')


def get_films(festival_data):
    az_url_path = f'/nl/film?edition=iffr-{FESTIVAL_YEAR}'   # https://iffr.com/nl/film?edition=iffr-2025
    az_url = IFFR_HOSTNAME + az_url_path
    az_file = FILE_KEEPER.az_file()
    url_file = UrlFile(az_url, az_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
    comment_at_download = f'Downloading AZ page: {az_url}, encoding: {url_file.encoding}'
    az_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
    if az_html is not None:
        comment(f'Analysing AZ page, encoding={url_file.encoding}')
        AzPageParser(festival_data).feed(az_html)


def get_combination_programs(festival_data):
    get_film_details(festival_data, Film.category_combinations, 'combination')


def get_events(festival_data):
    get_film_details(festival_data, Film.category_events, 'event', always_download=ALWAYS_DOWNLOAD)


def get_regular_films(festival_data):
    get_film_details(festival_data, Film.category_films, 'film', always_download=ALWAYS_DOWNLOAD)


def has_category(film, category):
    return Film.category_by_string[film.medium_category] == category


def get_film_details(festival_data, category, category_name, always_download=ALWAYS_DOWNLOAD):
    films = [film for film in festival_data.films if has_category(film, category)]
    for film in films:
        film_file = FILE_KEEPER.film_webdata_file(film.film_id)
        url_file = UrlFile(film.url, film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=300)
        comment_at_download = f'Downloading site of {film.title}: {film.url}, encoding: {url_file.encoding}'
        film_html = url_file.get_text(always_download=always_download, comment_at_download=comment_at_download)
        if film_html is not None:
            print(f'Analysing html file {film.film_id} of {category_name} {film.title}')
            FilmInfoPageParser(festival_data, film, url_file.encoding).feed(film_html)


def get_subsection_details(festival_data):
    for subsection in festival_data.subsection_by_name.values():
        found_films = True
        page_num = 0
        while found_films and page_num < MAX_PAGES:
            page_num += 1
            found_films = get_subsection_page_details(festival_data, subsection, page_num)
        if page_num >= MAX_PAGES:
            ERROR_COLLECTOR.add('Numbered webpage overflow', f'subsection {subsection.name}')


def get_subsection_page_details(festival_data, subsection, page_number):
    paged_file = FILE_KEEPER.paged_numbered_webdata_file('subsection', subsection.subsection_id, page_number)
    paged_url = f'{subsection.url}/page/{page_number}'
    not_found = 404

    try:
        url_file = UrlFile(paged_url, paged_file, ERROR_COLLECTOR, DEBUG_RECORDER,
                           byte_count=300, reraise_codes=[not_found])
    except HTTPError as e:
        COUNTER.increase('not found urls')
        return False

    comment_at_download = f'Downloading {subsection.name} page: {subsection.url}, encoding: {url_file.encoding}'
    subsection_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
    film_count = 0
    if subsection_html is not None:
        encoding_str = f'encoding={url_file.encoding}'
        print(f'Analysing subsection page {subsection.subsection_id}, {subsection.name}, {encoding_str}.')
        parser = SubsectionPageParser(festival_data, subsection)
        parser.feed(subsection_html)
        film_count = parser.film_count
    if film_count and page_number == 1:
        COUNTER.increase('subsections with films')
    return film_count


def set_combinations_from_screening_data(festival_data):
    def coinciding(screening, key, other_film):
        return ScreeningKey(screening) == key and screening.film.film_id != other_film.film_id

    for main_film, screening_key in ScreeningParser.screening_key_by_main_film.items():
        main_film_info = main_film.film_info(festival_data)
        screened_film_type = ScreeningParser.screened_film_type_by_screening_key[screening_key]
        screened_films = [s.film for s in festival_data.screenings if coinciding(s, screening_key, main_film)]
        if screened_films:
            COUNTER.increase('combinations from screenings')
            COUNTER.increase(screened_film_type.name)
        for film in screened_films:
            link_screened_film(festival_data, film, main_film, main_film_info, screened_film_type)


def is_combination_event(film):
    return film.title in COMBINATION_EVENT_TITLES and has_category(film, Film.category_events)


class AzPageParser(HtmlPageParser):
    class AzParseState(Enum):
        IDLE = auto()
        IN_FILM_SCRIPT = auto()
        DONE = auto()

    re_props = re.compile(
        r"""
            "(?P<medium>Film|CombinedProgram|OtherProgram)","id":"[^"]*?"       # Medium category
            ,"title":"(?P<title>.+?)",.*?                                       # Title
            ,"url\(\{\\"language\\":\\"nl\\"\}\)":"(?P<url>[^"]+)"              # Film URL
            ,"description\(\{.*?\}\)":"(?P<grid_desc>.*?)"                      # Grid description
            ,"description\(\{.*?\}\)":"(?P<list_desc>.*?)"                      # List description
            ,"section":([^:]*?:"Section","title":"(?P<section>[^"]+)".*?|null)  # IFFR Section
            ,"subSection":([^:]*?:"SubSection","title":"(?P<subsection>[^"]+)"  # IFFR Subsection
            ,"url\(\{.*?\}\)":"(?P<subsection_url>[^"]+)"|null).*?              # Sub-section URL
            (,"duration":(?P<duration>\d+),".*?)?                               # Duration
            ,"sortedTitle":"(?P<sorted_title>.+?)",                             # Sorted Title
        """, re.VERBOSE)

    color_by_section_id = {
        1: 'DodgerBlue',
        2: 'Yellow',
        3: 'Red',
        4: 'LimeGreen',
        5: 'LightCoral',
    }
    film_id_by_title = {}

    def __init__(self, festival_data):
        HtmlPageParser.__init__(self, festival_data, DEBUG_RECORDER, 'AZ', debugging=DEBUGGING)
        self.config = Config().config
        self.max_short_duration = datetime.timedelta(minutes=self.config['Constants']['MaxShortMinutes'])
        self.film = None
        self.title = None
        self.url = None
        self.description = None
        self.article = None
        self.section_name = None
        self.subsection_name = None
        self.subsection_url = None
        self.sorted_title = None
        self.duration = None
        self.medium_category = None
        self.state_stack = self.StateStack(self.print_debug, self.AzParseState.IDLE)
        self.init_film_data()

    def init_film_data(self):
        self.film = None
        self.title = None
        self.url = None
        self.duration = None
        self.medium_category = None
        self.description = None
        self.article = None
        self.section_name = None
        self.subsection_name = None
        self.subsection_url = None
        self.sorted_title = None

    def parse_props(self, data):
        i = self.re_props.finditer(data)
        matches = [match for match in i]
        groups = [m.groupdict() for m in matches]
        for g in groups:
            self.medium_category = g['medium']
            self.title = fix_json(g['title'], error_collector=ERROR_COLLECTOR)
            self.url = iri_slug_to_url(IFFR_HOSTNAME, g['url'])
            self.description, self.article = self.get_description(g['grid_desc'], g['list_desc'])
            if g['section']:
                self.section_name = fix_json(g['section'], error_collector=ERROR_COLLECTOR)
            if g['subsection']:
                self.subsection_name = fix_json(g['subsection'], error_collector=ERROR_COLLECTOR).rstrip()
            if g['subsection_url']:
                self.subsection_url = iri_slug_to_url(IFFR_HOSTNAME, g['subsection_url'])
            self.sorted_title = fix_json(g['sorted_title'], error_collector=ERROR_COLLECTOR).lower()
            if not self.sorted_title:
                self.sorted_title = re.sub(r'\\', '', g['sorted_title'])
                """Workaround for the 2024 edition to handle one double quote in sort string."""
                print(f'{self.sorted_title=} after fix.')
            self.duration = self.get_duration(g['duration'])
            self.add_film()
            self.init_film_data()

    @staticmethod
    def get_description(grid_description, list_description):
        description = fix_json(grid_description, error_collector=ERROR_COLLECTOR)
        article = fix_json(list_description, error_collector=ERROR_COLLECTOR)
        if not description:
            description = article
        if list_description == 'Binnenkort meer informatie over deze film.':
            description = ''
            COUNTER.increase('no description')
        if description:
            if not article:
                article = description
            if article != description:
                article = description + 2 * '\n' + article
        return description, article

    @staticmethod
    def get_duration(minutes_str):
        minutes = 0 if minutes_str is None else int(minutes_str)
        duration = datetime.timedelta(minutes=minutes)
        return duration

    def get_subsection(self):
        section = self.festival_data.get_section(self.section_name, color_by_id=self.color_by_section_id)
        if section:
            subsection = self.festival_data.get_subsection(self.subsection_name, self.subsection_url, section)
        else:
            subsection = None
        return subsection

    def add_film(self):
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            ERROR_COLLECTOR.add(f'Could\'t create film from {self.title}', self.url)
        else:
            self.film.medium_category = self.medium_category
            if self.film.medium_category not in Film.category_by_string:
                error_msg = f'{self.film.title}', f'{self.film.medium_category} from {self.url}'
                ERROR_COLLECTOR.add(f'Unexpected category "{self.film.medium_category}"', error_msg)
            self.film.duration = self.duration
            self.film.sortstring = self.sorted_title
            self.increase_per_duration_class_counter(self.film)
            self.increase_per_film_category_counter()
            self.film_id_by_title[self.film.title] = self.film.film_id
            print(f'Adding FILM: {self.title} ({self.film.duration_str()}) {self.film.medium_category}')
            self.festival_data.films.append(self.film)
            self.film.subsection = self.get_subsection()
            self.add_film_info()

    def add_film_info(self):
        if len(self.description) > 0:
            film_info = FilmInfo(self.film.film_id, self.description, self.article)
            self.festival_data.filminfos.append(film_info)

    def increase_per_duration_class_counter(self, film):
        key = 'feature films' if film.duration > self.max_short_duration else 'shorts'
        COUNTER.increase(key)

    def increase_per_film_category_counter(self):
        COUNTER.increase(self.film.medium_category)

    def check_film_url_in_data(self, url):
        for film in self.festival_data.films:
            if paths_eq(film.url, url):
                COUNTER.increase('film urls in az')

    def check_film_url_in_anchor(self, attrs):
        urls = [attr[1] for attr in attrs if attr[0] == 'href']
        for url in urls:
            self.check_film_url_in_data(url)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        match [self.state_stack.state(), tag, attrs]:
            case [self.AzParseState.IDLE, 'script', a] if a and a[0] == ('id', '__NEXT_DATA__'):
                self.state_stack.change(self.AzParseState.IN_FILM_SCRIPT)
            case [self.AzParseState.IDLE, 'a', a] if a:
                self.check_film_url_in_anchor(a)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        match self.state_stack.state():
            case self.AzParseState.IN_FILM_SCRIPT:
                self.parse_props(data)
                self.state_stack.change(self.AzParseState.DONE)
            case _ if data.strip().startswith(IFFR_HOSTNAME):
                self.check_film_url_in_data(data.strip())


class SubsectionPageParser(HtmlPageParser):
    class SubsectionParseState(Enum):
        IDLE = auto()
        AWAITING_HEADER = auto()
        AWAITING_LINK = auto()
        IN_TITLE = auto()
        AWAITING_FILM_DESCRIPTION = auto()
        IN_FILM_DESCRIPTION = auto()
        DONE = auto()

    def __init__(self, festival_data, subsection):
        super().__init__(festival_data, DEBUG_RECORDER, 'SEC', debugging=DEBUGGING)
        self.festival_data = festival_data
        self.subsection = subsection
        self.film = None
        self.film_url = None
        self.film_title = None
        self.film_description = None
        self.film_count = 0
        self.print_debug(self.bar, f'Analysing SUBSECTION {self.subsection.name}')
        self.state_stack = self.StateStack(self.print_debug, self.SubsectionParseState.IDLE)

    def init_film(self):
        self.film_url = None
        self.film_title = None
        self.film_description = ''

    def update_subsection(self, description=None):
        self.subsection.description = description

    def add_film(self):
        # Check validity of URL.
        year = self.film_url.split('/')[5]  # https://iffr.com/nl/iffr/2025/events/vpro-reviewdag-2025
        if year != str(FESTIVAL_YEAR):
            return

        # Create film.
        self.film = self.festival_data.create_film(self.film_title, self.film_url)
        if self.film is None:
            ERROR_COLLECTOR.add(f"Couldn't create film from {self.film_title}", self.film_url)
        else:
            self.film.medium_category = self.film_url.split('/')[6]
            self.film.subsection = self.subsection
            print(f'Adding FILM: {self.film_title} {self.film.medium_category}')
            self.festival_data.films.append(self.film)
            COUNTER.increase('films')

            # Add film info.
            self.description = self.film_description
            self.description or COUNTER.increase('no description')
            self.add_film_info()

            # Reset film variables.
            self.film_count += 1
            self.init_film()

    def add_film_info(self):
        film_info = FilmInfo(self.film.film_id, self.description, '')
        self.festival_data.filminfos.append(film_info)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.SubsectionParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'meta', a] if a and a[0][1] == 'og:description':
                self.update_subsection(a[1][1])
                stack.change(state.AWAITING_HEADER)
            case [state.AWAITING_HEADER | state.IDLE, 'h3', _]:
                stack.push(state.AWAITING_LINK)
            case [state.AWAITING_LINK, 'a', a] if a and a[0][0] == 'href':
                self.film_url = a[0][1]
                stack.change(state.IN_TITLE)
            case [state.AWAITING_FILM_DESCRIPTION, 'p', _]:
                stack.change(state.IN_FILM_DESCRIPTION)
            case [state.AWAITING_HEADER | state.IDLE, 'div', a] if a and a[0][1] == 'footer-menu':
                stack.change(state.DONE)

    def handle_data(self, data):
        super().handle_data(data)

        match self.state_stack.state():
            case self.SubsectionParseState.IN_TITLE:
                self.film_title = data.strip()
                self.state_stack.change(self.SubsectionParseState.AWAITING_FILM_DESCRIPTION)
            case self.SubsectionParseState.IN_FILM_DESCRIPTION:
                self.film_description = data
                self.add_film()
                self.state_stack.pop()


class ScreeningParser(HtmlPageParser):
    class ScreeningParseState(Enum):
        IDLE = auto()
        IN_SCREENINGS = auto()
        IN_SCREENING = auto()
        IN_SCREENING_DATE = auto()
        IN_SCREENING_TIMES = auto()
        IN_SCREENING_LOCATION = auto()
        IN_COMBINATION_LIST = auto()
        IN_COMBINATION_PART = auto()
        AFTER_SCREENING_DATA = auto()
        DONE = auto()

    nl_month_by_name: Dict[str, int] = {
        'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
        'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11,
        'december': 12}
    screened_film_type_by_string = {
        'Voorfilm bij ': ScreenedFilmType.SCREENED_BEFORE,
        'Te zien na ': ScreenedFilmType.SCREENED_AFTER,
        'Gepresenteerd als onderdeel van ': ScreenedFilmType.PART_OF_COMBINATION_PROGRAM,
        'Wordt vertoond in combinatie met ': ScreenedFilmType.DIRECTLY_COMBINED}
    screened_film_type_by_screening_key = {}
    screening_key_by_main_film = {}
    re_num_screen = re.compile(r'^(?P<theater>.*?)\s+(?P<number>\d+)$')
    re_separator = re.compile(r'^(?P<theater>.*?)\s+-\s+(?P<room>[^-]+)$')

    def __init__(self, festival_data, debug_prefix, debugging=DEBUGGING):
        HtmlPageParser.__init__(self, festival_data, DEBUG_RECORDER, debug_prefix, debugging=debugging)
        self.film = None
        self.film_info = None
        self.start_date = None
        self.times_str = None
        self.start_dt = None
        self.end_dt = None
        self.location = None
        self.screen = None
        self.screened_film_type = None
        self.combination_part = None
        self.combination_parts = None
        self.audience = None
        self.extra = None
        self.subtitles = None
        self.q_and_a = None
        self.sold_out = None

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.ScreeningParseState.IDLE)

    def init_screening_data(self):
        self.start_date = None
        self.times_str = ''
        self.start_dt = None
        self.end_dt = None
        self.location = None
        self.screen = None
        self.screened_film_type = None
        self.combination_part = ''
        self.combination_parts = []
        self.audience = Screening.audience_type_public
        self.extra = ''
        self.subtitles = ''
        self.q_and_a = ''

    def parse_screening_date(self, data):
        items = data.split()  # woensdag 01 februari 2023
        day = int(items[1])
        month = self.nl_month_by_name[items[2]]
        year = int(items[3])
        return datetime.date(year, month, day)

    def set_screening_times(self):
        items = self.times_str.split()  # 13:00 - 15:26
        start_time = datetime.time.fromisoformat(items[0])
        end_time = datetime.time.fromisoformat(items[2])
        self.start_dt = datetime.datetime.combine(self.start_date, start_time)
        end_date = self.start_date if end_time > start_time else self.start_date + datetime.timedelta(days=1)
        self.end_dt = datetime.datetime.combine(end_date, end_time)

    def set_screening_data(self, data):
        if data == 'Voor professionals':
            self.audience = data
        if 'Q&A' in data:
            self.q_and_a = 'Q&A'
        if 'Met voorfilm' in data:
            self.extra = 'voorfilm'
            self.screened_film_type = ScreenedFilmType.SCREENED_BEFORE
        if 'Uitverkocht' in data:
            pass    # Word is not encountered in the HTML text.
        if data.endswith('ondertiteld'):
            self.subtitles = data

    def add_on_location_screening(self):
        if self.event_starts_simultaneous():
            print(f'Screening skipped in favour of derived event: {self.film.title}')
            COUNTER.increase('duplicate events')
            return
        self.screen = self.get_screen()
        iffr_screening = IffrScreening(self.film, self.screen, self.start_dt, self.end_dt, self.q_and_a,
                                       self.extra, self.audience, self.screened_film_type, self.sold_out)
        self.set_combination_data(iffr_screening)
        iffr_screening.subtitles = self.subtitles
        self.add_screening(iffr_screening, display=DISPLAY_ADDED_SCREENING)
        COUNTER.increase('public' if self.audience == Screening.audience_type_public else 'industry')

    def event_starts_simultaneous(self):
        main_title = self.film.title
        if main_title in DUPLICATE_EVENTS_TITLES_BY_MAIN:
            for event_title in DUPLICATE_EVENTS_TITLES_BY_MAIN[main_title]:
                events = [f for f in self.festival_data.films if f.title == event_title]
                if not events:
                    ERROR_COLLECTOR.add(f'Derived event {event_title} not found')
                    break
                event = events[0]
                if [s for s in event.screenings(self.festival_data) if s.start_datetime == self.start_dt]:
                    return True
        return False

    def set_combination_data(self, iffr_screening):
        # First use combination data with specific screened file type.
        self.set_combination_from_screened_film_type(iffr_screening, main_film=self.film)

        # Use the unspecific combination data.
        self.set_combination_from_summery(iffr_screening)

    def set_combination_from_screened_film_type(self, iffr_screening, main_film=None):
        main_film = main_film or self.film
        if iffr_screening.screened_film_type and not self.is_combination(main_film):
            screening_key = ScreeningKey(iffr_screening)
            self.screened_film_type_by_screening_key[screening_key] = iffr_screening.screened_film_type
            self.screening_key_by_main_film[main_film] = screening_key

    def set_combination_from_summery(self, iffr_screening):
        main_title = None  # Lords of Lockdown (hoofdprogramma)
        extra_title = None  # In hi ko (onderdeel van het programma)
        for part in self.combination_parts:
            if part.endswith('(hoofdprogramma)'):
                main_title = part.split('(')[0].strip()
            elif part.endswith('(onderdeel van het programma)'):
                extra_title = part.split('(')[0].strip()
        if extra_title == self.film.title:
            if main_title in COMBINATION_TITLE_BY_ABBREVIATION:
                main_title = COMBINATION_TITLE_BY_ABBREVIATION[main_title]
            if main_title not in AzPageParser.film_id_by_title:
                COUNTER.increase('wrong_title')
                print(f'Wrong title: {main_title}')
            main_film_id = AzPageParser.film_id_by_title[main_title]
            main_film = self.festival_data.get_film_by_id(main_film_id)
            iffr_screening.screened_film_type = ScreenedFilmType.DIRECTLY_COMBINED
            self.set_combination_from_screened_film_type(iffr_screening, main_film=main_film)

    def is_combination(self, film):
        is_combo = has_category(film, Film.category_combinations) \
                   or film in self.screening_key_by_main_film \
                   or is_combination_event(film)
        return is_combo

    def get_screen(self):
        screen_parse_name = self.location
        return get_screen_from_parse_name(self.festival_data, screen_parse_name, self.split_location)

    @classmethod
    def split_location(cls, location):
        city_name = FESTIVAL_CITY
        theater_parse_name = None
        screen_abbreviation = 'zaal'
        one_room_theaters = ['SKVR Centrum', 'V2', 'BRUTUS', 'Frank Taal Galerie', 'OX.Space', 'OX.Space',
                             'Secret locations', 'HAKA-gebouw', 'JOEY RAMONE', 'Oude Luxor',
                             'Station Rotterdam Centraal', 'Depot Boijmans Van Beuningen']
        if location in one_room_theaters:
            theater_parse_name = location
        elif location.startswith('de Doelen') or location.startswith('De Doelen'):
            theater_parse_name = 'de Doelen'
            screen_abbreviation = ' '.join(location.split()[2:])
        elif location.startswith('TR Schouwburg'):
            theater_parse_name = 'Schouwburg'
            screen_abbreviation = ' '.join(location.split()[2:])
        elif location.startswith('WORM'):
            theater_parse_name = 'WORM'
            screen_abbreviation = ' '.join(location.split()[1:])
        if not theater_parse_name:
            for regex in [cls.re_num_screen, cls.re_separator]:
                match = regex.match(location)
                if match:
                    theater_parse_name = match.group(1)
                    screen_abbreviation = match.group(2)
                    break
        return city_name, theater_parse_name, screen_abbreviation

    def handle_screening_starttag(self, tag, attrs, state_stack, state_awaiting, state_done):
        if state_stack.state_is(state_awaiting):
            if tag == 'h3' and len(attrs) > 0:
                if attrs[0][1] == 'sc-dlMDgC krsMKg':
                    state_stack.change(state_done)
            elif len(attrs) > 1 and attrs[1][0] == 'style':
                self.init_screening_data()
                self.state_stack.push(self.ScreeningParseState.IN_SCREENING)
        elif self.state_stack.state_is(self.ScreeningParseState.IN_SCREENING) and tag == 'strong':
            if len(attrs) > 0 and attrs[0][1] == 'bookingtable__date':
                self.state_stack.push(self.ScreeningParseState.IN_SCREENING_DATE)
        elif self.state_stack.state_is(self.ScreeningParseState.IN_SCREENING_LOCATION) and tag == 'ul':
            self.state_stack.push(self.ScreeningParseState.IN_COMBINATION_LIST)
        elif self.state_stack.state_is(self.ScreeningParseState.IN_COMBINATION_LIST) and tag == 'li':
            self.state_stack.push(self.ScreeningParseState.IN_COMBINATION_PART)

    def handle_screening_endtag(self, tag, state_stack, state_done):
        if self.state_stack.state_is(self.ScreeningParseState.IN_SCREENING_TIMES) and tag == 'time':
            self.set_screening_times()
            self.state_stack.change(self.ScreeningParseState.IN_SCREENING_LOCATION)
        elif self.state_stack.state_is(self.ScreeningParseState.IN_COMBINATION_LIST) and tag == 'ul':
            self.state_stack.pop()
        elif self.state_stack.state_is(self.ScreeningParseState.IN_COMBINATION_PART) and tag == 'li':
            self.combination_parts.append(self.combination_part)
            self.combination_part = ''
            self.state_stack.pop()
        elif self.state_stack.state_is(self.ScreeningParseState.AFTER_SCREENING_DATA) and tag == 'li':
            self.add_on_location_screening()
            self.state_stack.pop()
            self.state_stack.pop()
        elif self.state_stack.state_is(self.ScreeningParseState.IN_SCREENINGS) and tag == 'ul':
            self.state_stack.pop()
            state_stack.change(state_done)

    def handle_screening_data(self, data):
        if self.state_stack.state_is(self.ScreeningParseState.IN_SCREENING_DATE):
            self.start_date = self.parse_screening_date(data)
            self.state_stack.change(self.ScreeningParseState.IN_SCREENING_TIMES)
        elif self.state_stack.state_is(self.ScreeningParseState.IN_SCREENING_TIMES):
            self.times_str += data
        elif self.state_stack.state_is(self.ScreeningParseState.IN_SCREENING_LOCATION):
            self.location = data
            self.state_stack.change(self.ScreeningParseState.AFTER_SCREENING_DATA)
        elif self.state_stack.state_is(self.ScreeningParseState.IN_COMBINATION_PART):
            self.combination_part += data
        elif self.state_stack.state_is(self.ScreeningParseState.AFTER_SCREENING_DATA):
            self.set_screening_data(data)


class FilmInfoPageParser(ScreeningParser):
    class FilmInfoParseState(Enum):
        IDLE = auto()
        IN_ARTICLE = auto()
        IN_PARAGRAPH = auto()
        IN_EMPHASIS = auto()
        IN_REVIEWER = auto()
        AWAITING_SCREENINGS = auto()
        IN_SCREENINGS = auto()
        IN_TIMES = auto()
        AWAITING_LOCATION = auto()
        IN_LOCATION = auto()
        AWAITING_PROPERTIES = auto()
        DONE_ARTICLE = auto()
        IN_PROPERTIES = auto()
        IN_PROPERTY_KEY = auto()
        IN_PROPERTY_VALUE = auto()
        # IN_SCREENED_FILM_LIST = auto()
        # AWAITING_SCREENED_FILM_LINK = auto()
        # IN_SCREENED_FILM_LINK = auto()
        DONE = auto()

    debugging = DEBUGGING
    re_reviewer = re.compile(r'–\s(?P<reviewer>[^–0-9]+?)$')

    def __init__(self, festival_data, film, charset):
        ScreeningParser.__init__(self, festival_data, 'FI', self.debugging)
        self.festival_data = festival_data
        self.film = film
        self.reviewer = None
        self.start_dt_str = None
        self.screening_times_str = None
        self.location = None
        self.charset = charset
        self.event_is_combi = is_combination_event(film)
        self.article_paragraphs = []
        self.article_paragraph = ''
        self.article = None
        self.screened_film_slugs = []
        self.film_property_by_label = {}
        self.metadata_key = None

        # Print a bar in the debug file when debugging.
        self.print_debug(self.bar, f'Analysing FILM {self.film} {self.film.url}')

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.FilmInfoParseState.IDLE)

        # Get the film info of the current film. Its unique existence is guaranteed in SubsectionPageParser.
        self.film_info = self.film.film_info(self.festival_data)
        self.description = self.film_info.description

    def init_screening_data(self):
        self.start_dt_str = None
        self.screening_times_str = None
        self.location = None

    def set_combination(self):
        self.print_debug('Updating combination program', f'{self.film}')
        self.film_info.screened_films = []
        for screened_film_slug in self.screened_film_slugs:
            if self.event_is_combi:
                # Href attribute is the entire URL.
                screened_film_url = screened_film_slug
            else:
                # Slug is already internationalized.
                screened_film_url = IFFR_HOSTNAME + screened_film_slug
            film = self.festival_data.get_film_by_key('', screened_film_url)
            link_screened_film(self.festival_data, film, self.film, self.film_info)
        if self.screened_film_slugs:
            print(f'{len(self.screened_film_slugs)} screened films found.')
        if self.event_is_combi:
            COUNTER.increase('combination events')

    def get_reviewer(self, data):
        reviewer = None
        if has_category(self.film, Film.category_films):
            m = self.re_reviewer.match(data)
            if m:
                self.reviewer = m.group('reviewer')
        return reviewer

    def add_iffr_screening(self):
        # Update film duration.
        self.update_film_duration()

        # calculate the times.
        start_dt = datetime.datetime.fromisoformat(self.start_dt_str)          # 2025-01-30 10:00
        end_time_str = self.screening_times_str[-5:]    # Donderdag 30 januari 2025 | 10.00 - 23.30
        end_time = datetime.time.fromisoformat(end_time_str)
        end_dt = datetime.datetime.combine(start_dt.date(), end_time)

        # Get the screen.
        screen = get_screen_from_parse_name(self.festival_data, self.location, ScreeningParser.split_location)

        # Create the screening.
        q_and_a = ''
        iffr_screening = IffrScreening(self.film, screen, start_dt, end_dt, q_and_a,
                                       '', Screening.audience_type_public)

        # Add the screening to the festival data.
        self.add_screening(iffr_screening, display=DISPLAY_ADDED_SCREENING)

        COUNTER.increase('screenings')
        self.init_screening_data()

    def finish_film_info(self):
        # Update film duration.
        self.update_film_duration()

        # Add film info.
        self.set_article()
        if self.article:
            COUNTER.increase('articles')
        if not self.description:
            self.set_description_from_article(self.film.title)
        self.film_info.article = self.article
        self.film_info.metadata = self.film_property_by_label
        if self.film_info.metadata:
            COUNTER.increase('metadata')
        if self.reviewer:
            self.film_info.metadata['Reviewer'] = self.reviewer
            self.film.reviewer = self.reviewer
        if has_category(self.film, Film.category_combinations) or self.event_is_combi:
            self.set_combination()

    def update_film_duration(self):
        if self.film_property_by_label:
            minutes = self.film_property_by_label['Lengte'].rstrip('"')     # 100"
        else:
            minutes = 0
        self.film.duration = datetime.timedelta(minutes=int(minutes))

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        stack = self.state_stack
        state = self.FilmInfoParseState
        match [stack.state(), tag, attrs]:

            # Article part.
            case [state.IDLE, 'h1', _]:
                stack.change(state.IN_ARTICLE)
            case [state.IN_ARTICLE, 'p', _]:
                stack.push(state.IN_PARAGRAPH)
            case [state.IN_PARAGRAPH, 'strong', _]:
                stack.push(state.IN_EMPHASIS)
            case [state.IN_PARAGRAPH, 'em', _]:
                stack.push(state.IN_REVIEWER)

            # Screenings part.
            case [state.IN_ARTICLE, 'div', a] if a and a[0] == ('id', 'vertoningen'):
                stack.change(state.DONE_ARTICLE)
                stack.push(state.AWAITING_SCREENINGS)
            case [state.AWAITING_SCREENINGS, 'ul', _]:
                stack.change(state.IN_SCREENINGS)
            case [state.IN_SCREENINGS, 'time', a] if a and a[0][0] == 'datetime':
                self.start_dt_str = a[0][1]
                stack.push(state.IN_TIMES)
            case [state.AWAITING_LOCATION, 'span', _]:
                stack.change(state.IN_LOCATION)

            # Properties part.
            case [state.IN_ARTICLE, 'div', a] if a and a[0][1] == 'detail-list':
                stack.change(state.DONE_ARTICLE)
                stack.push(state.AWAITING_PROPERTIES)
            case [state.AWAITING_PROPERTIES, 'dl', _]:
                stack.change(state.IN_PROPERTIES)
            case [state.IN_PROPERTIES, 'dt', _]:
                stack.push(state.IN_PROPERTY_KEY)
            case [state.IN_PROPERTIES, 'dd', _]:
                stack.push(state.IN_PROPERTY_VALUE)
            case [state.DONE_ARTICLE, 'aside', _]:
                self.finish_film_info()
                stack.change(state.DONE)

            # Reached sentinel in unexpected state.
            case [s, 'aside', _] if s != state.DONE:
                COUNTER.increase('unexpected sentinel')
                DEBUG_RECORDER.add(f'State stack when encountering sentinel:\n{str(stack)}')
                stack.change(state.DONE)

        # # Combination part.
        # elif self.state_stack.state_is(self.FilmInfoParseState.AWAITING_SCREENED_FILM_LINK):
        #     if tag == 'a' and len(attrs) > 1 and attrs[0][1] == 'favourite-link':
        #         screened_film_slug = attrs[1][1]
        #         self.screened_film_slugs.append(screened_film_slug)
        #         self.state_stack.change(self.FilmInfoParseState.IN_SCREENED_FILM_LINK)
        #     elif tag == 'section':
        #         self.finish_film_info()
        #         self.state_stack.change(self.FilmInfoParseState.DONE)
        #
        # # Screening part.
        # else:
        #     self.handle_screening_starttag(tag, attrs, self.state_stack,
        #                                    self.ScreeningParseState.IN_SCREENINGS,
        #                                    self.FilmInfoParseState.AWAITING_SCREENED_FILM_LINK)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        stack = self.state_stack
        state = self.FilmInfoParseState
        match [stack.state(), tag]:

            # Article part.
            case [state.IN_EMPHASIS, 'strong']:
                stack.pop()
            case [state.IN_REVIEWER, 'em']:
                stack.pop()
            case [state.IN_PARAGRAPH, 'p']:
                self.add_paragraph()
                stack.pop()

            # Screenings part.
            case [state.IN_TIMES, 'time']:
                stack.change(state.AWAITING_LOCATION)
            case [state.IN_LOCATION, 'span']:
                self.add_iffr_screening()
                stack.pop()
            case [state.IN_SCREENINGS, 'ul']:
                stack.pop()

            # Properties part.
            case [state.IN_PROPERTY_KEY, 'dt']:
                stack.pop()
            case [state.IN_PROPERTY_VALUE, 'dd']:
                stack.pop()
            case [state.IN_PROPERTIES, 'dl']:
                stack.pop()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        stack = self.state_stack
        state = self.FilmInfoParseState
        match stack.state():

            # Article part.
            case state.IN_PARAGRAPH | state.IN_EMPHASIS:
                self.add_article_text(data)
            case state.IN_REVIEWER:
                self.get_reviewer(data)

            # Screenings part.
            case state.IN_TIMES:
                self.screening_times_str = data
            case state.IN_LOCATION:
                self.location = data

            # Properties part.
            case state.IN_PROPERTY_KEY:
                self.metadata_key = data.strip()
            case state.IN_PROPERTY_VALUE:
                self.film_property_by_label[self.metadata_key] = data.strip()


class IffrScreening(Screening):

    def __init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience,
                 screened_film_type=None, sold_out=None):
        Screening.__init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience, sold_out=sold_out)
        self.screened_film_type = screened_film_type
        self.sold_out = sold_out


class IffrData(FestivalData):

    def __init__(self, planner_data_dir):
        super().__init__(FESTIVAL_CITY, planner_data_dir)

    def film_key(self, title, url):
        return url

    def film_can_go_to_planner(self, filmid):
        return True


if __name__ == "__main__":
    main()
