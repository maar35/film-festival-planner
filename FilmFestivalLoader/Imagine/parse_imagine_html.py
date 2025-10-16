#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 18 20:56:44 2021

@author: maartenroos
"""
import csv
import datetime
import os
import re
from enum import Enum, auto

from Shared.application_tools import ErrorCollector, DebugRecorder, comment, Counter
from Shared.parse_tools import FileKeeper, HtmlPageParser, try_parse_festival_sites
from Shared.planner_interface import FilmInfo, FestivalData, Film, get_screen_from_parse_name, AUDIENCE_PUBLIC, \
    ScreenedFilm, ScreenedFilmType
from Shared.web_tools import UrlFile

DOWNLOAD_WORKS = True       # Python html reader gets "certificate not found", used curl instead.
TICKETS_AVAILABLE = True
FILE_BY_URL = {}
ALWAYS_DOWNLOAD = False
DISPLAY_ADDED_SCREENING = False
SORTING_FROM_SITE = False

FESTIVAL = 'Imagine'
FESTIVAL_YEAR = 2025
FESTIVAL_CITY = 'Amsterdam'

# Files.
FILE_KEEPER = FileKeeper(FESTIVAL, FESTIVAL_YEAR)
AZ_FILE = FILE_KEEPER.az_file()
URL_MAP_FILE = os.path.join(FILE_KEEPER.webdata_dir, 'url_map.txt')

# URL information.
IMAGINE_HOSTNAME = 'https://www.imaginefilmfestival.nl'
AZ_URL_PATH = f'/programma{FESTIVAL_YEAR}'

# Application tools.
ERROR_COLLECTOR = ErrorCollector()
DEBUG_RECORDER = DebugRecorder(FILE_KEEPER.debug_file)
COUNTER = Counter()


def main():
    # Initialize a festival data object.
    comment('Creating festival data object.')
    festival_data = ImagineData(FILE_KEEPER.plandata_dir)

    # Set up counters.
    setup_counters()

    # Try parsing the websites.
    try_parse_festival_sites(
        parse_imagine_sites, festival_data, ERROR_COLLECTOR, DEBUG_RECORDER,
        festival=FESTIVAL,
        counter=COUNTER)

    # Write a map file for curl if downloading doesn't work.
    write_url_map_file()


def setup_counters():
    COUNTER.start('q&a screenings')
    COUNTER.start('q&a from article')
    COUNTER.start('q&a from ticket label')
    COUNTER.start('combination programs')
    COUNTER.start('screened films')
    COUNTER.start('Not parsed screened films')
    COUNTER.start('no description')


def write_url_map_file():
    if not DOWNLOAD_WORKS:
        dialect = csv.unix_dialect
        dialect.delimiter = ';'
        dialect.quotechar = '"'
        dialect.doublequote = True
        dialect.quoting = csv.QUOTE_MINIMAL
        rows = [[url, file] for url, file in FILE_BY_URL.items()]
        with open(URL_MAP_FILE, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile, dialect=dialect)
            csv_writer.writerows(rows)


def parse_imagine_sites(festival_data):
    comment('Parsing AZ pages and film pages.')
    get_films(festival_data)


def get_films(festival_data):
    az_url = IMAGINE_HOSTNAME + AZ_URL_PATH
    url_file = UrlFile(az_url, AZ_FILE, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=100)
    comment_at_download = f'Downloading AZ page from {az_url} to {url_file.path}.'
    az_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
    if az_html is not None:
        comment(f'Downloaded AZ page, encoding={url_file.encoding}')
        AzPageParser(festival_data).feed(az_html)


def get_details_of_one_film(festival_data, film, debug_prefix=None):
    film_file = FILE_KEEPER.film_webdata_file(film.film_id)
    if not DOWNLOAD_WORKS:
        FILE_BY_URL[film.url] = film_file
        return
    url_file = UrlFile(film.url, film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=256)
    comment_at_download = f'Downloading site of {film.title}: {film.url}, to {url_file.path}'
    film_html = url_file.get_text(comment_at_download=comment_at_download, always_download=ALWAYS_DOWNLOAD)

    if film_html is not None:
        print(f"Analysing html file {film.film_id} of {film.title} {film.url}")
        FilmPageParser(festival_data, film, debug_prefix=debug_prefix).feed(film_html)


class AzPageParser(HtmlPageParser):
    class AzParseState(Enum):
        IDLE = auto()
        IN_LIST = auto()
        IN_SCREENING = auto()
        IN_SORT_TITLE = auto()
        IN_SECTION = auto()
        IN_TYPE = auto()
        IN_TITLE = auto()
        IN_SCREEN = auto()
        IN_LANGUAGE = auto()
        IN_DURATION = auto()

    def __init__(self, festival_data):
        HtmlPageParser.__init__(self, festival_data, DEBUG_RECORDER, 'AZ', debugging=True)
        self.film = None
        self.url = None
        self.title = None
        self.sort_title = None
        self.duration = None
        self.section_name = None
        self.section_color = None
        self.screen_name = None
        self.screen = None
        self.start_dt = None
        self.end_dt = None
        self.medium_type = None
        self.audience = None
        self.qa = None
        self.subtitles = None
        self.state_stack = self.StateStack(self.print_debug, self.AzParseState.IDLE)
        self._init_categories()
        self._init_screening_data()

    def feed(self, data):
        super().feed(data)
        comment('Assigning Q&A property to the relevant screenings.')
        QaScreeningKey.update_q_and_a_screenings(self.festival_data)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.AzParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'ul', a] if a and a[0][1] == 'screenings imagine-rows filterable':
                stack.change(state.IN_LIST)
            case [state.IN_LIST, 'li', a] if len(a) > 3 and a[0][1] == 'screening item':
                self.url = a[2][1]
                self.sort_title = a[3][1]
                stack.push(state.IN_SCREENING)
            case [state.IN_SCREENING, 'time', a] if a and a[0][0] == 'datetime':
                self.start_dt = datetime.datetime.fromisoformat(a[0][1])
            case [state.IN_SCREENING, 'section', _]:
                stack.push(state.IN_SECTION)
            case [state.IN_SECTION, 'div', a] if a and a[0][1].startswith('background-color'):
                self.section_color = attrs[0][1].split(':')[1]
            case [state.IN_SCREENING, 'div', a] if a and a[0][1] == 'type':
                stack.push(state.IN_TYPE)
            case [state.IN_SCREENING, 'h2', _]:
                stack.push(state.IN_TITLE)
            case [state.IN_SCREENING, 'i', a] if a and a[0][1] == 'fa fa-map-marker':
                stack.push(state.IN_SCREEN)
            case [state.IN_SCREENING, 'i', a] if a and a[0][1] == 'fa fa-clock-o':
                stack.push(state.IN_DURATION)
            case [state.IN_SCREENING, 'i', a] if a and a[0][1] == 'fa fa-map-commenting':
                stack.push(state.IN_LANGUAGE)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        if self.state_stack.state_is(self.AzParseState.IN_SCREENING) and tag == 'li':
            self._add_imagine_screening()
            self.state_stack.pop()

    def handle_data(self, data):
        super().handle_data(data)

        stack = self.state_stack
        state = self.AzParseState
        match stack.state():
            case state.IN_SECTION if data.strip():
                self.section_name = data
                stack.pop()
            case state.IN_TYPE:
                self.medium_type = data
                stack.pop()
            case state.IN_TITLE:
                self.title = self.get_title(data)
                stack.pop()
            case state.IN_SCREEN:
                self.screen = self._get_imagine_screen(data)
                stack.pop()
            case state.IN_DURATION:
                self.duration = self.get_duration(data)
                stack.pop()
            case state.IN_LANGUAGE:
                self.subtitles = self.get_subtitles(data)
                stack.pop()

    @staticmethod
    def _init_categories():
        Film.category_by_string['documentary'] = Film.category_films
        Film.category_by_string['Extra'] = Film.category_films
        Film.category_by_string['feature'] = Film.category_films
        Film.category_by_string['shorts'] = Film.category_combinations
        Film.category_by_string['special'] = Film.category_events
        Film.category_by_string['talk'] = Film.category_events
        Film.category_by_string['Talk'] = Film.category_events
        Film.category_by_string['Workshop'] = Film.category_events
        Film.category_by_string['vr/expanded'] = Film.category_events

    def _init_screening_data(self):
        self.film = None
        self.url = None
        self.title = None
        self.sort_title = None
        self.duration = None
        self.section_name = None
        self.section_color = None
        self.screen_name = None
        self.screen = None
        self.start_dt = None
        self.end_dt = None
        self.medium_type = None
        self.audience = AUDIENCE_PUBLIC

        self.qa = ''
        self.subtitles = ''

    @staticmethod
    def get_duration(data):
        minutes = data.strip().split()[0]  # 106 min.
        duration = datetime.timedelta(minutes=int(minutes))
        return duration

    def _get_imagine_screen(self, data):
        screen_parse_name = data.strip()
        splitter = LocationSplitter.split_location
        return get_screen_from_parse_name(self.festival_data, screen_parse_name, splitter)

    def get_title(self, data):
        qa_string = ' + Q&A'
        self.qa = 'Q&A' if data.endswith(qa_string) else ''
        title = data[:-len(qa_string)] if self.qa else data
        return title

    @staticmethod
    def get_subtitles(data):
        re_parentheses = re.compile(r'^(?P<language>.*)\((?P<subs>.*)\).*')  # Spaans (Engels ondertiteld)
        matches = re_parentheses.match(data)
        subtitles = matches.group('subs') if matches else ''
        return subtitles

    def _add_film(self):
        # Create a new film.
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            ERROR_COLLECTOR.add(f'Could not create film:', '{self.title} ({self.url})')
        else:
            # Fill details.
            self.film.duration = self.duration
            self.film.subsection = self._get_subsection()
            self.film.medium_category = self.medium_type
            if SORTING_FROM_SITE:
                self.film.sort_string = self.sort_title

            # Add the film to the list.
            self.festival_data.films.append(self.film)

            # Get the film info.
            get_details_of_one_film(self.festival_data, self.film)

    def _get_subsection(self):
        if self.section_name:
            section = self.festival_data.get_section(self.section_name, self.section_color)
            dummy_url = 'https://www.imaginefilmfestival.nl/themas/'
            subsection = self.festival_data.get_subsection(section.name, dummy_url, section)
            return subsection
        return None

    def _add_imagine_screening(self):
        # Get the film.
        try:
            self.film = self.festival_data.get_film_by_key(self.title, self.url)
        except (KeyError, ValueError):
            self._add_film()

        # Calculate the screening's end time.
        duration = self.film.duration
        self.start_dt = self.start_dt.replace(tzinfo=None)
        self.end_dt = self.start_dt + duration

        # Add screening to the list.
        HtmlPageParser.add_screening_from_fields(
            self,
            self.film,
            self.screen,
            self.start_dt,
            self.end_dt,
            qa=self.qa,
            audience=self.audience,
            subtitles=self.subtitles,
            display=DISPLAY_ADDED_SCREENING,
        )

        # Initialize the next round of parsing.
        self._init_screening_data()


class FilmPageParser(HtmlPageParser):
    class FilmInfoParseState(Enum):
        IDLE = auto()
        AWAITING_SCREENINGS = auto()
        IN_SCREENINGS = auto()
        IN_SCREENING = auto()
        IN_TIME = auto()
        IN_SCREEN = auto()
        AWAITING_TICKET_LINK = auto()
        IN_TICKETS_LINK = auto()
        AWAITING_DESCRIPTION = auto()
        IN_DESCRIPTION = auto()
        IN_ARTICLE = auto()
        IN_ALT_ARTICLE = auto()
        AWAITING_METADATA = auto()
        IN_METADATA = auto()
        IN_METADATA_KEY = auto()
        IN_METADATA_VALUE = auto()
        AWAITING_SCREENED_FILMS = auto()
        IN_SCREENED_FILMS = auto()
        IN_SCREENED_FILM = auto()
        AWAITING_SCREENED_TITLE = auto()
        DONE_SCREENED_TITLE = auto()
        IN_SCREENED_TITLE = auto()
        DONE = auto()

    nl_month_by_name = {'okt': 10, 'nov': 11}
    re_date = re.compile(r'(maan|dins|woens|donder|vrij|zater|zon)dag\s+(\d+)\s+([a-z]+)')
    """ Parse e.g. 'vrijdag 31 oktober' from an article."""

    def __init__(self, festival_data, film, debug_prefix=None):
        debug_prefix = debug_prefix or 'F'
        HtmlPageParser.__init__(self, festival_data, DEBUG_RECORDER, debug_prefix, debugging=True)
        self.film = film
        self.screening_start_date = None
        self.screening_start_time = None
        self.screening_screen = None
        self.screening_ticket_label = None
        self.description = None
        self.film_property_by_label = {}
        self.metadata_key = None
        self.screened_title = None
        self.screened_url = None
        self.screened_films = []
        self.combination_urls = []
        self.state_stack = self.StateStack(self.print_debug, self.FilmInfoParseState.IDLE)
        self.print_debug(f"{40 * '-'} ", f"Analysing FILM {film}, {film.url}")

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.FilmInfoParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'h2', _]:
                stack.push(state.AWAITING_SCREENINGS)
            case [state.IDLE, 'div', a] if a and a[0][1] == 'zmovies-programma':
                COUNTER.increase('combination programs')
                stack.push(state.AWAITING_SCREENED_FILMS)
            case [state.IDLE, 'div', a] if a and a[0][1] == 'nectar-global-section before-footer':
                stack.change(state.DONE)
            case [state.IN_SCREENINGS, 'tr', _]:
                self.screening_start_date = attrs[1][1]
                stack.push(state.IN_SCREENING)
            case [state.IN_SCREENING, 'td', a] if a and a[0][1] == 'time':
                stack.push(state.IN_TIME)
            case [state.IN_SCREENING, 'td', a] if a and a[0][1] == 'theatre':
                stack.push(state.IN_SCREEN)
            case [state.IN_SCREENING, 'td', a] if a and a[0][1] == 'ticket':
                stack.push(state.AWAITING_TICKET_LINK)
            case [state.AWAITING_TICKET_LINK, 'a', _]:
                stack.change(state.IN_TICKETS_LINK)
            case [state.IDLE, 'div', a] if a and a[0] == ('class', 'container-wrap'):
                stack.push(state.AWAITING_DESCRIPTION)
            case [state.AWAITING_DESCRIPTION, 'div', a] if a and a[0] == ('class', 'text'):
                stack.change(state.IN_DESCRIPTION)
            case [state.AWAITING_DESCRIPTION, 'div', a] if a and a[0] == ('class', 'w6'):
                stack.change(state.IN_ALT_ARTICLE)
            case [state.AWAITING_METADATA, 'div', a] if a and a[0] == ('class', 'meta'):
                stack.change(state.IN_METADATA)
            case [state.IN_METADATA, 'div', _]:
                stack.push(state.IN_METADATA_KEY)
            case [state.AWAITING_SCREENED_FILMS, 'ul', _]:
                stack.change(state.IN_SCREENED_FILMS)
            case [state.IN_SCREENED_FILMS, 'li', _]:
                self._init_screened_film()
                stack.push(state.IN_SCREENED_FILM)
            case [state.IN_SCREENED_FILM, 'a', a] if a and a[0][0] == 'href':
                self.screened_url = a[0][1]
                stack.change(state.AWAITING_SCREENED_TITLE)
            case [state.AWAITING_SCREENED_TITLE, 'h3', _]:
                stack.push(state.IN_SCREENED_TITLE)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        stack = self.state_stack
        state = self.FilmInfoParseState
        match [stack.state(), tag]:
            case [state.AWAITING_SCREENINGS, 'h2']:
                stack.pop()
            case [state.IN_SCREENING, 'tr']:
                stack.pop()
            case [state.IN_SCREENINGS, 'table']:
                stack.pop()
            case [(state.IN_ARTICLE | state.IN_ALT_ARTICLE), 'p']:
                self.add_paragraph()
            case [state.IN_ARTICLE, 'div']:
                stack.change(state.AWAITING_METADATA)
            case [state.IN_ALT_ARTICLE, 'div']:
                self._finish_film_info()
                stack.pop()
            case [state.IN_METADATA_VALUE, 'div']:
                stack.pop()
            case [state.IN_METADATA, 'div']:
                self._finish_film_info()
                stack.pop()
            case [state.IN_SCREENED_TITLE, 'h3']:
                stack.pop()
                stack.change(state.DONE_SCREENED_TITLE)
            case [state.DONE_SCREENED_TITLE, 'li']:
                self._add_screened_film()
                stack.pop()
            case [state.IN_SCREENED_FILMS, 'ul']:
                stack.pop()

    def handle_data(self, data):
        super().handle_data(data)

        stack = self.state_stack
        state = self.FilmInfoParseState
        match stack.state():
            case state.AWAITING_SCREENINGS if data == 'Screenings & Tickets':
                stack.change(state.IN_SCREENINGS)
            case state.IN_TIME:
                self.screening_start_time = data
                stack.pop()
            case state.IN_SCREEN:
                self.screening_screen = data
                stack.pop()
            case state.IN_TICKETS_LINK:
                self.screening_ticket_label = data
                self._add_qa_record_from_ticket_label()
                stack.pop()
            case state.IN_DESCRIPTION if len(data.strip()):
                self.description = data
                if not self.description.strip():
                    COUNTER.increase(f'no description')
                stack.change(state.IN_ARTICLE)
            case (state.IN_ARTICLE | state.IN_ALT_ARTICLE):
                self.article_paragraph += data
                if 'nagesprek' in data:
                    self._add_qa_record_from_article(data)
            case state.IN_METADATA_KEY:
                self.metadata_key = data.strip()
                stack.change(state.IN_METADATA_VALUE)
            case state.IN_METADATA_VALUE:
                self.film_property_by_label[self.metadata_key] = data.strip()
            case state.IN_SCREENED_TITLE:
                self.screened_title = data.strip()

    def add_paragraph(self):
        paragraph = self.article_paragraph
        if len(paragraph) > 0:
            self.article_paragraphs.append(paragraph.strip())
        self.article_paragraph = ''

    def set_article(self):
        descr_threshold = 512
        if len(self.film_property_by_label):
            properties = [f'{key}: {value}' for (key, value) in self.film_property_by_label.items()]
            metadata = '\n'.join(properties)
            self.article_paragraph = metadata
            self.add_paragraph()
        if self.article_paragraphs:
            self.description = self.description or self.article_paragraphs[0]
            if len(self.description) > descr_threshold:
                self.description = self.description[:descr_threshold] + '…'
            self.article = '\n\n'.join(self.article_paragraphs)
        else:
            self.description = self.description or ''
            self.article = ''

    def _init_screened_film(self):
        self.screened_title = None
        self.screened_url = None

    def _add_screened_film(self):
        COUNTER.increase('screened films')

        # Create a new film.
        screened_film = self.festival_data.create_film(self.screened_title, self.screened_url)
        if screened_film is None:
            ERROR_COLLECTOR.add(f'Could not create screened film', f'{self.screened_title} ({self.screened_url})')
        else:
            # Fill details.
            screened_film.subsection = self.film.subsection
            screened_film.medium_category = self.film.medium_category
            if SORTING_FROM_SITE:
                screened_film.sort_string = self.film.sort_str()

            # Add the screened film to the list.
            self.festival_data.films.append(screened_film)

            # Get film details.
            get_details_of_one_film(self.festival_data, screened_film, debug_prefix='SF')

            # Set film properties.
            screened_film_info = screened_film.film_info(self.festival_data)
            try:
                minutes_str = screened_film_info.metadata['Speeltijd']      # 18 minuten
            except KeyError:
                ERROR_COLLECTOR.add(f'{self.screened_title} has no minutes', f'Screened in {self.film}')
                COUNTER.increase('Not parsed screened films')
                minutes_str = "0"
            minutes = int(minutes_str.split()[0])
            screened_film.duration = datetime.timedelta(minutes=minutes)

            # Link the screened film to the combination program.
            screened_film_info.combination_films.append(self.film)
            combination_film_info = self.film.film_info(self.festival_data)
            screened_film = ScreenedFilm(
                screened_film.film_id,
                self.screened_title,
                screened_film_info.description,
                screened_film_type=ScreenedFilmType.PART_OF_COMBINATION_PROGRAM,
            )
            combination_film_info.screened_films.append(screened_film)
            if not combination_film_info.film_id:
                combination_film_info.film_id = self.film.film_id
                self.festival_data.filminfos.append(combination_film_info)

    def _add_qa_record_from_ticket_label(self):
        if self.debug_prefix == 'F' and 'Q&A' in self.screening_ticket_label:
            dom, month_str = self.screening_start_date.split('-')   # 27-okt
            month = self.nl_month_by_name[month_str]
            hour, minute = self.screening_start_time.split(':')     # 13:30
            start_dt = datetime.datetime(FESTIVAL_YEAR, month, int(dom), int(hour), int(minute))
            screen = self._get_imagine_screen()
            COUNTER.increase('q&a from ticket label')
            QaScreeningKey(self.film, start_dt, screen).add()

    def _add_qa_record_from_article(self, data):
        """Process data like 'vrijdag 31 oktober' into a Q&A screening record."""
        if TICKETS_AVAILABLE:
            return
        for _, dom, month in self.re_date.findall(data):
            start_date = datetime.date(year=FESTIVAL_YEAR, month=self.nl_month_by_name[month[:3]], day=int(dom))
            COUNTER.increase('q&a from article')
            # TODO for 2026 if still applicable: Get this working
            # (without screen as key and with data instead of datetime).
            QaScreeningKey(self.film, start_date).add()

    def _get_imagine_screen(self):
        screen_parse_name = self.screening_screen.strip()
        splitter = LocationSplitter.split_location
        return get_screen_from_parse_name(self.festival_data, screen_parse_name, splitter)

    def _add_film_info(self):
        screened_films = self.film.screened_films(self.festival_data)
        if self.description or screened_films:
            article = self.article or self.description
            if screened_films:
                film_info = self.film.film_info(self.festival_data)
                film_info.article = article
            else:
                film_info = FilmInfo(self.film.film_id, self.description, article,
                                     metadata=self.film_property_by_label)
                self.festival_data.filminfos.append(film_info)

    def _finish_film_info(self):
        self.set_article()
        self._add_film_info()


class LocationSplitter:
    num_screen_re = re.compile(r'^(?P<theater>.*?) (?P<number>\d+)$')

    @classmethod
    def split_location(cls, location):
        city_name = FESTIVAL_CITY
        theater_parse_name = location
        default_screen_abbreviation = 'zaal'
        num_match = cls.num_screen_re.match(location)
        if location.startswith('KINO'):
            city_name = 'Rotterdam'
        elif location.startswith('Louis Hartlooper Complex'):
            city_name = 'Utrecht'

        parts = location.split()
        screen_abbreviation = ''
        parts.extend(['', ''])
        match [parts[0], parts[1], parts[2]]:
            case ['Hal', 'West', number]:
                theater_parse_name = 'Hal West (VR)'
                screen_abbreviation = number
            case ['Lab-1', number, _]:
                theater_parse_name = 'LAB111'
                screen_abbreviation = number
            case ['OT', '301', _]:
                theater_parse_name = 'OT 301'
            case _:
                if location == 'SPUI 25':
                    theater_parse_name = location
                    screen_abbreviation = default_screen_abbreviation
                elif location == 'OBA Oosterdok OBA Theater':
                    location_words = location.split()
                    theater_parse_name = ' '.join(location_words[:2])
                    screen_abbreviation = ' '.join(location_words[2:])
                elif num_match:
                    theater_parse_name = num_match.group(1)
                    screen_abbreviation = num_match.group(2)
                elif location.startswith('LAB111 '):
                    theater_parse_name = 'LAB111'
                    screen_abbreviation = location.split()[1]
                else:
                    screen_abbreviation = default_screen_abbreviation
        return city_name, theater_parse_name, screen_abbreviation or default_screen_abbreviation


class QaScreeningKey:
    q_and_a_screening_keys = []
    manual_keys = set()

    def __init__(self, film, start_dt, screen=None):
        self.film = film
        self.start_dt = start_dt
        self.screen = screen

    def __str__(self):
        screen_part = f' - {self.screen.abbr}' if self.screen else ''
        return f'film id: {self.film.film_id} - {self.start_dt.isoformat(sep=" ")}{screen_part}'

    def add(self):
        self.q_and_a_screening_keys.append(self)

    @classmethod
    def update_q_and_a_screenings(cls, festival_data):
        auto_keys = {(k.film.film_id, k.start_dt, k.screen.screen_id) for k in cls.q_and_a_screening_keys}
        rhs_list = auto_keys | cls.manual_keys
        for screening in festival_data.screenings:
            lhs = (screening.film.film_id, screening.start_datetime, screening.screen.screen_id)
            for rhs in rhs_list:
                if rhs == lhs:
                    screening.q_and_a = 'Q&A'
                    COUNTER.increase('q&a screenings')
                    break


class ImagineData(FestivalData):
    def __init__(self, plandata_dir, common_data_dir=None):
        super().__init__(FESTIVAL_CITY, plandata_dir, common_data_dir=common_data_dir)

    def film_key(self, film, url):
        return url

    def film_can_go_to_planner(self, film_id):
        film = self.get_film_by_id(film_id)
        return not film.subsection or film.subsection.name != 'Industry'


if __name__ == "__main__":
    main()
