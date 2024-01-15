#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import re
from enum import Enum, auto
from typing import Dict

from Shared.application_tools import ErrorCollector, DebugRecorder, comment, Config, Counter
from Shared.parse_tools import FileKeeper, try_parse_festival_sites, HtmlPageParser, ScreeningKey
from Shared.planner_interface import FilmInfo, Screening, ScreenedFilmType, ScreenedFilm, FestivalData, Film, \
    get_screen_from_parse_name
from Shared.web_tools import UrlFile, iri_slug_to_url, fix_json

ALWAYS_DOWNLOAD = False
DEBUGGING = True
DISPLAY_ADDED_SCREENING = True
COMBINATION_EVENT_TITLES = ['Babyfilmclub']
DUPLICATE_EVENTS_TITLES_BY_MAIN = {
    'Head South': ['Opening Night 2024: Head South'],
    'La Luna': ['Closing Night: La Luna (film only)', 'Closing Night: La Luna & Party'],
    'How to Have Sex': ['IFFR x EUR: How to Have Sex'],
    'Blackbird Blackbird Blackberry': ['IFFR Young Selectors: Blackbird Blackbird Blackberry'],
}

festival = 'IFFR'
festival_year = 2024
festival_city = 'Rotterdam'

# Files.
file_keeper = FileKeeper(festival, festival_year)
debug_file = file_keeper.debug_file

# URL information.
iffr_hostname = "https://iffr.com"

# Application tools.
error_collector = ErrorCollector()
debug_recorder = DebugRecorder(debug_file)
counter = Counter()


def main():
    # Initialize a festival data object.
    festival_data: IffrData = IffrData(file_keeper.plandata_dir)

    # Add film category keys.
    Film.category_by_string['Film'] = Film.category_films
    Film.category_by_string['CombinedProgram'] = Film.category_combinations
    Film.category_by_string['OtherProgram'] = Film.category_events

    # Set-up counters.
    counter.start('no description')
    counter.start('Film')
    counter.start('CombinedProgram')
    counter.start('OtherProgram')
    counter.start('feature films')
    counter.start('shorts')
    counter.start('duplicate events')
    counter.start('combination events')
    counter.start('public')
    counter.start('industry')
    counter.start('combinations from screenings')
    for screened_film_type in ScreenedFilmType:
        counter.start(screened_film_type.name)

    # Try parsing the websites.
    try_parse_festival_sites(parse_iffr_sites, festival_data, error_collector, debug_recorder, festival, counter)


def parse_iffr_sites(festival_data):
    comment('Parsing AZ pages.')
    get_films(festival_data)

    comment('Parsing subsection pages.')
    get_subsection_details(festival_data)

    comment('Parsing combination programs.')
    get_combination_programs(festival_data)

    comment('Parsing events.')
    get_events(festival_data)

    comment('Parsing regular film pages.')
    get_regular_films(festival_data)

    comment('Constructing combinations from screening data')
    set_combinations_from_screening_data(festival_data)


def get_films(festival_data):
    url_festival = iffr_hostname.split('/')[2].split('.')[0]
    az_url_path = f'/nl/{url_festival}/{festival_year}/a-z'
    az_url = iri_slug_to_url(iffr_hostname, az_url_path)
    az_file = file_keeper.az_file()
    url_file = UrlFile(az_url, az_file, error_collector, debug_recorder, byte_count=200)
    comment_at_download = f'Downloading AZ page: {az_url}, encoding: {url_file.encoding}'
    az_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
    if az_html is not None:
        comment(f'Analysing AZ page, encoding={url_file.encoding}')
        AzPageParser(festival_data).feed(az_html)


def get_combination_programs(festival_data):
    get_film_details(festival_data, Film.category_combinations, 'combination')


def get_events(festival_data):
    get_film_details(festival_data, Film.category_events, 'event')


def get_regular_films(festival_data):
    get_film_details(festival_data, Film.category_films, 'film', always_download=ALWAYS_DOWNLOAD)


def has_category(film, category):
    return Film.category_by_string[film.medium_category] == category


def get_film_details(festival_data, category, category_name, always_download=ALWAYS_DOWNLOAD):
    films = [film for film in festival_data.films if has_category(film, category)]
    for film in films:
        film_file = file_keeper.film_webdata_file(film.filmid)
        url_file = UrlFile(film.url, film_file, error_collector, debug_recorder, byte_count=300)
        comment_at_download = f'Downloading site of {film.title}: {film.url}, encoding: {url_file.encoding}'
        film_html = url_file.get_text(always_download=always_download, comment_at_download=comment_at_download)
        if film_html is not None:
            print(f'Analysing html file {film.filmid} of {category_name} {film.title}')
            FilmInfoPageParser(festival_data, film, url_file.encoding).feed(film_html)


