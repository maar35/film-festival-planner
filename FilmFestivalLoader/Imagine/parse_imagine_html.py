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
from Shared.planner_interface import FilmInfo, FestivalData, Film, get_screen_from_parse_name
from Shared.web_tools import UrlFile

DOWNLOAD_WORKS = True       # Python html reader gets "certificate not found", used curl instead.
FILE_BY_URL = {}
ALWAYS_DOWNLOAD = False

FESTIVAL = 'Imagine'
FESTIVAL_YEAR = 2024
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
    COUNTER.start('q&a screenings')

    # Try parsing the websites.
    try_parse_festival_sites(parse_imagine_sites, festival_data, ERROR_COLLECTOR, DEBUG_RECORDER, counter=COUNTER)

    # Write a map file for curl if downloading doesn't work.
    write_url_map_file()


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
    comment_at_download = f'Downloading AZ page from {az_url}.'
    az_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD)
    if az_html is not None:
        comment(f'Downloaded AZ page, encoding={url_file.encoding}')
        AzPageParser(festival_data).feed(az_html)


def get_details_of_one_film(festival_data, film):
    film_file = FILE_KEEPER.film_webdata_file(film.film_id)
    if not DOWNLOAD_WORKS:
        FILE_BY_URL[film.url] = film_file
        return
    url_file = UrlFile(film.url, film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=256)
    comment_at_download = f'Downloading site of {film.title}: {film.url}'
    film_html = url_file.get_text(comment_at_download=comment_at_download, always_download=ALWAYS_DOWNLOAD)

    if film_html is not None:
        print(f"Analysing html file {film.film_id} of {film.title} {film.url}")
        FilmPageParser(festival_data, film).feed(film_html)


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
        self.sorting_from_site = False
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
        self.stateStack = self.StateStack(self.print_debug, self.AzParseState.IDLE)
        self.init_categories()
        self.init_screening_data()

    @staticmethod
    def init_categories():
        Film.category_by_string['Extra'] = Film.category_films
        Film.category_by_string['feature'] = Film.category_films
        Film.category_by_string['shorts'] = Film.category_combinations
        Film.category_by_string['special'] = Film.category_events
        Film.category_by_string['Talk'] = Film.category_events
        Film.category_by_string['Workshop'] = Film.category_events
        Film.category_by_string['vr/expanded'] = Film.category_events

    def init_screening_data(self):
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
        self.audience = 'publiek'
        self.qa = ''
        self.subtitles = ''

    @staticmethod
    def get_duration(data):
        minutes = data.strip().split()[0]  # 106 min.
        duration = datetime.timedelta(minutes=int(minutes))
        return duration

    def get_imagine_screen(self, data):
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

    def add_film(self):
        # Create a new film.
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            ERROR_COLLECTOR.add(f'Could not create film:', '{self.title} ({self.url})')
        else:
            # Fill details.
            self.film.duration = self.duration
            self.film.subsection = self.get_subsection()
            self.film.medium_category = self.medium_type
            if self.sorting_from_site:
                self.film.sortstring = self.sort_title

            # Add the film to the list.
            self.festival_data.films.append(self.film)

            # Get the film info.
            get_details_of_one_film(self.festival_data, self.film)

    def get_subsection(self):
        if self.section_name:
            section = self.festival_data.get_section(self.section_name, self.section_color)
            dummy_url = 'https://www.imaginefilmfestival.nl/en/blockschedule'
            subsection = self.festival_data.get_subsection(section.name, dummy_url, section)
            return subsection
        return None

    def add_imagine_screening(self):
        # Get the film.
        try:
            self.film = self.festival_data.get_film_by_key(self.title, self.url)
        except (KeyError, ValueError):
            self.add_film()

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
            qa=self.qa, audience=self.audience, subtitles=self.subtitles, display=True)

        # Initialize the next round of parsing.
        self.init_screening_data()

    def feed(self, data):
        super().feed(data)
        comment('Assigning Q&A property to the relevant screenings.')
        QaScreeningKey.update_q_and_a_screenings(self.festival_data)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.AzParseState.IDLE) and tag == 'ul' and attrs:
            if attrs[0][1] == 'screenings imagine-rows filterable':
                self.stateStack.change(self.AzParseState.IN_LIST)
        elif self.stateStack.state_is(self.AzParseState.IN_LIST) and tag == 'li' and len(attrs) > 3:
            if attrs[0][1] == 'screening item':
                self.url = attrs[2][1]
                self.sort_title = attrs[3][1]
                self.stateStack.push(self.AzParseState.IN_SCREENING)
        elif self.stateStack.state_is(self.AzParseState.IN_SCREENING) and tag == 'time' and attrs:
            if attrs[0][0] == 'datetime':
                self.start_dt = datetime.datetime.fromisoformat(attrs[0][1])
        elif self.stateStack.state_is(self.AzParseState.IN_SCREENING) and tag == 'section':
            self.stateStack.push(self.AzParseState.IN_SECTION)
        elif self.stateStack.state_is(self.AzParseState.IN_SECTION) and tag == 'div' and attrs:
            if attrs[0][1].startswith('background-color'):
                self.section_color = attrs[0][1].split(':')[1]
        elif self.stateStack.state_is(self.AzParseState.IN_SCREENING) and tag == 'div' and attrs:
            if attrs[0][1] == 'type':
                self.stateStack.push(self.AzParseState.IN_TYPE)
        elif self.stateStack.state_is(self.AzParseState.IN_SCREENING) and tag == 'h2':
            self.stateStack.push(self.AzParseState.IN_TITLE)
        elif self.stateStack.state_is(self.AzParseState.IN_SCREENING) and tag == 'i' and attrs:
            if attrs[0][1] == 'fa fa-map-marker':
                self.stateStack.push(self.AzParseState.IN_SCREEN)
            elif attrs[0][1] == 'fa fa-clock-o':
                self.stateStack.push(self.AzParseState.IN_DURATION)
            elif attrs[0][1] == 'fa fa-commenting':
                self.stateStack.push(self.AzParseState.IN_LANGUAGE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.stateStack.state_is(self.AzParseState.IN_SCREENING) and tag == 'li':
            self.add_imagine_screening()
            self.stateStack.pop()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.stateStack.state_is(self.AzParseState.IN_SECTION):
            if data.strip():
                self.section_name = data
                self.stateStack.pop()
        if self.stateStack.state_is(self.AzParseState.IN_TYPE):
            self.medium_type = data
            self.stateStack.pop()
        elif self.stateStack.state_is(self.AzParseState.IN_TITLE):
            self.title = self.get_title(data)
            self.stateStack.pop()
        elif self.stateStack.state_is(self.AzParseState.IN_SCREEN):
            self.screen = self.get_imagine_screen(data)
            self.stateStack.pop()
        elif self.stateStack.state_is(self.AzParseState.IN_DURATION):
            self.duration = self.get_duration(data)
            self.stateStack.pop()
        elif self.stateStack.state_is(self.AzParseState.IN_LANGUAGE):
            self.subtitles = self.get_subtitles(data)
            self.stateStack.pop()


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
        DONE = auto()

    nl_month_by_name = {'okt': 10, 'nov': 11}

    def __init__(self, festival_data, film):
        HtmlPageParser.__init__(self, festival_data, DEBUG_RECORDER, "F", debugging=True)
        self.film = film
        self.screening_start_date = None
        self.screening_start_time = None
        self.screening_screen = None
        self.screening_ticket_label = None
        self.description = None
        self.film_property_by_label = {}
        self.metadata_key = None
        self.screened_films = []
        self.combination_urls = []
        self.stateStack = self.StateStack(self.print_debug, self.FilmInfoParseState.IDLE)
        self.print_debug(f"{40 * '-'} ", f"Analysing FILM {film}, {film.url}")

    def add_q_and_a_record(self):
        if 'Q&A' in self.screening_ticket_label:
            dom, month_str = self.screening_start_date.split('-')   # 27-okt
            month = self.nl_month_by_name[month_str]
            hour, minute = self.screening_start_time.split(':')     # 13:30
            start_dt = datetime.datetime(FESTIVAL_YEAR, month, int(dom), int(hour), int(minute))
            screen = self.get_imagine_screen()
            QaScreeningKey(self.film, start_dt, screen).add()

    def get_imagine_screen(self):
        screen_parse_name = self.screening_screen.strip()
        splitter = LocationSplitter.split_location
        return get_screen_from_parse_name(self.festival_data, screen_parse_name, splitter)

    def add_paragraph(self):
        paragraph = self.article_paragraph
        if len(paragraph) > 0:
            self.article_paragraphs.append(paragraph.strip())
        self.article_paragraph = ''

    def set_article(self):
        descr_threshold = 512
        if self.article_paragraphs:
            self.description = self.description or self.article_paragraphs[0]
            if len(self.description) > descr_threshold:
                self.description = self.description[:descr_threshold] + '…'
            self.article = '\n\n'.join(self.article_paragraphs)
        else:
            self.description = ''
            self.article = ''
        if len(self.film_property_by_label):
            properties = [f'{key}: {value}' for (key, value) in self.film_property_by_label.items()]
            metadata = '\n'.join(properties)
            self.article += f'\n\n{metadata}'

    def add_film_info(self):
        if self.description:
            article = self.article or self.description
            film_info = FilmInfo(self.film.film_id, self.description, article,
                                 metadata=self.film_property_by_label)
            self.festival_data.filminfos.append(film_info)

    def finish_film_info(self):
        self.set_article()
        self.add_film_info()

    def in_any_article(self):
        return self.stateStack.state_in([self.FilmInfoParseState.IN_ARTICLE,
                                         self.FilmInfoParseState.IN_ALT_ARTICLE])

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.FilmInfoParseState.IDLE) and tag == 'h2':
            self.stateStack.push(self.FilmInfoParseState.AWAITING_SCREENINGS)
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_SCREENINGS) and tag == 'tr':
            self.screening_start_date = attrs[1][1]
            self.stateStack.push(self.FilmInfoParseState.IN_SCREENING)
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_SCREENING) and tag == 'td' and attrs:
            match attrs[0][1]:
                case 'time':
                    self.stateStack.push(self.FilmInfoParseState.IN_TIME)
                case 'theatre':
                    self.stateStack.push(self.FilmInfoParseState.IN_SCREEN)
                case 'ticket':
                    self.stateStack.push(self.FilmInfoParseState.AWAITING_TICKET_LINK)
        elif self.stateStack.state_is(self.FilmInfoParseState.AWAITING_TICKET_LINK) and tag == 'a':
            self.stateStack.change(self.FilmInfoParseState.IN_TICKETS_LINK)
        elif self.stateStack.state_is(self.FilmInfoParseState.IDLE) and tag == 'div' and attrs:
            if attrs[0] == ('class', 'container-wrap'):
                self.stateStack.push(self.FilmInfoParseState.AWAITING_DESCRIPTION)
        if self.stateStack.state_is(self.FilmInfoParseState.AWAITING_DESCRIPTION) and tag == 'div':
            if attrs:
                if attrs[0] == ('class', 'text'):
                    self.stateStack.change(self.FilmInfoParseState.IN_DESCRIPTION)
                elif attrs[0] == ('class', 'w6'):
                    self.stateStack.change(self.FilmInfoParseState.IN_ALT_ARTICLE)
        elif self.stateStack.state_is(self.FilmInfoParseState.AWAITING_METADATA) and tag == 'div':
            if attrs and attrs[0] == ('class', 'meta'):
                self.stateStack.change(self.FilmInfoParseState.IN_METADATA)
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_METADATA) and tag == 'div':
            self.stateStack.push(self.FilmInfoParseState.IN_METADATA_KEY)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.stateStack.state_is(self.FilmInfoParseState.AWAITING_SCREENINGS) and tag == 'h2':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_SCREENING) and tag == 'tr':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_SCREENINGS) and tag == 'table':
            self.stateStack.pop()
        elif self.in_any_article() and tag == 'p':
            self.add_paragraph()
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_ARTICLE) and tag == 'div':
            self.stateStack.change(self.FilmInfoParseState.AWAITING_METADATA)
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_ALT_ARTICLE) and tag == 'div':
            self.finish_film_info()
            self.stateStack.pop()
            self.stateStack.change(self.FilmInfoParseState.DONE)
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_METADATA_VALUE) and tag == 'div':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_METADATA) and tag == 'div':
            self.finish_film_info()
            self.stateStack.pop()
            self.stateStack.change(self.FilmInfoParseState.DONE)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.stateStack.state_is(self.FilmInfoParseState.AWAITING_SCREENINGS):
            if data == 'Screenings & Tickets':
                self.stateStack.change(self.FilmInfoParseState.IN_SCREENINGS)
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_TIME):
            self.screening_start_time = data
            self.stateStack.pop()
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_SCREEN):
            self.screening_screen = data
            self.stateStack.pop()
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_TICKETS_LINK):
            self.screening_ticket_label = data
            self.add_q_and_a_record()
            self.stateStack.pop()
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_DESCRIPTION):
            if len(data.strip()) > 0:
                self.description = data
                self.stateStack.change(self.FilmInfoParseState.IN_ARTICLE)
        elif self.in_any_article():
            self.article_paragraph += data
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_METADATA_KEY):
            self.metadata_key = data.strip()
            self.stateStack.change(self.FilmInfoParseState.IN_METADATA_VALUE)
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_METADATA_VALUE):
            self.film_property_by_label[self.metadata_key] = data.strip()


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
        return city_name, theater_parse_name, screen_abbreviation


