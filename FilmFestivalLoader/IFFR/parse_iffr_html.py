#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import re
from copy import copy
from enum import Enum, auto
from typing import Dict
from urllib.error import HTTPError

from Shared.application_tools import ErrorCollector, DebugRecorder, comment, Config, Counter
from Shared.parse_tools import FileKeeper, try_parse_festival_sites, HtmlPageParser
from Shared.planner_interface import FilmInfo, Screening, ScreenedFilmType, ScreenedFilm, FestivalData, Film
from Shared.web_tools import UrlFile, iri_slug_to_url, fix_json, get_encoding, UrlReader

ALWAYS_DOWNLOAD = True
DEBUGGING = True

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

    # Set-up counters.
    counter.start('no description')
    counter.start('combinations')
    counter.start('feature films')
    counter.start('shorts')
    counter.start('public')
    counter.start('industry')
    counter.start('fabricated screenings')
    counter.start('extras in screening')
    counter.start('fabricated combinations')

    # Try parsing the websites.
    try_parse_festival_sites(parse_iffr_sites, festival_data, error_collector, debug_recorder, festival, counter)


def parse_iffr_sites(festival_data):
    comment('Parsing AZ pages.')
    get_films(festival_data)

    # comment('Parsing film pages.')
    # get_film_details(festival_data)
    #
    comment('Parsing subsection pages.')
    get_subsection_details(festival_data)


def get_films(festival_data):
    url_festival = iffr_hostname.split('/')[2].split('.')[0]
    az_url_path = f'/nl/{url_festival}/{festival_year}/a-z'
    az_url = iri_slug_to_url(iffr_hostname, az_url_path)
    az_file = file_keeper.az_file()
    url_file = UrlFile(az_url, az_file, error_collector, debug_recorder, byte_count=200)
    az_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=f'Downloading AZ page')
    if az_html is not None:
        comment(f'Analysing AZ page, encoding={url_file.encoding}')
        AzPageParser(festival_data).feed(az_html)


def get_film_details(festival_data):
    combi_keeper = CombinationKeeper()
    films = [film for film in festival_data.films if film.medium_category == Film.category_by_string['films']]
    for film in films:
        film_file = file_keeper.film_webdata_file(film.filmid)
        url_file = UrlFile(film.url, film_file, error_collector, debug_recorder, byte_count=300)
        film_html = url_file.get_text(f'Downloading site of {film.title}: {film.url}, encoding: {url_file.encoding}')
        if film_html is not None:
            print(f'Analysing html file {film.filmid} of {film.title}')
            FilmInfoPageParser(festival_data, film, combi_keeper, url_file.encoding).feed(film_html)
    combi_keeper.apply_combinations(festival_data)


def get_combination_film(festival_data, combi_keeper, url, charset):
    # Try if the film to be read already has a number.
    try:
        film_id = festival_data.film_id_by_url[url]
    except KeyError:
        get_combination_film_from_url(festival_data, combi_keeper, url, charset)
    else:
        film = festival_data.get_film_by_id(film_id)
        if film is None:
            # Get the html data from the numbered file if it exists, or
            # from the url otherwise.
            film_file = file_keeper.film_webdata_file(film_id)
            url_file = UrlFile(url, film_file, error_collector, debug_recorder, byte_count=300)
            log_str = f'Downloading site of combination program: {url}'
            combination_html = url_file.get_text(f'{log_str}, encoding: {url_file.encoding}')
            if combination_html is not None:
                print(f'Analysing html file {film_id} of {url}')
                CombinationPageParser(festival_data, combi_keeper, url).feed(combination_html)