def get_subsection_details(festival_data):
    for subsection in festival_data.subsection_by_name.values():
        subsection_file = file_keeper.numbered_webdata_file('subsection_file', subsection.subsection_id)
        url_file = UrlFile(subsection.url, subsection_file, error_collector, debug_recorder, byte_count=300)
        comment_at_download = f'Downloading {subsection.name} page: {subsection.url}, encoding: {url_file.encoding}'
        subsection_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
        if subsection_html is not None:
            encoding_str = f'encoding={url_file.encoding}'
            print(f'Analysing subsection page {subsection.subsection_id}, {subsection.name}, {encoding_str}.')
            SubsectionPageParser(festival_data, subsection).feed(subsection_html)


def set_combinations_from_screening_data(festival_data):
    for main_film, screening_key in ScreeningParser.screening_key_by_main_film.items():
        main_film_info = main_film.film_info(festival_data)
        screened_film_type = ScreeningParser.screened_film_type_by_screening_key[screening_key]
        films = [s.film for s in festival_data.screenings if s.film.filmid != main_film.filmid and ScreeningKey(s) == screening_key]
        screened_films = set(films)
        if screened_films:
            counter.increase('combinations from screenings')
            counter.increase(screened_film_type.name)
        for film in screened_films:
            screened_film_info = film.film_info(festival_data)
            screened_film_info.combination_films.append(main_film)
            screened_film = ScreenedFilm(film.filmid, film.title, screened_film_info.description, screened_film_type)
            main_film_info.screened_films.append(screened_film)


