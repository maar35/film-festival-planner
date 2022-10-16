#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 18 20:56:44 2021

@author: maartenroos
"""

import datetime
import os
import re
from enum import Enum, auto

import Shared.web_tools as web_tools
from Shared.application_tools import ErrorCollector, DebugRecorder, comment
from Shared.parse_tools import FileKeeper, HtmlPageParser, add_screening
from Shared.planner_interface import write_lists, FilmInfo, Screening, FestivalData, Film

# Parameters.
festival = 'Imagine'
year = 2022
city = 'Amsterdam'
ondemand_available_hours = None

# Files.
fileKeeper = FileKeeper(festival, year)
az_file = fileKeeper.az_file
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
    write_film_list = False
    write_other_lists = True
    try:
        parse_imagine_sites(festival_data)
    except KeyboardInterrupt:
        comment('Interrupted from keyboard... exiting')
        write_other_lists = False
    except Exception as e:
        debug_recorder.write_debug()
        comment('Debug info printed.')
        raise e
    else:
        write_film_list = True

    # Display errors when found.
    if error_collector.error_count() > 0:
        comment('Encountered some errors:')
        print(error_collector)

    # Write parsed information.
    comment('Done loading Imagine data.')
    write_lists(festival_data, write_film_list, write_other_lists)
    debug_recorder.write_debug()


def parse_imagine_sites(festival_data):
    comment('Parsing AZ pages.')
    get_films(festival_data)

    # comment('Parsing film pages.')
    # get_film_details(festival_data)


def get_films(festival_data):
    az_url = imagine_hostname + az_url_path
    url_file = web_tools.UrlFile(az_url, az_file, error_collector, byte_count=3)
    az_html = url_file.get_text()
    if az_html is not None:
        AzPageParser(festival_data).feed(az_html)


def get_film_details(festival_data):
    for film in festival_data.films:
        film_file = fileKeeper.filmdata_file(film.filmid)
        if os.path.isfile(film_file):
            charset = web_tools.get_charset(film_file)
            with open(film_file, 'r', encoding=charset) as f:
                html_data = f.read()
        else:
            print(f"Downloading site of {film.title}: {film.url}")
            html_data = web_tools.UrlReader(error_collector).load_url(film.url, film_file)
        if html_data is not None:
            print(f"Analysing html file {film.filmid} of {film.title} {film.url}")
            FilmPageParser(festival_data, film).feed(html_data)


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
        re_parentheses = re.compile(r'^(?P<language>.*)\((?P<subs>.*)\).*')   # Spaans (Engels ondertiteld)
        matches = re_parentheses.match(data)
        subtitles = matches.group('subs') if matches else ''
        return subtitles

    def add_film(self):
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            error_collector.add(f'Could not create film:', '{self.title} ({self.url})')
        else:
            if self.section is None:
                self.section = 'Imagine General'
            self.film.subsection = self.festival_data.subsection_by_name[self.section]
            if self.section == 'Industry':
                self.audience = 'industry'
            self.film.medium_category = self.medium_type
            self.film.sortstring = self.sort_title
            self.film.duration = self.duration
            self.festival_data.films.append(self.film)

    def add_screening(self):
        # Get the film.
        try:
            self.film = self.festival_data.get_film_by_key(self.title, self.url)
        except KeyError:
            self.add_film()
        if self.film is None:
            self.add_film()

        # Calculate the screening's end time.
        duration = self.film.duration
        self.end_dt = self.start_dt + duration

        # Add screening to the list.
        add_screening(self.festival_data, self.film, self.screen, self.start_dt, self.end_dt,
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
            self.add_screening()
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
    class ScreeningsParseState(Enum):
        IDLE = auto()
        IN_META_DATA = auto()
        IN_DURATION = auto()
        IN_NAMED_META = auto()
        IN_META_KEY = auto()
        AWAITING_ARTICLE = auto()
        IN_ARTICLE = auto()
        SKIP_DESCRIPTION = auto()
        IN_SCREENINGS = auto()
        IN_DATE = auto()
        IN_TIME = auto()
        IN_LOCATION = auto()
        IN_EXTRA = auto()
        DONE = auto()

    nl_month_by_name = {'mar': 3, 'apr': 4, 'okt': 10}

    def __init__(self, festival_data, film):
        HtmlPageParser.__init__(self, festival_data, debug_recorder, "F")
        self.start_dt = None
        self.start_date = None
        self.subtitles = None
        self.end_dt = None
        self.film = film
        self.filminfo = self.get_filminfo(self.film.filmid)
        self.debugging = False
        self.article = None
        self.combination_urls = []
        self.print_debug(f"{40 * '-'} ", f"Analysing FILM {film}, {film.url}")
        self.screened_films = []
        self.metadata = None
        self.init_screening_data()
        self.stateStack = self.StateStack(self.print_debug, self.ScreeningsParseState.IDLE)

    def init_screening_data(self):
        self.audience = 'publiek'
        self.qa = ''
        self.subtitles = ''
        self.extra = ''
        self.screen = None
        self.start_dt = None
        self.end_dt = None
        self.start_date = None
        self.times = None

    def get_filminfo(self, filmid):
        filminfos = [filminfo for filminfo in self.festival_data.filminfos if filminfo.filmid == self.film.filmid]
        if len(filminfos) == 1:
            return filminfos[0]
        error_collector.add(f'No unique FILMINFO found for {self.film}', f'{len(filminfos)} linked filminfo records')
        return None

    def update_filminfo(self):
        if self.filminfo is not None:
            self.article = re.sub('\n\n+', '\n', self.metadata).rstrip() + '\n\n' + self.article.lstrip()
            if self.article is not None and len(self.article) > 0:
                self.filminfo.article = self.article
            elif self.article is None:
                error_collector.add('Article is None', f'{self.film} {self.film.duration_str()}')
                self.filminfo.article = ''
            else:
                error_collector.add('Article is empty string', f'{self.film} {self.film.duration_str()}')
                self.filminfo.article = ''
            self.filminfo.combination_urls = self.combination_urls
            self.filminfo.screened_films = self.screened_films
            self.print_debug(f'FILMINFO of {self.film.title} updated', f'ARTICLE: {self.filminfo.article}')
        else:
            filminfo = FilmInfo(self.film.filmid, '', self.article, self.screened_films)
            self.festival_data.filminfos.append(filminfo)

    def set_screen(self, location):
        self.screen = self.festival_data.get_screen(city, location)

    def set_screening_info(self, data):
        self.print_debug('Found SCREENING info', data)
        parts = data.split(self.film.title)
        if len(parts) > 1:
            searchtext = parts[1]
        else:
            searchtext = data
        if 'Q&A' in searchtext:
            self.qa = 'Q&A'
        if '+' in searchtext:
            self.extra = searchtext.split('+')[1].strip()
        if searchtext.endswith('(besloten)'):
            self.audience = 'besloten'

    def add_screening(self):
        # Calculate the screening's end time.
        duration = self.film.duration
        self.end_dt = self.start_dt + duration

        # Print the screening propoerties.
        if self.audience == 'publiek':
            print()
            print(f"---SCREENING OF {self.film.title}")
            print(f"--  screen:     {self.screen}")
            print(f"--  start time: {self.start_dt}")
            print(f"--  end time:   {self.end_dt}")
            print(f"--  duration:   film: {self.film.duration_str()}  screening: {self.end_dt - self.start_dt}")
            print(f"--  audience:   {self.audience}")
            print(f"--  category:   {self.film.medium_category}")
            print(f"--  q and a:    {self.qa}")

        # Create a new screening object.
        program = None
        screening = Screening(self.film, self.screen, self.start_dt, self.end_dt,
                              self.qa, self.extra, self.audience, program, self.subtitles)

        # Add the screening to the list.
        self.festival_data.screenings.append(screening)
        print("---SCREENING ADDED")

        # Initialize the next round of parsing.
        self.init_screening_data()

    def parse_imagine_category(self, data):
        items = data.split(',')  # Feature, 88min
        return items[0].strip()

    def parse_duration(self, data):
        items = data.split(',')  # Feature, 88min
        return datetime.timedelta(minutes=int(items[1].strip().rstrip('min')))

    def parse_date(self, data):
        items = data.split()  # 10 apr
        day = int(items[0])
        month = self.nl_month_by_name[items[1]]
        return datetime.date(year, month, day)

    def parse_time(self, data):
        items = data.split()  # 17:00 (online)
        return datetime.time.fromisoformat(items[0])

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        # Get data for film info.
        if tag == 'div' and len(attrs) > 0 and attrs[0] == ('class', 'meta'):
            self.stateStack.push(self.ScreeningsParseState.IN_META_DATA)
            self.metadata = ''
            self.stateStack.push(self.ScreeningsParseState.IN_DURATION)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_META_DATA) and tag == 'strong':
            self.stateStack.change(self.ScreeningsParseState.IN_NAMED_META)
            self.stateStack.push(self.ScreeningsParseState.IN_META_KEY)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_NAMED_META) and tag == 'strong':
            self.stateStack.push(self.ScreeningsParseState.IN_META_KEY)
        elif tag == 'div' and len(attrs) > 0 and attrs[0] == ('class', 'w6'):
            self.stateStack.push(self.ScreeningsParseState.AWAITING_ARTICLE)
        elif self.stateStack.state_is(self.ScreeningsParseState.AWAITING_ARTICLE) and tag == 'p':
            self.stateStack.change(self.ScreeningsParseState.IN_ARTICLE)
            self.article = ''
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_ARTICLE) and tag == 'strong':
            self.stateStack.push(self.ScreeningsParseState.SKIP_DESCRIPTION)

        # Get data for screenings.
        if tag == 'ul' and len(attrs) > 0 and attrs[0] == ('class', 'shows'):
            self.stateStack.push(self.ScreeningsParseState.IN_SCREENINGS)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'div' and attrs[0] == (
        'class', 'date'):
            self.stateStack.push(self.ScreeningsParseState.IN_DATE)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'div' and attrs[0] == (
        'class', 'time'):
            self.stateStack.push(self.ScreeningsParseState.IN_TIME)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'div' and attrs[0] == (
        'class', 'theatre'):
            self.stateStack.push(self.ScreeningsParseState.IN_LOCATION)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'div' and attrs[0] == (
        'class', 'extra'):
            self.stateStack.push(self.ScreeningsParseState.IN_EXTRA)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        # Get data for film info.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_META_DATA) and tag == 'div':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_NAMED_META) and tag == 'div':
            self.stateStack.pop()
            self.metadata += '\n'
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_META_KEY) and tag == 'strong':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_ARTICLE) and tag == 'div':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.ScreeningsParseState.SKIP_DESCRIPTION) and tag == 'strong':
            self.stateStack.pop()

        # Get data for screenings.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'ul':
            self.stateStack.pop()
            self.update_filminfo()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        # Get data for film info.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_DURATION):
            self.stateStack.pop()
            self.metadata += data.strip()
            self.film.duration = self.parse_duration(data)
            self.filminfo.description = self.parse_imagine_category(data) + ' - ' + self.filminfo.description
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_META_DATA):
            self.metadata += '\n' + data.strip()
            if 'ondertiteld' in data:
                self.subtitles = data.strip()
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_NAMED_META):
            self.metadata += data
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_META_KEY):
            self.metadata += '\n' + data
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_ARTICLE):
            self.article += data

        # Get data for screenings.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_DATE):
            self.stateStack.pop()
            self.start_date = self.parse_date(data)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_TIME):
            self.stateStack.pop()
            self.start_dt = datetime.datetime.combine(self.start_date, self.parse_time(data))
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_LOCATION):
            self.stateStack.pop()
            self.set_screen(data)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_EXTRA):
            self.stateStack.pop()
            self.set_screening_info(data)
            self.add_screening()


class ImagineData(FestivalData):

    def _init__(self, plandata_dir):
        FestivalData.__init__(self, plandata_dir)

    def _filmkey(self, film, url):
        return url

    def film_can_go_to_planner(self, film_id):
        film = self.get_film_by_id(film_id)
        return film.subsection.name != 'Industry'


if __name__ == "__main__":
    main()