class QaScreeningKey:
    q_and_a_screening_keys = []
    manual_keys = {
        (21, 118, datetime.datetime.fromisoformat('2024-10-25 16:40:00')),
        (44, 51, datetime.datetime.fromisoformat('2024-10-26 21:40:00')),
        (50, 118, datetime.datetime.fromisoformat('2024-10-27 13:45:00')),
        (56, 52, datetime.datetime.fromisoformat('2024-10-27 16:30:00')),
        (59, 51, datetime.datetime.fromisoformat('2024-11-01 18:30:00')),
    }

    def __init__(self, film, start_dt, screen):
        self.film = film
        self.start_dt = start_dt
        self.screen = screen

    def __str__(self):
        return (f'film id: {self.film.film_id} - {self.start_dt.isoformat(sep=" ")} '
                f'- screen id: {self.screen.screen_id}')

    def add(self):
        self.q_and_a_screening_keys.append(self)

    @classmethod
    def update_q_and_a_screenings(cls, festival_data):
        auto_keys = {(k.film.film_id, k.screen.screen_id, k.start_dt) for k in cls.q_and_a_screening_keys}
        rhs_list = auto_keys | cls.manual_keys
        for screening in festival_data.screenings:
            lhs = (screening.film.film_id, screening.screen.screen_id, screening.start_datetime)
            for rhs in rhs_list:
                if rhs == lhs:
                    screening.q_and_a = 'Q&A'
                    COUNTER.increase('q&a screenings')


class ImagineData(FestivalData):
    def __init__(self, plandata_dir):
        super().__init__(FESTIVAL_CITY, plandata_dir)

    def film_key(self, film, url):
        return url

    def film_can_go_to_planner(self, film_id):
        film = self.get_film_by_id(film_id)
        return not film.subsection or film.subsection.name != 'Industry'


if __name__ == "__main__":
    main()
