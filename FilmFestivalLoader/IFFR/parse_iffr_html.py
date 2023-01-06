#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import re
from enum import Enum, auto
from json import JSONDecodeError
from typing import Dict

from Shared.application_tools import ErrorCollector, DebugRecorder, comment
from Shared.parse_tools import FileKeeper, try_parse_festival_sites, HtmlPageParser
from Shared.planner_interface import FilmInfo, Screening, ScreenedFilmType, ScreenedFilm, FestivalData, Film
from Shared.web_tools import UrlFile, iri_slug_to_url, fix_json, get_encoding, UrlReader

festival = 'IFFR'
festival_year = 2023
festival_city = 'Rotterdam'

# Files.
file_keeper = FileKeeper(festival, festival_year)
debug_file = file_keeper.debug_file

# URL information.
iffr_hostname = "https://iffr.com"
url_festival = iffr_hostname.split('/')[2].split('.')[0]
az_url_path = f'/nl/{url_festival}/{festival_year}/a-z'

# Application tools.
error_collector = ErrorCollector()
debug_recorder = DebugRecorder(debug_file)


def main():
    # Initialize a festival data object.
    festival_data: IffrData = IffrData(file_keeper.plandata_dir)

    # Try parsing the websites.
    try_parse_festival_sites(parse_iffr_sites, festival_data, error_collector, debug_recorder, festival)


def parse_iffr_sites(festival_data):
    comment('Parsing AZ pages.')
    get_films(festival_data)

    comment('Parsing film pages.')
    get_film_details(festival_data)

    comment('Parsing subsection pages.')
    get_subsection_details(festival_data)


def get_films(festival_data):
    az_url = iffr_hostname + az_url_path
    az_file = file_keeper.az_file()
    url_file = UrlFile(az_url, az_file, error_collector, byte_count=30000)
    az_html = url_file.get_text()
    if az_html is not None:
        AzPageParser(festival_data).feed(az_html)


def get_film_details(festival_data):
    films = [film for film in festival_data.films if film.medium_category == Film.category_string_films]
    for film in films:
        film_file = file_keeper.film_webdata_file(film.filmid)
        url_file = UrlFile(film.url, film_file, error_collector, byte_count=1000)
        film_html = url_file.get_text(f'Downloading site of {film.title}: {film.url}, encoding: {url_file.encoding}')
        if film_html is not None:
            print(f'Analysing html file {film.filmid} of {film.title}')
            # ScreeningsPageParser(festival_data, film).feed(film_html)
            FilmInfoPageParser(festival_data, film).feed(film_html)
    FilmInfoPageParser.apply_combinations(festival_data)


def get_combination_film(festival_data, url):
    encoding = get_encoding(url, error_collector)
    reader = UrlReader(error_collector)
    print(f'Requesting combination page {url}, encoding={encoding}')
    combination_html = reader.load_url(url, None, encoding)
    if combination_html is not None:
        print(f'Analysing combination program data from {url}')
        CombinationPageParser(festival_data, url).feed(combination_html)


def get_subsection_details(festival_data):
    for subsection in festival_data.subsection_by_name.values():
        subsection_file = file_keeper.numbered_webdata_file('subsection_file', subsection.subsection_id)
        url_file = UrlFile(subsection.url, subsection_file, error_collector, byte_count=300)
        comment_at_download = f'Downloading {subsection.name} page: {subsection.url}, encoding: {url_file.encoding}'
        subsection_html = url_file.get_text(comment_at_download)
        if subsection_html is not None:
            print(f'Analysing html file {subsection.subsection_id} of {subsection.name}.')
            SubsectionPageParser(festival_data, subsection).feed(subsection_html)


