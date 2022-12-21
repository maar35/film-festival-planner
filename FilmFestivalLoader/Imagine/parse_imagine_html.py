#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 18 20:56:44 2021

@author: maartenroos
"""

import datetime
import re
from enum import Enum, auto

from Shared.application_tools import ErrorCollector, DebugRecorder, comment
from Shared.parse_tools import FileKeeper, HtmlPageParser, try_parse_festival_sites
from Shared.planner_interface import FilmInfo, FestivalData, Film
from Shared.web_tools import UrlFile

# Parameters.
festival = 'Imagine'
year = 2022
city = 'Amsterdam'
ondemand_available_hours = None

# Files.
fileKeeper = FileKeeper(festival, year)
az_file = fileKeeper.az_file()
debug_file = fileKeeper.debug_file

# URL information.
imagine_hostname = 'https://www.imaginefilmfestival.nl'
az_url_path = f'/programma{year}'

# Application tools.
error_collector = ErrorCollector()
debug_recorder = DebugRecorder(debug_file)


def main():
    # Initialize a festival data object.
    comment('Creating festival data object.')
    festival_data = ImagineData(fileKeeper.plandata_dir)

    # Try parsing the websites.
    try_parse_festival_sites(parse_imagine_sites, festival_data, error_collector, debug_recorder)


def parse_imagine_sites(festival_data):
    comment('Parsing AZ pages and film pages.')
    get_films(festival_data)


def get_films(festival_data):
    az_url = imagine_hostname + az_url_path
    url_file = UrlFile(az_url, az_file, error_collector, byte_count=100)
    az_html = url_file.get_text()
    if az_html is not None:
        AzPageParser(festival_data).feed(az_html)


def get_details_of_all_films(festival_data):
    for film in festival_data.films:
        get_details_of_one_film(festival_data, film)


def get_details_of_one_film(festival_data, film):
    film_file = fileKeeper.film_webdata_file(film.filmid)
    url_file = UrlFile(film.url, film_file, error_collector, byte_count=30000)
    film_html = url_file.get_text(f'Downloading site of {film.title}: {film.url}')

    if film_html is not None:
        print(f"Analysing html file {film.filmid} of {film.title} {film.url}")
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
        HtmlPageParser.__init__(self, festival_data, debug_recorder, 'AZ')
        self.debugging = True
        self.film = None
        self.url = None
        self.title = None
        self.sort_title = None
        self.duration = None
        self.section = None
        self.screen_name = None
        self.screen = None
        self.start_dt = None
        self.end_dt = None
        self.medium_type = None
        self.audience = None
        self.subtitles = None
        self.stateStack = self.StateStack(self.print_debug, self.AzParseState.IDLE)
        self.init_categories()
        self.init_screening_data()

    @staticmethod
    def init_categories():
        Film.category_by_string['Extra'] = Film.category_films
        Film.category_by_string['Feature'] = Film.category_films
        Film.category_by_string['Shorts'] = Film.category_combinations
        Film.category_by_string['Special'] = Film.category_events
        Film.category_by_string['Workshop'] = Film.category_events

    def init_screening_data(self):
        self.film = None
        self.url = None
        self.title = None
        self.sort_title = None
        self.duration = None
        self.section = None
        self.screen_name = None
        self.screen = None
        self.start_dt = None
        self.end_dt = None
        self.medium_type = None
        self.audience = 'publiek'
        self.subtitles = ''

    @staticmethod
    def get_duration(data):
        minutes = data.strip().split()[0]  # 106 min.
        duration = datetime.timedelta(minutes=int(minutes))
        return duration

    def get_screen(self, data):
        screen_name = data.strip()
        screen = self.festival_data.get_screen(city, screen_name)
        return screen

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
            error_collector.add(f'Could not create film:', '{self.title} ({self.url})')
        else:
            # Fill details.
            if self.section is None:
                self.section = 'Imagine General'
            self.film.subsection = self.festival_data.subsection_by_name[self.section]
            if self.section == 'Industry':
                self.audience = 'industry'
            self.film.medium_category = self.medium_type
            self.film.sortstring = self.sort_title
            self.film.duration = self.duration

            # Add the film to the list.
            self.festival_data.films.append(self.film)

            # Get the film info.
            get_details_of_one_film(self.festival_data, self.film)

    def add_imagine_screening(self):
        # Get the film.
        try:
            self.film = self.festival_data.get_film_by_key(self.title, self.url)
        except KeyError:
            self.add_film()
        except ValueError:
            self.add_film()

        # Calculate the screening's end time.
        duration = self.film.duration
        self.end_dt = self.start_dt + duration

        # Add screening to the list.
        HtmlPageParser.add_screening(self, self.film, self.screen, self.start_dt, self.end_dt,
                                     audience=self.audience, subtitles=self.subtitles, display=True)

        # Initialize the next round of parsing.
        self.init_screening_data()

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.AzParseState.IDLE) and tag == 'ul' and len(attrs) > 0:
            if attrs[0][1] == 'screenings imagine-rows filterable':
                self.stateStack.change(self.AzParseState.IN_LIST)
        elif self.stateStack.state_is(self.AzParseState.IN_LIST) and tag == 'li' and len(attrs) > 3:
            if attrs[0][1] == 'screening item':
                self.url = attrs[1][1]
                self.sort_title = attrs[3][1]
                self.stateStack.push(self.AzParseState.IN_SCREENING)
        elif self.stateStack.state_is(self.AzParseState.IN_SCREENING) and tag == 'time' and len(attrs) > 0:
            if attrs[0][0] == 'datetime':
                self.start_dt = datetime.datetime.fromisoformat(attrs[0][1])
        elif self.stateStack.state_is(self.AzParseState.IN_SCREENING) and tag == 'section':
            self.stateStack.push(self.AzParseState.IN_SECTION)
        elif self.stateStack.state_is(self.AzParseState.IN_SCREENING) and tag == 'div' and len(attrs) > 0:
            if attrs[0][1] == 'type':
                self.stateStack.push(self.AzParseState.IN_TYPE)
        elif self.stateStack.state_is(self.AzParseState.IN_SCREENING) and tag == 'h2':
            self.stateStack.push(self.AzParseState.IN_TITLE)
        elif self.stateStack.state_is(self.AzParseState.IN_SCREENING) and tag == 'i' and len(attrs) > 0:
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
            self.section = data
            self.stateStack.pop()
        if self.stateStack.state_is(self.AzParseState.IN_TYPE):
            self.medium_type = data
            self.stateStack.pop()
        elif self.stateStack.state_is(self.AzParseState.IN_TITLE):
            self.title = data
            self.stateStack.pop()
        elif self.stateStack.state_is(self.AzParseState.IN_SCREEN):
            self.screen = self.get_screen(data)
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
        AWAITING_DESCRIPTION = auto()
        IN_DESCRIPTION = auto()
        IN_ARTICLE = auto()
        AWAITING_ALT_DESCRIPTION = auto()
        IN_ALT_DESCRIPTION = auto()
        AWAITING_ALT_ARTICLE = auto()
        IN_ALT_ARTICLE = auto()
        AWAITING_METADATA = auto()
        IN_METADATA = auto()
        IN_METADATA_KEY = auto()
        IN_METADATA_VALUE = auto()
        DONE = auto()

    def __init__(self, festival_data, film):
        HtmlPageParser.__init__(self, festival_data, debug_recorder, "F")
        self.debugging = False
        self.film = film
        self.description = None
        self.alt_description = None
        self.alt_description_parts = []
        self.film_property_by_label = {}
        self.metadata_key = None
        self.screened_films = []
        self.combination_urls = []
        self.stateStack = self.StateStack(self.print_debug, self.FilmInfoParseState.IDLE)
        self.print_debug(f"{40 * '-'} ", f"Analysing FILM {film}, {film.url}")

    def set_alt_description(self):
        parts_count = len(self.alt_description_parts)
        if parts_count > 1:
            pluralizer = 's' if parts_count > 2 else ''
            header = f'Program with {parts_count - 1} part{pluralizer}, total {self.alt_description_parts[0]}'
            parts = '\n'.join(self.alt_description_parts[1:])
            self.alt_description = f'{header}\n{parts}'
        elif parts_count == 1:
            self.alt_description = self.alt_description_parts[0]
        else:
            self.alt_description = None

    def add_paragraph(self):
        paragraph = self.article_paragraph
        if len(paragraph) > 0:
            self.article_paragraphs.append(paragraph.strip())
        self.article_paragraph = ''

    def set_article(self):
        descr_threshold = 512
        article = '\n\n'.join(self.article_paragraphs)
        if self.alt_description is None:
            self.article = article
        elif len(self.article_paragraphs) > 0:
            self.description = self.article_paragraphs[0]
            if len(self.description) > descr_threshold:
                self.description = self.description[:descr_threshold] + '…'
            self.article = f'{self.alt_description}\n\n{article}'
        else:
            self.description = self.film.title
            self.article = ''
        if len(self.film_property_by_label):
            properties = [f'{key}: {value}' for (key, value) in self.film_property_by_label.items()]
            metadata = '\n'.join(properties)
            self.article += f'\n\n{metadata}'

    def add_film_info(self):
        if len(self.description) == 0:
            self.description = self.film.title
        film_info = FilmInfo(self.film.filmid, self.description, self.article)
        self.festival_data.filminfos.append(film_info)

    def finish_film_info(self):
        self.set_article()
        self.add_film_info()

    def in_article(self):
        return self.stateStack.state_in([self.FilmInfoParseState.IN_ARTICLE,
                                         self.FilmInfoParseState.IN_ALT_ARTICLE])

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.FilmInfoParseState.IDLE) and tag == 'div' and len(attrs) > 0:
            if attrs[0] == ('class', 'container-wrap'):
                self.stateStack.push(self.FilmInfoParseState.AWAITING_DESCRIPTION)
        if self.stateStack.state_is(self.FilmInfoParseState.AWAITING_DESCRIPTION) and tag == 'div':
            if len(attrs) > 0:
                if attrs[0] == ('class', 'text'):
                    self.stateStack.change(self.FilmInfoParseState.IN_DESCRIPTION)
                elif attrs[0] == ('class', 'w3'):
                    self.stateStack.change(self.FilmInfoParseState.AWAITING_ALT_DESCRIPTION)
        elif self.stateStack.state_is(self.FilmInfoParseState.AWAITING_ALT_DESCRIPTION) and tag == 'div':
            if len(attrs) > 0 and attrs[0] == ('class', 'meta'):
                self.stateStack.change(self.FilmInfoParseState.IN_ALT_DESCRIPTION)
        elif self.stateStack.state_is(self.FilmInfoParseState.AWAITING_ALT_ARTICLE) and tag == 'div':
            if len(attrs) > 0 and attrs[0] == ('class', 'w6'):
                self.stateStack.change(self.FilmInfoParseState.IN_ALT_ARTICLE)
        elif self.stateStack.state_is(self.FilmInfoParseState.AWAITING_METADATA) and tag == 'div':
            if len(attrs) > 0 and attrs[0] == ('class', 'meta'):
                self.stateStack.change(self.FilmInfoParseState.IN_METADATA)
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_METADATA) and tag == 'div':
            self.stateStack.push(self.FilmInfoParseState.IN_METADATA_KEY)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.stateStack.state_is(self.FilmInfoParseState.IN_ALT_DESCRIPTION) and tag == 'div':
            self.set_alt_description()
            self.stateStack.change(self.FilmInfoParseState.AWAITING_ALT_ARTICLE)
        elif self.in_article() and tag == 'p':
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

        if self.stateStack.state_is(self.FilmInfoParseState.IN_DESCRIPTION):
            if len(data.strip()) > 0:
                self.description = data
                self.stateStack.change(self.FilmInfoParseState.IN_ARTICLE)
        elif self.in_article():
            self.article_paragraph += data
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_ALT_DESCRIPTION):
            part = data.strip()
            if len(part):
                self.alt_description_parts.append(part)
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_METADATA_KEY):
            self.metadata_key = data.strip()
            self.stateStack.change(self.FilmInfoParseState.IN_METADATA_VALUE)
        elif self.stateStack.state_is(self.FilmInfoParseState.IN_METADATA_VALUE):
            self.film_property_by_label[self.metadata_key] = data.strip()


class ImagineData(FestivalData):

    def _init__(self, plandata_dir):
        FestivalData.__init__(self, plandata_dir)

    def film_key(self, film, url):
        return url

    def film_can_go_to_planner(self, film_id):
        film = self.get_film_by_id(film_id)
        return film.subsection.name != 'Industry'


if __name__ == "__main__":
    main()