def get_combination_film_from_url(festival_data, combi_keeper, url, charset):
    # Get an encoding, even in harsh circumstances like gupta's amd
    # circular redirections.
    encoding = get_encoding(url, error_collector, debug_recorder, charset)

    # Get the html data form the url.
    print(f'Requesting combination page {url}, encoding={encoding}')
    reader = UrlReader(error_collector)
    combination_parser = CombinationPageParser(festival_data, combi_keeper, url)
    try:
        combination_html = reader.load_url(url, None, encoding)
    except HTTPError as e:
        debug_recorder.add(f'HTTP ERROR {e} while getting combination program from {url}')
        print(f'WORKAROUND: Fabricating combination program')
        combination_parser.fabricate_combination_program()
    else:
        print(f'Analysing combination program data from {url}')
        combination_parser.feed(combination_html)

        # Write the gotten html to file.
        try:
            film_id = festival_data.film_id_by_url[url]
        except KeyError as e:
            error_collector.add(e, 'No film id found with this URL')
        else:
            # Verify if the combination program file isn't fabricated.
            if film_id not in CombinationPageParser.fabricated_film_ids:
                film_file = file_keeper.film_webdata_file(film_id)
                print(f'Writing combination program {festival_data.get_film_by_id(film_id).title} to {film_file}')
                html_bytes = combination_html.encode(encoding=encoding)
                with open(film_file, 'wb') as f:
                    f.write(html_bytes)


def get_subsection_details(festival_data):
    for subsection in festival_data.subsection_by_name.values():
        subsection_file = file_keeper.numbered_webdata_file('subsection_file', subsection.subsection_id)
        url_file = UrlFile(subsection.url, subsection_file, error_collector, debug_recorder, byte_count=300)
        comment_at_download = f'Downloading {subsection.name} page: {subsection.url}, encoding: {url_file.encoding}'
        subsection_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
        if subsection_html is not None:
            print(f'Analysing subsection page {subsection.subsection_id}, {subsection.name}, encoding={url_file.encoding}.')
            SubsectionPageParser(festival_data, subsection).feed(subsection_html)


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
        2: 'PapayaWhip',
        3: 'DarkMagenta',
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
        self.init_categories()

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

    @staticmethod
    def init_categories():
        Film.category_by_string['Film'] = Film.category_films
        Film.category_by_string['CombinedProgram'] = Film.category_combinations
        Film.category_by_string['OtherProgram'] = Film.category_events

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
            if not description:
                counter.increase('no description')
        if list_description == 'Binnenkort meer informatie over deze film.':
            description = ''
        if description:
            if not article:
                article = description
            if article != description:
                article = description + 2*'\n' + article
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
            self.increase_film_counter(self.film)
            self.increase_combination_counter()
            self.film_id_by_title[self.film.title] = self.film.filmid
            print(f'Adding FILM: {self.title} ({self.film.duration_str()}) {self.film.medium_category}')
            self.festival_data.films.append(self.film)
            self.film.subsection = self.get_subsection()
            self.add_film_info()

    def add_film_info(self):
        if len(self.description) > 0:
            film_info = FilmInfo(self.film.filmid, self.description, self.article)
            self.festival_data.filminfos.append(film_info)

    def increase_film_counter(self, film):
        key = 'feature films' if film.duration > self.max_short_duration else 'shorts'
        counter.increase(key)

    def increase_combination_counter(self):
        if Film.category_by_string[self.film.medium_category] == Film.category_combinations:
            counter.increase('combinations')

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