class AzPageParser(HtmlPageParser):
    class AzParseState(Enum):
        IDLE = auto()
        IN_FILM_SCRIPT = auto()
        DONE = auto()

    props_re = re.compile(
        r"""
            "Film","id":"[^"]*?","title":"(?P<title>[^"]+)"                     # Title
            .*?,"url\(\{\\"language\\":\\"nl\\"\}\)":"(?P<url>[^"]+)"           # Film URL
            ,"description\(\{.*?\}\)":"(?P<grid_desc>.+?)"                      # Grid description
            ,"description\(\{.*?\}\)":"(?P<list_desc>.+?)"                      # List description
            ,"section":([^:]*?:"Section","title":"(?P<section>[^"]+)".*?|null)  # IFFR Section
            ,"subSection":([^:]*?:"SubSection","title":"(?P<subsection>[^"]+)"  # IFFR Sub-section
            ,"url\(\{.*?\}\)":"(?P<subsection_url>[^"]+)".*?|null)              # Sub-section URL
            ,"duration":(?P<duration>\d+),".*?                                  # Duration
            ,"sortedTitle":"(?P<sorted_title>[^"]+)"                            # Sorted Title
        """, re.VERBOSE)

    def __init__(self, festival_data):
        HtmlPageParser.__init__(self, festival_data, debug_recorder, 'AZ', debugging=False)
        self.film = None
        self.title = None
        self.url = None
        self.description = None
        self.section_name = None
        self.subsection_name = None
        self.subsection_url = None
        self.sorted_title = None
        self.duration = None
        self.state_stack = self.StateStack(self.print_debug, self.AzParseState.IDLE)
        self.init_film_data()

    def init_film_data(self):
        self.film = None
        self.title = None
        self.url = None
        self.duration = None
        self.description = None
        self.section_name = None
        self.subsection_name = None
        self.subsection_url = None
        self.sorted_title = None

    def parse_props(self, data):
        i = self.props_re.finditer(data)
        matches = [match for match in i]
        groups = [m.groupdict() for m in matches]
        for g in groups:
            self.title = fix_json(g['title'])
            self.url = iri_slug_to_url(iffr_hostname, g['url'])
            self.description = self.get_description(g['list_desc'])
            if g['section']:
                self.section_name = fix_json(g['section'])
            if g['subsection']:
                self.subsection_name = fix_json(g['subsection']).rstrip()
            if g['subsection_url']:
                self.subsection_url = iri_slug_to_url(iffr_hostname, g['subsection_url'])
            self.sorted_title = fix_json(g['sorted_title']).lower()
            self.duration = self.get_duration(g['duration'])
            self.add_film()
            self.init_film_data()

    def get_description(self, parsed_description):
        try:
            description = fix_json(parsed_description)
        except JSONDecodeError as e:
            error_collector.add(f'{self.title}: {e}:', parsed_description)
            description = ''
        if parsed_description == 'Binnenkort meer informatie over deze film.':
            description = ''
        return description

    @staticmethod
    def get_duration(minutes_str):
        minutes = 0 if minutes_str is None else int(minutes_str)
        duration = datetime.timedelta(minutes=minutes)
        return duration

    def add_film(self):
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            error_collector.add(f'Could\'t create film from {self.title}', self.url)
        else:
            self.film.medium_category = self.url.split('/')[6]   # https://iffr.com/nl/iffr/2023/films/firaaq
            if self.film.medium_category != Film.category_string_films:
                error_collector.add(f'Unexpected category in: {self.film.title}', f'{self.film.medium_category} from {self.url}')
            self.film.duration = self.duration
            self.film.sortstring = self.sorted_title
            print(f'Adding FILM: {self.title} ({self.film.duration_str()}) {self.film.medium_category}')
            self.festival_data.films.append(self.film)
            if len(self.description) == 0:
                self.subsection_name = 'NO DESCRIPTION'
            section = self.festival_data.get_section(self.section_name)
            if section is not None:
                subsection = self.festival_data.get_subsection(self.subsection_name, self.subsection_url, section)
                self.film.subsection = subsection
            self.add_film_info()

    def add_film_info(self):
        if len(self.description) > 0:
            film_info = FilmInfo(self.film.filmid, self.description, '')
            self.festival_data.filminfos.append(film_info)

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