class AzPageParser(HtmlPageParser):
    class AzParseState(Enum):
        IDLE = auto()
        IN_FILM_SCRIPT = auto()
        DONE = auto()

    props_re = re.compile(
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
        HtmlPageParser.__init__(self, festival_data, debug_recorder, 'AZ', debugging=DEBUGGING)
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
        i = self.props_re.finditer(data)
        matches = [match for match in i]
        groups = [m.groupdict() for m in matches]
        for g in groups:
            self.medium_category = g['medium']
            self.title = fix_json(g['title'], error_collector=error_collector)
            self.url = iri_slug_to_url(iffr_hostname, g['url'])
            self.description, self.article = self.get_description(g['grid_desc'], g['list_desc'])
            if g['section']:
                self.section_name = fix_json(g['section'], error_collector=error_collector)
            if g['subsection']:
                self.subsection_name = fix_json(g['subsection'], error_collector=error_collector).rstrip()
            if g['subsection_url']:
                self.subsection_url = iri_slug_to_url(iffr_hostname, g['subsection_url'])
            self.sorted_title = fix_json(g['sorted_title'], error_collector=error_collector).lower()
            if not self.sorted_title:
                self.sorted_title = re.sub(r'\\', '', g['sorted_title'])
                """Workaround for the 2024 edition to handle one double quote in sort string."""
                print(f'{self.sorted_title=} after fix.')
            self.duration = self.get_duration(g['duration'])
            self.add_film()
            self.init_film_data()

    @staticmethod
    def get_description(grid_description, list_description):
        description = fix_json(grid_description, error_collector=error_collector)
        article = fix_json(list_description, error_collector=error_collector)
        if not description:
            description = article
        if list_description == 'Binnenkort meer informatie over deze film.':
            description = ''
            counter.increase('no description')
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
            error_collector.add(f'Could\'t create film from {self.title}', self.url)
        else:
            self.film.medium_category = self.medium_category
            if self.film.medium_category not in Film.category_by_string:
                error_msg = f'{self.film.title}', f'{self.film.medium_category} from {self.url}'
                error_collector.add(f'Unexpected category "{self.film.medium_category}"', error_msg)
            self.film.duration = self.duration
            self.film.sortstring = self.sorted_title
            self.increase_per_duration_class_counter(self.film)
            self.increase_per_film_category_counter()
            self.film_id_by_title[self.film.title] = self.film.filmid
            print(f'Adding FILM: {self.title} ({self.film.duration_str()}) {self.film.medium_category}')
            self.festival_data.films.append(self.film)
            self.film.subsection = self.get_subsection()
            self.add_film_info()

    def add_film_info(self):
        if len(self.description) > 0:
            film_info = FilmInfo(self.film.filmid, self.description, self.article)
            self.festival_data.filminfos.append(film_info)

    def increase_per_duration_class_counter(self, film):
        key = 'feature films' if film.duration > self.max_short_duration else 'shorts'
        counter.increase(key)

    def increase_per_film_category_counter(self):
        counter.increase(self.film.medium_category)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.AzParseState.IDLE) and tag == 'script':
            if len(attrs) > 1 and attrs[0] == ('id', '__NEXT_DATA__'):
                self.state_stack.change(self.AzParseState.IN_FILM_SCRIPT)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.AzParseState.IN_FILM_SCRIPT):
            self.parse_props(data)
            self.state_stack.change(self.AzParseState.DONE)


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
        HtmlPageParser.__init__(self, festival_data, debug_recorder, debug_prefix, debugging=debugging)
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
        self.screenings = []

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.ScreeningParseState.IDLE)

    def init_screening_data(self):
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
        self.sold_out = False

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
            self.sold_out = True
        if data.endswith('ondertiteld'):
            self.subtitles = data

    def add_on_location_screening(self):
        if self.event_starts_simultaneous():
            print(f'Screening skipped in favour of derived event: {self.film.title}')
            counter.increase('duplicate events')
            return
        self.screen = self.get_screen()
        iffr_screening = IffrScreening(self.film, self.screen, self.start_dt, self.end_dt, self.q_and_a,
                                       self.extra, self.audience, self.screened_film_type, self.sold_out)
        self.set_combination_data(iffr_screening)
        self.set_combination_main_film(iffr_screening)
        iffr_screening.subtitles = self.subtitles
        self.add_screening(iffr_screening, display=DISPLAY_ADDED_SCREENING)
        counter.increase('public' if self.audience == Screening.audience_type_public else 'industry')
        self.screenings.append(self.screening)

    def event_starts_simultaneous(self):
        main_title = self.film.title
        if main_title in DUPLICATE_EVENTS_TITLES_BY_MAIN:
            for event_title in DUPLICATE_EVENTS_TITLES_BY_MAIN[main_title]:
                events = [f for f in self.festival_data.films if f.title == event_title]
                if not events:
                    error_collector.add(f'Derived event {event_title} not found')
                    break
                event = events[0]
                if [s for s in event.screenings(self.festival_data) if s.start_datetime == self.start_dt]:
                    return True
        return False

    def set_combination_main_film(self, iffr_screening):
        main_title = None   # Lords of Lockdown (hoofdprogramma)
        extra_title = None  # In hi ko (onderdeel van het programma)
        for part in self.combination_parts:
            if part.endswith('(hoofdprogramma)'):
                main_title = part.split('(')[0].strip()
            elif part.endswith('(onderdeel van het programma)'):
                extra_title = part.split('(')[0].strip()
        if extra_title == self.film.title:
            try:
                # Find the film in the list of regular films.
                main_film_id = AzPageParser.film_id_by_title[main_title]
            except KeyError:
                # Combination programs are handled differently.
                pass
            else:
                main_film = self.festival_data.get_film_by_id(main_film_id)
                if main_film is None:
                    error_collector.add('Main film not found', f'Film ID: {main_film_id}')
                else:
                    if not self.is_combination(main_film):
                        iffr_screening.screened_film_type = ScreenedFilmType.DIRECTLY_COMBINED
                        self.set_combination_data(iffr_screening, main_film)

    def set_combination_data(self, iffr_screening, main_film=None):
        if self.is_combination(self.film):
            # Already combined in film info page parser.
            return
        if iffr_screening.screened_film_type:
            main_film = main_film or self.film
            screening_key = ScreeningKey(iffr_screening)
            self.screened_film_type_by_screening_key[screening_key] = iffr_screening.screened_film_type
            self.screening_key_by_main_film[main_film] = screening_key

    def is_combination(self, film):
        is_combo = has_category(film, Film.category_combinations) \
            or film in self.screening_key_by_main_film \
            or (film.title in COMBINATION_EVENT_TITLES and has_category(film, Film.category_events))
        return is_combo

    def get_screen(self):
        screen_parse_name = self.location
        return get_screen_from_parse_name(self.festival_data, screen_parse_name, self.split_location)

    def split_location(self, location):
        city_name = festival_city
        theater_parse_name = None
        screen_abbreviation = 'zaal'
        one_room_theaters = ['SKVR Centrum', 'V2', 'BRUTUS', 'Frank Taal Galerie', 'OX.Space', 'OX.Space',
                             'Secret locations', 'HAKA-gebouw', 'JOEY RAMONE', 'Oude Luxor',
                             'Station Rotterdam Centraal', 'Depot Boijmans Van Beuningen']
        if location in one_room_theaters:
            theater_parse_name = location
        elif location.startswith('de Doelen'):
            theater_parse_name = 'de Doelen'
            screen_abbreviation = ' '.join(location.split()[2:])
        elif location.startswith('TR Schouwburg'):
            theater_parse_name = 'Schouwburg'
            screen_abbreviation = ' '.join(location.split()[2:])
        elif location.startswith('WORM'):
            theater_parse_name = 'WORM'
            screen_abbreviation = ' '.join(location.split()[1:])
        if not theater_parse_name:
            for regex in [self.re_num_screen, self.re_separator]:
                match = regex.match(location)
                if match:
                    theater_parse_name = match.group(1)
                    screen_abbreviation = match.group(2)
                    break
        return city_name, theater_parse_name, screen_abbreviation

    def handle_screening_starttag(self, tag, attrs, state_stack, state_awaiting, state_done):
        if state_stack.state_is(state_awaiting) and tag == 'h3':
            if len(attrs) > 0:
                if attrs[0][1].endswith('bookingtable__title'):
                    self.state_stack.push(self.ScreeningParseState.IN_SCREENINGS)
                elif attrs[0][1] == 'sc-dlMDgC krsMKg':
                    state_stack.change(state_done)
        elif self.state_stack.state_is(self.ScreeningParseState.IN_SCREENINGS) and tag == 'li':
            if len(attrs) > 1 and attrs[1][0] == 'style':
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
        IN_SCREENED_FILM_LIST = auto()
        AWAITING_SCREENINGS = auto()
        AWAITING_SCREENED_FILM_LINK = auto()
        IN_SCREENED_FILM_LINK = auto()
        DONE = auto()

    debugging = DEBUGGING

    def __init__(self, festival_data, film, charset):
        ScreeningParser.__init__(self, festival_data, 'FI', self.debugging)
        self.festival_data = festival_data
        self.film = film
        self.charset = charset
        self.event_is_combi = film.title in COMBINATION_EVENT_TITLES and has_category(film, Film.category_events)
        self.article_paragraphs = []
        self.article_paragraph = ''
        self.article = None
        self.screened_film_slugs = []

        # Print a bar in the debug file when debugging.
        self.print_debug(self.bar, f'Analysing FILM {self.film} {self.film.url}')

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.FilmInfoParseState.IDLE)

        # Get the film info of the current film. Its unique existence is guaranteed in AzPageParser.
        self.film_info = self.film.film_info(self.festival_data)

    def set_article(self):
        HtmlPageParser.set_article(self)
        self.film_info.article = self.article

    def set_combination(self):
        self.print_debug('Updating combination program', f'{self.film}')
        self.film_info.screened_films = []
        for screened_film_slug in self.screened_film_slugs:
            if self.event_is_combi:
                # Href attribute is the entire URL.
                screened_film_url = screened_film_slug
            else:
                # Slug is already internationalized.
                screened_film_url = iffr_hostname + screened_film_slug
            film = self.festival_data.get_film_by_key('', screened_film_url)
            film_info = film.film_info(self.festival_data)
            film_info.combination_films.append(self.film)
            screened_film = ScreenedFilm(film.filmid, film.title, film_info.description)
            self.film_info.screened_films.append(screened_film)
        if self.screened_film_slugs:
            print(f'{len(self.screened_film_slugs)} screened films found.')
        if self.event_is_combi:
            counter.increase('combination events')

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        # Article part.
        if self.state_stack.state_is(self.FilmInfoParseState.IDLE) and tag == 'div' and len(attrs) > 0:
            if attrs[0][0] == 'class' and attrs[0][1] in ['sc-fujyAs induiK', 'sc-dkuGKe fXALKH']:
                self.state_stack.push(self.FilmInfoParseState.IN_ARTICLE)
                self.print_debug(f'{self.event_is_combi=}')
        elif self.state_stack.state_is(self.FilmInfoParseState.IN_ARTICLE):
            if tag == 'p':
                self.state_stack.push(self.FilmInfoParseState.IN_PARAGRAPH)
            elif self.event_is_combi and tag == 'a' and len(attrs):
                screened_film_slug = attrs[0][1]
                self.screened_film_slugs.append(screened_film_slug)
                self.state_stack.push(self.FilmInfoParseState.IN_SCREENED_FILM_LIST)
        elif self.state_stack.state_is(self.FilmInfoParseState.IN_PARAGRAPH) and tag == 'em':
            self.state_stack.push(self.FilmInfoParseState.IN_EMPHASIS)

        # Combination part.
        elif self.state_stack.state_is(self.FilmInfoParseState.AWAITING_SCREENED_FILM_LINK):
            if tag == 'a':
                if len(attrs) > 1 and attrs[0][1] == 'favourite-link':
                    screened_film_slug = attrs[1][1]
                    self.screened_film_slugs.append(screened_film_slug)
                    self.state_stack.change(self.FilmInfoParseState.IN_SCREENED_FILM_LINK)
            elif tag == 'section':
                if has_category(self.film, Film.category_combinations) or self.event_is_combi:
                    self.set_combination()
                self.state_stack.change(self.FilmInfoParseState.DONE)

        # Screening part.
        else:
            self.handle_screening_starttag(tag, attrs, self.state_stack,
                                           self.FilmInfoParseState.AWAITING_SCREENINGS,
                                           self.FilmInfoParseState.AWAITING_SCREENED_FILM_LINK)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_is(self.FilmInfoParseState.IN_EMPHASIS) and tag == 'em':
            self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmInfoParseState.IN_PARAGRAPH) and tag == 'p':
            self.state_stack.pop()
            self.add_paragraph()
        elif self.state_stack.state_is(self.FilmInfoParseState.IN_ARTICLE) and tag == 'div':
            self.state_stack.pop()
            self.set_article()
            self.state_stack.change(self.FilmInfoParseState.AWAITING_SCREENINGS)
        elif self.state_stack.state_is(self.FilmInfoParseState.IN_SCREENED_FILM_LIST) and tag == 'a':
            self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmInfoParseState.IN_SCREENED_FILM_LINK) and tag == 'a':
            self.state_stack.change(self.FilmInfoParseState.AWAITING_SCREENED_FILM_LINK)
        else:
            self.handle_screening_endtag(tag, self.state_stack, self.FilmInfoParseState.AWAITING_SCREENED_FILM_LINK)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_in([self.FilmInfoParseState.IN_PARAGRAPH,
                                      self.FilmInfoParseState.IN_EMPHASIS,
                                      self.FilmInfoParseState.IN_ARTICLE]):
            self.article_paragraph += data.replace('\n', ' ')
        else:
            self.handle_screening_data(data)