class CombinationKeeper:

    def __init__(self):
        self.main_film_by_extra_id = {}

    def apply_combinations(self, festival_data):
        for extra_id, main_film in self.main_film_by_extra_id.items():
            extra_film = festival_data.get_film_by_id(extra_id)
            if extra_film is None:
                error_collector.add('Extra film not found', f'Film ID: {extra_id}')
            else:
                extra_film_info = extra_film.film_info(festival_data)
                main_film_info = main_film.film_info(festival_data)
                screened_film_type = ScreenedFilmType.SCREENED_BEFORE
                screened_film = ScreenedFilm(
                    extra_id, extra_film.title, extra_film_info.description, screened_film_type)
                main_film_info.screened_films.append(screened_film)
                extra_film_info.combination_films.append(main_film)
                counter.increase('extras in screening')


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

    def __init__(self, festival_data, combi_keeper, debug_recorder, debug_prefix, debugging=DEBUGGING):
        HtmlPageParser.__init__(self, festival_data, debug_recorder, debug_prefix, debugging=debugging)
        self.combi_keeper = combi_keeper
        self.film = None
        self.film_info = None
        self.start_date = None
        self.times_str = None
        self.start_dt = None
        self.end_dt = None
        self.location = None
        self.screen = None
        self.combination_program = None
        self.screened_film_type = None
        self.combination_part = None
        self.combination_parts = None
        self.audience = None
        self.extra = None
        self.subtitles = None
        self.q_and_a = None
        self.screenings = []

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.ScreeningParseState.IDLE)

    def init_screening_data(self):
        self.times_str = ''
        self.start_dt = None
        self.end_dt = None
        self.location = None
        self.screen = None
        self.combination_program = None
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

    def set_combination_info(self):
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
                    self.combination_program = main_film
                    self.combi_keeper.main_film_by_extra_id[self.film.filmid] = main_film

    def add_on_location_screening(self):
        self.screen = self.festival_data.get_screen(festival_city, self.location)
        iffr_screening = IffrScreening(self.film, self.screen, self.start_dt, self.end_dt, self.q_and_a,
                                       self.extra, self.audience, self.screened_film_type)
        iffr_screening.combination_program = self.combination_program
        iffr_screening.subtitles = self.subtitles
        self.add_screening(iffr_screening, display=True)
        counter.increase('public' if self.audience == Screening.audience_type_public else 'industry')
        self.screenings.append(self.screening)

    def update_screenings(self):
        combination_films = self.film_info.combination_films
        if len(combination_films) > 0:
            for screening in self.screenings:
                screening.combination_program = combination_films[0]

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
            self.set_combination_info()
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
            self.update_screenings()
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
            if data == 'Voor professionals':
                self.audience = data
            if 'Q&A' in data:
                self.q_and_a = 'Q&A'
            if 'voorfilm' in data:
                self.extra = 'voorfilm'
                self.screened_film_type = ScreenedFilmType.SCREENED_BEFORE
            if data.endswith('ondertiteld'):
                self.subtitles = data


class FilmInfoPageParser(ScreeningParser):
    class FilmInfoParseState(Enum):
        IDLE = auto()
        IN_ARTICLE = auto()
        IN_PARAGRAPH = auto()
        IN_EMPHASIS = auto()
        AWAITING_SCREENINGS = auto()
        AWAITING_COMBINATION_LINK = auto()
        IN_COMBINATION_LINK = auto()
        DONE = auto()

    debugging = DEBUGGING
    intro_span = datetime.timedelta(minutes=4)
    combination_loaded_by_url = {}

    def __init__(self, festival_data, film, combi_keeper, charset):
        ScreeningParser.__init__(self, festival_data, combi_keeper, debug_recorder, 'FI', self.debugging)
        self.festival_data = festival_data
        self.film = film
        self.charset =  charset
        self.article_paragraphs = []
        self.article_paragraph = ''
        self.article = None
        self.combination_slug = None

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
        combination_url = iri_slug_to_url(iffr_hostname, self.combination_slug)
        if combination_url not in self.combination_loaded_by_url.keys():
            self.combination_loaded_by_url[combination_url] = True
            self.print_debug('-- FOLLOW COMBINATION URL', f'{combination_url}')
            get_combination_film(self.festival_data, self.combi_keeper, combination_url, self.charset)
        try:
            combination_program = CombinationPageParser.combination_program_by_url[combination_url]
        except KeyError as e:
            error_collector.add(e, 'No combination program with this url')
        else:
            self.film_info.combination_films.append(combination_program)
            screened_film = ScreenedFilm(self.film.filmid, self.film.title, self.film_info.description)
            combination_program.film_info(self.festival_data).screened_films.append(screened_film)

            # If this combination was fabricated because IFFR introduced
            # a gupta, fabricate its screenings.
            self.check_set_fabricated_screenings(combination_program)

    def check_set_fabricated_screenings(self, combination_program):
        if combination_program.filmid in CombinationPageParser.fabricated_film_ids:
            screenings = self.film.screenings(self.festival_data)

            # If the fabricated program has no screenings yet, copy
            # them fom the screened film screenings.
            combination_program_screening_count = len(combination_program.screenings(self.festival_data))
            if combination_program_screening_count == 0:
                for screening in screenings:
                    counter.increase('fabricated screenings')
                    combi_screening = copy(screening)
                    combi_screening.film = combination_program
                    self.add_screening(combi_screening)

            # Set the combination program in all screened film screenings.
            for screening in screenings:
                screening.combination_program = combination_program

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        # Article part.
        if self.state_stack.state_is(self.FilmInfoParseState.IDLE) and tag == 'div' and len(attrs) > 0:
            if attrs[0][0] == 'class' and attrs[0][1] in ['sc-fujyAs induiK', 'sc-dkuGKe fXALKH']:
                self.state_stack.push(self.FilmInfoParseState.IN_ARTICLE)
        elif self.state_stack.state_is(self.FilmInfoParseState.IN_ARTICLE) and tag == 'p':
            self.state_stack.push(self.FilmInfoParseState.IN_PARAGRAPH)
        elif self.state_stack.state_is(self.FilmInfoParseState.IN_PARAGRAPH) and tag == 'em':
            self.state_stack.push(self.FilmInfoParseState.IN_EMPHASIS)

        # Combination part.
        elif self.state_stack.state_is(self.FilmInfoParseState.AWAITING_COMBINATION_LINK) and tag == 'a':
            if len(attrs) > 1 and attrs[0][1] == 'sc-csTbgd hGhsas':
                self.combination_slug = attrs[1][1]
                self.state_stack.change(self.FilmInfoParseState.IN_COMBINATION_LINK)

        # Screening part.
        else:
            self.handle_screening_starttag(tag, attrs, self.state_stack,
                                           self.FilmInfoParseState.AWAITING_SCREENINGS,
                                           self.FilmInfoParseState.AWAITING_COMBINATION_LINK)

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
        else:
            self.handle_screening_endtag(tag, self.state_stack, self.FilmInfoParseState.AWAITING_COMBINATION_LINK)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_in([self.FilmInfoParseState.IN_PARAGRAPH,
                                      self.FilmInfoParseState.IN_EMPHASIS,
                                      self.FilmInfoParseState.IN_ARTICLE]):
            self.article_paragraph += data.replace('\n', ' ')
        elif self.state_stack.state_is(self.FilmInfoParseState.IN_COMBINATION_LINK):
            if data.strip() == 'Bekijk het gehele verzamelprogramma':
                self.print_debug('Setting combination program', f'{self.combination_slug}')
                self.set_combination()
            else:
                self.print_debug('NOT a combination program', f'{self.combination_slug}')
            self.state_stack.change(self.FilmInfoParseState.DONE)
        else:
            self.handle_screening_data(data)