# class ScreeningsPageParser(HtmlPageParser):
#     class ScreeningsParseState(Enum):
#         IDLE = auto()
#         IN_ON_DEMAND = auto()
#         IN_ON_DEMAND_START_TIME = auto()
#         BETWEEN_ON_DEMAND_TIMES = auto()
#         IN_ON_DEMAND_END_TIME = auto()
#         AFTER_ON_DEMAND_END_TIME = auto()
#         IN_SCREENINGS = auto()
#         IN_SCREENING_DATE = auto()
#         IN_SCREENING_TIMES = auto()
#         IN_SCREENING_LOCATION = auto()
#         AFTER_SCREENING_LOCATION = auto()
#         IN_SCREENING_INFO = auto()
#         DONE = auto()
#
#     on_demand_location = "OnDemand"
#     nl_month_by_name: Dict[str, int] = {'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
#                                         'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11,
#                                         'december': 12}
#
#     def __init__(self, festival_data, film):
#         HtmlPageParser.__init__(self, festival_data, debug_recorder, "FS", debugging=True)
#         self.film = film
#         self.location = None
#         self.start_date = None
#         self.subtitles = None
#         self.qa = None
#         self.times = None
#         self.end_dt = None
#         self.start_dt = None
#         self.extra = None
#         self.audience = None
#         self.screen = None
#         self.print_debug(f"{40 * '-'} ", f"Analysing FILM {film}, {film.url}")
#
#         self.init_screening_data()
#         self.state_stack = self.StateStack(self.print_debug, self.ScreeningsParseState.IDLE)
#
#     def init_screening_data(self):
#         self.audience = 'publiek'
#         self.extra = ''
#         self.qa = ''
#         self.subtitles = ''
#         self.location = None
#         self.screen = None
#         self.start_dt = None
#         self.end_dt = None
#         self.start_date = None
#         self.times = None
#
#     def add_on_demand_screening(self):
#         self.screen = self.festival_data.get_screen(festival_city, self.on_demand_location)
#         self.add_screening()
#
#     def add_on_location_screening(self):
#         self.screen = self.festival_data.get_screen(festival_city, self.location)
#         self.add_screening()
#
#     def add_screening(self):
#         # Set some unwanted screenings to non-public.
#         if self.film.title.startswith('GLR '):
#             self.audience = 'GLR'
#         elif self.film.title == 'Testing' or self.film.title.startswith('IFFR'):
#             self.audience = 'Testers'
#         elif self.film.title == 'The Last Movie':
#             self.audience = 'Crew'
#         self.print_debug("--- ",
#                          f"SCREEN={self.screen}, START TIME={self.start_dt}, END TIME={self.end_dt}, AUDIENCE={self.audience}")
#
#         # Print the screening properties.
#         if self.audience == 'publiek' and self.film.medium_category != 'events':
#             print()
#             print(f"---SCREENING OF {self.film.title}")
#             print(f"--  screen:     {self.screen}")
#             print(f"--  start time: {self.start_dt}")
#             print(f"--  end time:   {self.end_dt}")
#             print(f"--  duration:   film: {self.film.duration_str()}  screening: {self.end_dt - self.start_dt}")
#             print(f"--  audience:   {self.audience}")
#             print(f"--  category:   {self.film.medium_category}")
#             print(f"--  q and a:    {self.qa}")
#             print(f"--  extra:      {self.extra}")
#             print(f"--  subtitles:  {self.subtitles}")
#
#         # Create a new screening object.
#         program = None
#         screening = Screening(self.film, self.screen, self.start_dt, self.end_dt, self.qa,
#                               self.extra, self.audience, program, self.subtitles)
#
#         # Add the screening to the list.
#         self.festival_data.screenings.append(screening)
#         print("---SCREENING ADDED")
#
#         # Initialize the next round of parsing.
#         self.init_screening_data()
#
#     def parse_datetime(self, data):
#         items = data.split()  # zaterdag 06 februari 13:00
#         day = int(items[1])
#         month = self.nl_month_by_name[items[2]]
#         time = items[3].split(':')
#         hours = int(time[0])
#         minutes = int(time[1])
#         year = festival_year
#
#         # Work around test data from the festival
#         if month > 10:
#             year = festival_year - 1
#
#         return datetime.datetime(year, month, day, hours, minutes)
#
#     def parse_date(self, data):
#         items = data.split()  # woensdag 03 februari 2021
#         day = int(items[1])
#         month = self.nl_month_by_name[items[2]]
#         year = int(items[3])
#         return datetime.date(year, month, day)
#
#     def set_screening_times(self, data):
#         items = data.split()  # 13:00 - 15:26
#         start_time = datetime.time.fromisoformat(items[0])
#         end_time = datetime.time.fromisoformat(items[2])
#         self.start_dt = datetime.datetime.combine(self.start_date, start_time)
#         end_date = self.start_date if end_time > start_time else self.start_date + datetime.timedelta(days=1)
#         self.end_dt = datetime.datetime.combine(end_date, end_time)
#
#     def set_screening_info(self, data):
#         self.print_debug('Found SCREENING info', data)
#         if 'professionals' in data:
#             self.audience = 'Industry'
#         if 'Q&A' in data:
#             self.qa = 'Q&A'
#         if 'ondertiteld' in data:
#             self.subtitles = data
#         if 'voorfilm' in data:
#             self.extra = 'Voorfilm'
#
#     def handle_starttag(self, tag, attrs):
#         HtmlPageParser.handle_starttag(self, tag, attrs)
#
#         # Get data for screenings.
#         if self.state_stack.state_is(self.ScreeningsParseState.IDLE) and tag == 'header' and len(attrs) > 0:
#             if attrs[0][1] == 'bookingtable-on-demand__header':
#                 self.state_stack.push(self.ScreeningsParseState.IN_ON_DEMAND)
#             if attrs[0][1] == 'bookingtable__header':
#                 self.state_stack.change(self.ScreeningsParseState.IN_SCREENINGS)
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_ON_DEMAND) and tag == 'span' and len(attrs) > 0:
#             if attrs[0][1] == 'bookingtable-on-demand__date-value':
#                 self.state_stack.change(self.ScreeningsParseState.IN_ON_DEMAND_START_TIME)
#         elif self.state_stack.state_is(self.ScreeningsParseState.BETWEEN_ON_DEMAND_TIMES) and tag == 'span':
#             if attrs[0][1] == 'bookingtable-on-demand__date-value':
#                 self.state_stack.change(self.ScreeningsParseState.IN_ON_DEMAND_END_TIME)
#         elif self.state_stack.state_is(self.ScreeningsParseState.AFTER_ON_DEMAND_END_TIME) and tag == 'div':
#             if attrs[0] == ('class', 'bookingtable-on-demand__time-remaning-wrapper'):
#                 self.state_stack.change(self.ScreeningsParseState.IN_ON_DEMAND)
#                 self.add_on_demand_screening()
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_SCREENING_DATE) and tag == 'time':
#             if attrs[0] == ('class', 'bookingtable__time'):
#                 self.state_stack.change(self.ScreeningsParseState.IN_SCREENING_TIMES)
#                 self.times = ''
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_SCREENING_TIMES) and tag == 'div':
#             if attrs[0] == ('class', 'booking__table__location'):
#                 self.state_stack.change(self.ScreeningsParseState.IN_SCREENING_LOCATION)
#         elif self.state_stack.state_is(self.ScreeningsParseState.AFTER_SCREENING_LOCATION) and tag == 'div' and len(
#                 attrs) > 0:
#             if attrs[0] == ('class', 'bookingtable__calender-link'):
#                 self.state_stack.change(self.ScreeningsParseState.IN_SCREENINGS)
#                 self.add_on_location_screening()
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'div' and len(attrs) > 0:
#             if attrs[0] == ('class', 'bookingtable__date-wrapper'):
#                 self.state_stack.change(self.ScreeningsParseState.IN_SCREENING_DATE)
#         if self.state_stack.state_in([self.ScreeningsParseState.AFTER_ON_DEMAND_END_TIME,
#                                      self.ScreeningsParseState.AFTER_SCREENING_LOCATION]) and tag == 'div' and len(
#             attrs) > 0:
#             if attrs[0] == ('class', 'sc-hiKfDv hJEYeH'):
#                 self.state_stack.push(self.ScreeningsParseState.IN_SCREENING_INFO)
#
#     def handle_endtag(self, tag):
#         HtmlPageParser.handle_endtag(self, tag)
#
#         # Get data for screenings.
#         if self.state_stack.state_is(self.ScreeningsParseState.IN_ON_DEMAND) and tag == 'section':
#             self.state_stack.pop()
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_SCREENING_TIMES) and tag == 'time':
#             self.set_screening_times(self.times)
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_SCREENING_INFO) and tag == 'div':
#             self.state_stack.pop()
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'section':
#             self.state_stack.change(self.ScreeningsParseState.DONE)
#
#     def handle_data(self, data):
#         HtmlPageParser.handle_data(self, data)
#
#         if self.state_stack.state_is(self.ScreeningsParseState.IN_ON_DEMAND_START_TIME):
#             self.state_stack.change(self.ScreeningsParseState.BETWEEN_ON_DEMAND_TIMES)
#             self.start_dt = self.parse_datetime(data)
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_ON_DEMAND_END_TIME):
#             self.state_stack.change(self.ScreeningsParseState.AFTER_ON_DEMAND_END_TIME)
#             self.end_dt = self.parse_datetime(data)
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_SCREENING_DATE):
#             self.start_date = self.parse_date(data)
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_SCREENING_TIMES):
#             self.times += data
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_SCREENING_LOCATION):
#             self.state_stack.change(self.ScreeningsParseState.AFTER_SCREENING_LOCATION)
#             self.location = data
#         elif self.state_stack.state_is(self.ScreeningsParseState.IN_SCREENING_INFO):
#             self.set_screening_info(data)