class SubsectionPageParser(HtmlPageParser):
    class SubsectionsParseState(Enum):
        IDLE = auto()
        AWAITING_DESCRIPTION = auto()
        IN_DESCRIPTION = auto()
        DONE = auto()

    def __init__(self, festival_data, subsection):
        HtmlPageParser.__init__(self, festival_data, debug_recorder, 'SEC', debugging=DEBUGGING)
        self.festival_data = festival_data
        self.subsection = subsection
        self.state_stack = self.StateStack(self.print_debug, self.SubsectionsParseState.IDLE)
        self.description = None

    def update_subsection(self, description=None):
        self.subsection.description = description

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.SubsectionsParseState.IDLE) and tag == 'h1':
            self.state_stack.change(self.SubsectionsParseState.AWAITING_DESCRIPTION)
        elif self.state_stack.state_is(self.SubsectionsParseState.AWAITING_DESCRIPTION) and tag == 'h2':
            self.update_subsection()
            self.state_stack.change(self.SubsectionsParseState.DONE)
        elif self.state_stack.state_is(self.SubsectionsParseState.AWAITING_DESCRIPTION) and tag == 'section':
            self.state_stack.change(self.SubsectionsParseState.IN_DESCRIPTION)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.SubsectionsParseState.IN_DESCRIPTION):
            self.update_subsection(data)
            self.state_stack.change(self.SubsectionsParseState.DONE)


class IffrScreening(Screening):

    def __init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience,
                 screened_film_type=None, sold_out=None):
        Screening.__init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience)
        self.screened_film_type = screened_film_type
        self.sold_out = sold_out


class IffrData(FestivalData):

    def __init__(self, planner_data_dir):
        FestivalData.__init__(self, planner_data_dir, festival_city)

    def film_key(self, title, url):
        return url

    def film_can_go_to_planner(self, filmid):
        return True


if __name__ == "__main__":
    main()