class CombinationPageParser(ScreeningParser):

    class CombinationParserState(Enum):
        IDLE = auto()
        IN_TITLE = auto()
        AWAITING_SECTION = auto()
        IN_SUBSECTION = auto()
        AWAITING_DESCRIPTION = auto()
        IN_PARAGRAPH = auto()
        IN_EMPHASIS = auto()
        AWAITING_SCREENINGS = auto()
        DONE = auto()

    combination_program_by_url = {}
    fabricated_film_ids = []

    def __init__(self, festival_data, combi_keeper, url):
        ScreeningParser.__init__(self, festival_data, combi_keeper, debug_recorder, 'CO', debugging=DEBUGGING)
        self.festival_data = festival_data
        self.url = url
        self.title = None
        self.combination_program = None
        self.film_info = None
        self.section_name = None
        self.subsection_name = None
        self.subsection_url = None

        # Print a bar in the debug file when debugging.
        self.print_debug(self.bar, f'Analysing COMBINATION PROGRAM {self.url}')

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.CombinationParserState.IDLE)

    def fabricate_combination_program(self):
        film_id = self.festival_data.film_id_by_url[self.url]
        title = self.festival_data.title_by_film_id[film_id]
        self.festival_data.film_seqnr += 1
        self.combination_program = Film(self.festival_data.film_seqnr, film_id, title, self.url)
        if self.combination_program is None:
            error_collector.add('Could not fabricate combination film', f'title {title}, url {self.url}')
        else:
            counter.increase('fabricated combinations')
            self.fabricated_film_ids.append(film_id)
            self.description = 'No description'
            self.add_existing_combination_film()

    def add_combination_film(self):
        self.combination_program = self.festival_data.create_film(self.title, self.url)
        if self.combination_program is None:
            error_collector.add(f'Could\'t create combination program from {self.title}', self.url)
        else:
            self.add_existing_combination_film()

    def add_existing_combination_film(self):
        self.combination_program.medium_category = Film.category_by_string['combinations']
        self.combination_program.duration = datetime.timedelta(minutes=0)
        if len(self.description) == 0:
            self.subsection_name = 'NO DESCRIPTION'
        section = self.festival_data.get_section(self.section_name)
        if section is not None:
            subsection = self.festival_data.get_subsection(self.subsection_name, self.subsection_url, section)
            self.combination_program.subsection = subsection
        print(f'Adding COMBINATION PROGRAM: {self.title}')
        counter.increase('combinations')
        self.festival_data.films.append(self.combination_program)
        self.film = self.combination_program
        self.print_debug('-- STORING COMBI BY URL', f'title: {self.combination_program.title}, url: {self.url}')
        self.combination_program_by_url[self.url] = self.combination_program
        self.add_combination_film_info()

    def add_combination_film_info(self):
        if len(self.description) > 0:
            self.film_info = FilmInfo(self.combination_program.filmid, self.description, '')
            self.festival_data.filminfos.append(self.film_info)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.CombinationParserState.IDLE) and tag == 'h1':
            if len(attrs) > 0 and attrs[0][1].endswith('header__title'):
                self.state_stack.change(self.CombinationParserState.IN_TITLE)
        elif self.state_stack.state_is(self.CombinationParserState.AWAITING_SECTION) and tag == 'a':
            if len(attrs) > 6 and attrs[0][0] == 'tagcolor':
                self.section_name = attrs[0][1]
                self.subsection_url = attrs[6][1]
                self.state_stack.change(self.CombinationParserState.IN_SUBSECTION)
        elif self.state_stack.state_is(self.CombinationParserState.AWAITING_DESCRIPTION) and tag == 'div':
            if len(attrs) > 0 and attrs[0][0] == 'class':
                self.state_stack.push(self.CombinationParserState.IN_PARAGRAPH)
        elif self.state_stack.state_is(self.CombinationParserState.IN_PARAGRAPH) and tag == 'em':
            self.state_stack.push(self.CombinationParserState.IN_EMPHASIS)

        # Screening part.
        else:
            self.handle_screening_starttag(tag, attrs, self.state_stack,
                                           self.CombinationParserState.AWAITING_SCREENINGS,
                                           self.CombinationParserState.DONE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_in([self.CombinationParserState.IN_EMPHASIS]) and tag == 'em':
            self.state_stack.pop()
        elif self.state_stack.state_is(self.CombinationParserState.IN_PARAGRAPH) and tag == 'div':
            self.state_stack.pop()
            self.add_paragraph()
            self.set_article()
            self.description = self.article
            self.add_combination_film()
            self.state_stack.change(self.CombinationParserState.AWAITING_SCREENINGS)
        elif tag == 'html' and not self.state_stack.state_is(self.CombinationParserState.DONE):
            self.print_debug('WORK AROUND THE APPEARANCE OF A GUPTA', f'url {self.url}')
            self.fabricate_combination_program()
            self.state_stack.change(self.CombinationParserState.DONE)
        else:
            self.handle_screening_endtag(tag, self.state_stack, self.CombinationParserState.DONE)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.CombinationParserState.IN_TITLE):
            self.title = data.strip()
            self.print_debug(self.bar, f'Analysing COMBINATION PROGRAM {self.title} {self.url}')
            self.state_stack.change(self.CombinationParserState.AWAITING_SECTION)
        elif self.state_stack.state_is(self.CombinationParserState.IN_SUBSECTION):
            self.subsection_name = data.strip()
            self.state_stack.change(self.CombinationParserState.AWAITING_DESCRIPTION)
        if self.state_stack.state_in([self.CombinationParserState.IN_PARAGRAPH,
                                      self.CombinationParserState.IN_EMPHASIS]):
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

    def __init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience, screened_film_type=None):
        Screening.__init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience)
        self.screened_film_type = screened_film_type


class IffrData(FestivalData):

    def __init__(self, planner_data_dir):
        FestivalData.__init__(self, planner_data_dir, festival_city)

    def film_key(self, title, url):
        return url

    def film_can_go_to_planner(self, filmid):
        return True


if __name__ == "__main__":
    main()