class FilmInfoPageParser(HtmlPageParser):
    class FilmInfoParseState(Enum):
        IDLE = auto()
        IN_ARTICLE = auto()
        IN_PARAGRAPH = auto()
        IN_EMPHASIS = auto()
        AWAITING_COMBINATION_LINK = auto()
        IN_COMBINATION_LINK = auto()
        DONE = auto()

    debugging = True
    intro_span = datetime.timedelta(minutes=4)
    combination_loaded_by_url = {}
    extras_by_main = {}
    screened_film_type_by_string = {
        'Voorfilm bij ': ScreenedFilmType.SCREENED_BEFORE,
        'Te zien na ': ScreenedFilmType.SCREENED_AFTER,
        'Gepresenteerd als onderdeel van ': ScreenedFilmType.PART_OF_COMBINATION_PROGRAM,
        'Wordt vertoond in combinatie met ': ScreenedFilmType.DIRECTLY_COMBINED}

    def __init__(self, festival_data, film):
        HtmlPageParser.__init__(self, festival_data, debug_recorder, 'FI', debugging=self.debugging)
        self.festival_data = festival_data
        self.film = film
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

    @classmethod
    def apply_combinations(cls, festival_data):

        def pr_debug(s):
            if cls.debugging:
                debug_recorder.add('AC ' + s)

        def str_extras(extras):
            return ' [' + ', '.join([' '.join([str(e[0]), e[1].name]) for e in extras]) + ']'

        def pr_debug_dict(d):
            str_dict = '\n'.join([str(mf) + str_extras(extras) for (mf, extras) in d.items()])
            pr_debug(f'Main films and extras:\n{str_dict}')

        def short_str(film_id):
            return festival_data.get_film_by_id(film_id).short_str()

        pr_debug_dict(cls.extras_by_main)

        # Find mutually linked films and decide which will be the main film.
        film_ids_to_pop = set()
        for (main_film_id, extra_infos) in cls.extras_by_main.items():
            if len(extra_infos) == 1:
                (extra_film_id, screened_film_type) = extra_infos[0]
                if extra_film_id in cls.extras_by_main:
                    extra_infos_from_extra = cls.extras_by_main[extra_film_id]
                    if len(extra_infos_from_extra) == 1:
                        extra_info_from_extra = extra_infos_from_extra[0]
                        if extra_info_from_extra == (main_film_id, screened_film_type):
                            main_duration = festival_data.get_film_by_id(main_film_id).duration
                            extra_duration = festival_data.get_film_by_id(extra_film_id).duration
                            pop_film_id = extra_film_id if main_duration > extra_duration else main_film_id
                            film_ids_to_pop.add(pop_film_id)

        # Remove the non-main films from the extras by main dictionary.
        for film_id_to_pop in film_ids_to_pop:
            cls.extras_by_main.pop(film_id_to_pop)

        # Implement the links in the extras by main dictionary in the film info lists.
        for (main_film_id, extra_infos) in cls.extras_by_main.items():
            pr_debug(f'{short_str(main_film_id)} [{" || ".join([short_str(i) for (i, t) in extra_infos])}]')
            main_film = festival_data.get_film_by_id(main_film_id)
            main_film_info = main_film.film_info(festival_data)
            screened_films = []
            for (extra_film_id, screened_film_type) in extra_infos:
                extra_film = festival_data.get_film_by_id(extra_film_id)
                extra_film_info = extra_film.film_info(festival_data)
                extra_film_info.combination_films.append(main_film)
                screened_film = ScreenedFilm(
                    extra_film_id, extra_film.title, extra_film_info.description, screened_film_type)
                screened_films.append(screened_film)
            main_film_info.screened_films.extend(screened_films)

    # def update_screenings(self):
    #     combination_films = self.film_info.combination_films
    #     if len(combination_films) > 0:
    #         screenings = [s for s in self.festival_data.screenings if s.film.filmid == self.film.filmid]
    #         for screening in screenings:
    #             screening.combination_program = combination_films[0]

    def set_combination(self):
        combination_url = iri_slug_to_url(iffr_hostname, self.combination_slug)
        if combination_url not in self.combination_loaded_by_url.keys():
            self.combination_loaded_by_url[combination_url] = True
            get_combination_film(self.festival_data, combination_url)
        try:
            combination_program = CombinationPageParser.combination_program_by_url[combination_url]
        except KeyError as e:
            error_collector.add(e, 'No combination program with this url')
        else:
            self.film_info.combination_films.append(combination_program)
            screened_film = ScreenedFilm(self.film.filmid, self.film.title, self.film_info.description)
            combination_program.film_info(self.festival_data).screened_films.append(screened_film)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.FilmInfoParseState.IDLE) and tag == 'div' and len(attrs) > 0:
            if attrs[0][0] == 'class' and attrs[0][1] in ['sc-fujyAs induiK', 'sc-dkuGKe fXALKH']:
                self.state_stack.push(self.FilmInfoParseState.IN_ARTICLE)
        elif self.state_stack.state_is(self.FilmInfoParseState.IN_ARTICLE) and tag == 'p':
            self.state_stack.push(self.FilmInfoParseState.IN_PARAGRAPH)
        elif self.state_stack.state_is(self.FilmInfoParseState.IN_PARAGRAPH) and tag == 'em':
            self.state_stack.push(self.FilmInfoParseState.IN_EMPHASIS)
        elif self.state_stack.state_is(self.FilmInfoParseState.AWAITING_COMBINATION_LINK) and tag == 'a':
            if len(attrs) > 1 and attrs[0][1] == 'sc-gJpXkD hgMAEf':
                self.combination_slug = attrs[1][1]
                self.state_stack.change(self.FilmInfoParseState.IN_COMBINATION_LINK)

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
            self.state_stack.change(self.FilmInfoParseState.AWAITING_COMBINATION_LINK)

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


class CombinationPageParser(HtmlPageParser):

    class CombinationParserState(Enum):
        IDLE = auto()
        IN_TITLE = auto()
        AWAITING_SECTION = auto()
        IN_SUBSECTION = auto()
        AWAITING_DESCRIPTION = auto()
        IN_PARAGRAPH = auto()
        IN_EMPHASIS = auto()
        DONE = auto()

    combination_program_by_url = {}

    def __init__(self, festival_data, url):
        HtmlPageParser.__init__(self, festival_data, debug_recorder, 'CO', debugging=True)
        self.festival_data = festival_data
        self.url = url
        self.title = None
        self.combination_program = None
        self.section_name = None
        self.subsection_name = None
        self.subsection_url = None
        self.state_stack = self.StateStack(self.print_debug, self.CombinationParserState.IDLE)

    def add_combination_film(self):
        self.combination_program = self.festival_data.create_film(self.title, self.url)
        if self.combination_program is None:
            error_collector.add(f'Could\'t create combination program from {self.title}', self.url)
        else:
            self.combination_program.medium_category = Film.category_string_combinations
            self.combination_program.duration = datetime.timedelta(minutes=0)
            if len(self.description) == 0:
                self.subsection_name = 'NO DESCRIPTION'
            section = self.festival_data.get_section(self.section_name)
            if section is not None:
                subsection = self.festival_data.get_subsection(self.subsection_name, self.subsection_url, section)
                self.combination_program.subsection = subsection
            print(f'Adding COMBINATION PROGRAM: {self.title}')
            self.festival_data.films.append(self.combination_program)
            self.combination_program_by_url[self.url] = self.combination_program
            self.add_combination_film_info()

    def add_combination_film_info(self):
        if len(self.description) > 0:
            film_info = FilmInfo(self.combination_program.filmid, self.description, '')
            self.festival_data.filminfos.append(film_info)

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
            self.state_stack.change(self.CombinationParserState.DONE)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.CombinationParserState.IN_TITLE):
            self.title = data.strip()
            self.state_stack.change(self.CombinationParserState.AWAITING_SECTION)
        elif self.state_stack.state_is(self.CombinationParserState.IN_SUBSECTION):
            self.subsection_name = data.strip()
            self.state_stack.change(self.CombinationParserState.AWAITING_DESCRIPTION)
        if self.state_stack.state_in([self.CombinationParserState.IN_PARAGRAPH,
                                      self.CombinationParserState.IN_EMPHASIS]):
            self.article_paragraph += data.replace('\n', ' ')


class SubsectionPageParser(HtmlPageParser):

    class SubsectionsParseState(Enum):
        IDLE = auto()
        AWAITING_DESCRIPTION = auto()
        IN_DESCRIPTION = auto()
        DONE = auto()

    debugging = False

    def __init__(self, festival_data, subsection):
        HtmlPageParser.__init__(self, festival_data, debug_recorder, 'SEC', debugging=True)
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


class IffrData(FestivalData):

    def __init__(self, planner_data_dir):
        FestivalData.__init__(self, planner_data_dir)

    def film_key(self, title, url):
        return url

    def film_can_go_to_planner(self, filmid):
        return True


if __name__ == "__main__":
    main()
