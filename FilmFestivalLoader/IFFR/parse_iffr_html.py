#!/Users/maarten/opt/anaconda3/bin/python3

import os
import sys
import re
import datetime
from enum import Enum, auto
from typing import Dict

shared_dir = os.path.expanduser("~/Projects/FilmFestivalPlanner/FilmFestivalLoader/Shared")
sys.path.insert(0, shared_dir)
import planner_interface as planner
import application_tools as app_tools
import web_tools

# Parameters.
festival = 'IFFR'
year = 2021
city = 'Rotterdam'

# Directories.
documents_dir = os.path.expanduser("~/Documents/Film/{0}/{0}{1}".format(festival, year))
webdata_dir = os.path.join(documents_dir, "_website_data")
plandata_dir = os.path.join(documents_dir, "_planner_data")

# Filename formats.
film_file_format = os.path.join(webdata_dir, "filmpage_{:03d}.html")

# Files.
az_file = os.path.join(webdata_dir, "azpage_01.html")
debug_file = os.path.join(plandata_dir, "debug.txt")

# URL information.
iffr_hostname = "https://iffr.com"
url_festival = iffr_hostname.split('/')[2].split('.')[0]
az_url_path = "/nl/iffr/" + str(year) + "/a-z"


def main():
    # Initialize globals.
    Globals.error_collector = app_tools.ErrorCollector()
    Globals.debug_recorder = app_tools.DebugRecorder(debug_file)

    # Initialize a festival data object.
    iffr_data: IffrData = IffrData(plandata_dir)

    # Try parsing the websites.
    write_film_list = False
    write_other_lists = True
    try:
        parse_iffr_sites(iffr_data)
    except KeyboardInterrupt:
        comment('Interrupted from keyboard... exiting')
        write_other_lists = False
    except Exception as e:
        Globals.debug_recorder.write_debug()
        comment('Debug info printed.')
        raise e
    else:
        write_film_list = True

    # Display error when found.
    if Globals.error_collector.error_count() > 0:
        comment('Encountered some errors:')
        print(Globals.error_collector)

    # Write parsed information.
    comment('Done laoding IFFR data.')
    write_lists(iffr_data, write_film_list, write_other_lists)
    Globals.debug_recorder.write_debug()


def parse_iffr_sites(iffr_data):
    comment('Parsing AZ pages.')
    get_films(iffr_data)

    comment('Parsing film pages.')
    get_film_details(iffr_data)


def comment(text):
    print(f"\n{datetime.datetime.now()}  - {text}")


def write_lists(iffr_data, write_film_list, write_other_lists):
    if write_film_list or write_other_lists:
        print("\n\nWRITING LISTS")

    if write_film_list:
        iffr_data.sort_films()
        iffr_data.write_films()
    else:
        print("Films NOT WRITTEN")

    if write_other_lists:
        iffr_data.write_filminfo()
        iffr_data.write_screens()
        iffr_data.write_screenings()
    else:
        print("Screens and screenings NOT WRITTEN")


def get_films(iffr_data):
    az_url = iffr_hostname + az_url_path
    url_file = web_tools.UrlFile(az_url, az_file, Globals.error_collector)
    az_html = url_file.get_text()
    if az_html is not None:
        AzPageParser(iffr_data).feed(az_html)


def get_film_details(iffr_data):
    for film in iffr_data.films:
        film_file = film_file_format.format(film.filmid)
        url_file = web_tools.UrlFile(film.url, film_file, Globals.error_collector, bytecount=60000)
        film_html = url_file.get_text(f'Downloading site of {film.title}: {film.url}')
        if film_html is not None:
            print(f'Analysing html file {film.filmid} of {film.title} {film.url}')
            ScreeningsPageParser(iffr_data, film).feed(film_html)
            FilmInfoPageParser(iffr_data, film).feed(film_html)
    apply_combinations(iffr_data)


def apply_combinations(iffr_data):
    def rep(film_id):
        film = iffr_data.get_film_from_id(film_id)
        return f'{film.title} ({film.duration_str()})'

    Globals.debug_recorder.add(f'\nMain films and extras: {Globals.extras_by_main}')
    for (main_film_id, extra_film_ids) in Globals.extras_by_main.items():
        Globals.debug_recorder.add(f'{rep(main_film_id)} [{" || ".join([rep(f) for f in extra_film_ids])}]')
        main_film = iffr_data.get_film_from_id(main_film_id)
        main_film_info = main_film.film_info(iffr_data)
        screened_films = []
        for extra_film_id in extra_film_ids:
            extra_film = iffr_data.get_film_from_id(extra_film_id)
            extra_film_info = extra_film.film_info(iffr_data)
            if len(extra_film_info.combination_urls) == 0:
                extra_film_info.combination_urls = [main_film.url]
            else:
                extra_film_info.combination_urls.append(main_film.url)
            screened_film = planner.ScreenedFilm(extra_film_id, extra_film.title, extra_film_info.description)
            screened_films.append(screened_film)
        main_film_info.screened_films = screened_films


class Globals:
    error_collector = None
    debug_recorder = None
    extras_by_main = {}


class HtmlPageParser(web_tools.HtmlPageParser):

    def __init__(self, iffr_data, debug_prefix):
        web_tools.HtmlPageParser.__init__(self, Globals.debug_recorder, debug_prefix)
        self.iffr_data = iffr_data
        self.debugging = False


class AzPageParser(HtmlPageParser):
    props_re = re.compile(
        r"""
            "bookings":\[[^]]*?\],"title":"(?P<title>[^"]+)"          # Title
            .*?"url\(\{\\"language\\":\\"nl\\"\}\)":"(?P<url>[^"]+)"  # URL
            ,"description\(\{.*?\}\)":"(?P<grid_desc>[^"]+)"          # Grid description
            ,"description\(\{.*?\}\)":"(?P<list_desc>[^"]+)"          # List description
            .*?"sortedTitle":"(?P<sorted_title>[^"]+)"                # Sorted Title
            (?:.*?"duration":(?P<duration>\d+)\})?                    # Duration
        """, re.VERBOSE)

    def __init__(self, iffr_data):
        HtmlPageParser.__init__(self, iffr_data, 'AZ')
        self.film = None
        self.duration = None
        self.sorted_title = None
        self.description = None
        self.url = None
        self.title = None
        self.debugging = False
        self.init_film_data()

    def parse_props(self, data):
        i = self.props_re.finditer(data)
        matches = [match for match in i]
        groups = [m.groupdict() for m in matches]
        for g in groups:
            self.title = g['title']
            self.url = iffr_hostname + web_tools.iripath_to_uripath(g['url'])
            self.description = g['list_desc']
            self.sorted_title = g['sorted_title'].lower()
            minutes_str = g['duration']
            minutes = 0 if minutes_str is None else int(minutes_str)
            self.duration = datetime.timedelta(minutes=minutes)
            self.add_film()

    def init_film_data(self):
        self.film = None
        self.title = None
        self.url = None
        self.duration = None
        self.description = None
        self.sorted_title = None

    def add_film(self):
        self.film = self.iffr_data.create_film(self.title, self.url)
        if self.film is None:
            Globals.error_collector.add(f'Could\'t create film from {self.title}', self.url)
        else:
            self.film.medium_category = self.url.split('/')[6]
            self.film.duration = self.duration
            self.film.sortstring = self.sorted_title
            print(f'Adding FILM: {self.title} ({self.film.duration_str()}) {self.film.medium_category}')
            self.iffr_data.films.append(self.film)
            self.add_film_info()

    def add_film_info(self):
        film_info = planner.FilmInfo(self.film.filmid, self.description, '')
        self.iffr_data.filminfos.append(film_info)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
        if data.startswith('{"props":'):
            self.parse_props(data.replace(r'\u0026', '&'))


class ScreeningsPageParser(HtmlPageParser):
    class ScreeningsParseState(Enum):
        AWAITING_OD = auto()
        IN_ON_DEMAND = auto()
        IN_OD_START_TIME = auto()
        BETWEEN_OD_TIMES = auto()
        IN_OD_END_TIME = auto()
        AFTER_ON_DEMAND = auto()
        AWAITING_S = auto()
        IN_SCREENINGS = auto()
        IN_S_TIMES = auto()
        IN_S_LOCATION = auto()
        IN_S_INFO = auto()
        AFTER_SCREENING = auto()
        DONE = auto()

    on_demand_location = "OnDemand"
    nl_month_by_name: Dict[str, int] = {'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6}

    def __init__(self, iffr_data, film):
        HtmlPageParser.__init__(self, iffr_data, "F")
        self.location = None
        self.start_date = None
        self.subtitles = None
        self.qa = None
        self.times = None
        self.end_dt = None
        self.start_dt = None
        self.audience = None
        self.screen = None
        self.film = film
        self.debugging = True
        self.print_debug(f"{40 * '-'} ", f"Analysing FILM {film}, {film.url}")

        self.init_screening_data()
        self.stateStack = self.StateStack(self.print_debug, self.ScreeningsParseState.AWAITING_OD)

    def init_screening_data(self):
        self.audience = 'publiek'
        self.qa = ''
        self.subtitles = ''
        self.location = None
        self.screen = None
        self.start_dt = None
        self.end_dt = None
        self.start_date = None
        self.times = None

    def add_on_demand_screening(self):
        self.screen = self.iffr_data.get_screen(city, self.on_demand_location)
        self.add_screening()

    def add_on_location_screening(self):
        self.screen = self.iffr_data.get_screen(city, self.location)
        self.add_screening()

    def add_screening(self):
        # Set some unwanted screenings to non-public.
        if self.film.title.startswith('GLR '):
            self.audience = 'GLR'
        elif self.film.title == 'Testing':
            self.audience = 'Testers'
        elif self.film.title == 'The Last Movie':
            self.audience = 'Crew'
        self.print_debug("--- ",
                         f"SCREEN={self.screen}, START TIME={self.start_dt}, END TIME={self.end_dt}, AUDIENCE={self.audience}")

        # Print the screening properties.
        if self.audience == 'publiek' and self.film.medium_category != 'events':
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
        extra = ''
        program = None
        screening = planner.Screening(self.film, self.screen, self.start_dt,
                                      self.end_dt, self.qa, extra,
                                      self.audience, program, self.subtitles)

        # Add the screening to the list.
        self.iffr_data.screenings.append(screening)
        print("---SCREENING ADDED")

        # Initialize the next round of parsing.
        self.init_screening_data()

    def parse_datetime(self, data):
        items = data.split()  # zaterdag 06 februari 13:00
        day = int(items[1])
        month = self.nl_month_by_name[items[2]]
        time = items[3].split(':')
        hours = int(time[0])
        minutes = int(time[1])
        return datetime.datetime(year, month, day, hours, minutes)

    def parse_date(self, data):
        items = data.split()  # woensdag 03 februari 2021
        day = int(items[1])
        month = self.nl_month_by_name[items[2]]
        year = int(items[3])
        return datetime.date(year, month, day)

    def set_screening_times(self, data):
        items = data.split()  # 13:00 - 15:26
        start_time = datetime.time.fromisoformat(items[0])
        end_time = datetime.time.fromisoformat(items[2])
        self.start_dt = datetime.datetime.combine(self.start_date, start_time)
        end_date = self.start_date if end_time > start_time else self.start_date + datetime.timedelta(days=1)
        self.end_dt = datetime.datetime.combine(end_date, end_time)

    def set_screening_info(self, data):
        self.print_debug('Found SCREENING info', data)
        if 'professionals' in data:
            self.audience = 'Industry'
        if 'Q&A' in data:
            self.qa = data
        if 'Ondertiteld' in data:
            self.subtitles = data

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        # Get data for screenings.
        if tag == 'h3' and len(attrs) > 0 and attrs[0][1] == 'typography__H3-sc-1jflaau-4 dNhFS':
            self.stateStack.change(self.ScreeningsParseState.DONE)
            self.update_film_info()
            self.print_debug('Done finding SCREENINGS', f'Attribute name: {attrs[0][0]}')
        if self.stateStack.state_is(self.ScreeningsParseState.IN_ON_DEMAND) and tag == 'span' and len(attrs) > 0:
            if attrs[0][1] == 'bookingtable-on-demand__date-value':
                self.stateStack.change(self.ScreeningsParseState.IN_OD_START_TIME)
        elif self.stateStack.state_is(self.ScreeningsParseState.BETWEEN_OD_TIMES) and tag == 'span':
            if attrs[0][1] == 'bookingtable-on-demand__date-value':
                self.stateStack.change(self.ScreeningsParseState.IN_OD_END_TIME)
        elif tag == 'div' and len(attrs) > 0:
            if attrs[0][1] == 'styles__FunctionalLabelWrapper-sc-12mea6v-0 iWNHmD':
                self.stateStack.push(self.ScreeningsParseState.IN_S_INFO)
            elif attrs[0] == ('class', 'bookingtable__date-wrapper'):
                if self.stateStack.state_is(self.ScreeningsParseState.AFTER_SCREENING):
                    self.add_on_location_screening()
                self.stateStack.change(self.ScreeningsParseState.IN_SCREENINGS)
        if self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'time':
            if attrs[0] == ('class', 'bookingtable__time'):
                self.stateStack.change(self.ScreeningsParseState.IN_S_TIMES)
                self.times = ''
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_S_TIMES) and tag == 'div':
            if attrs[0] == ('class', 'booking__table__location'):
                self.stateStack.change(self.ScreeningsParseState.IN_S_LOCATION)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        # Get data for screenings.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_S_TIMES) and tag == 'time':
            self.set_screening_times(self.times)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_ON_DEMAND) and tag == 'section':
            self.stateStack.change(self.ScreeningsParseState.AWAITING_S)
        elif self.stateStack.state_is(self.ScreeningsParseState.AFTER_SCREENING) and tag == 'section':
            self.add_on_location_screening()
            self.stateStack.change(self.ScreeningsParseState.DONE)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.stateStack.state_is(self.ScreeningsParseState.IN_OD_START_TIME):
            self.stateStack.change(self.ScreeningsParseState.BETWEEN_OD_TIMES)
            self.start_dt = self.parse_datetime(data)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_OD_END_TIME):
            self.stateStack.change(self.ScreeningsParseState.IN_ON_DEMAND)
            self.end_dt = self.parse_datetime(data)
            self.add_on_demand_screening()
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS):
            self.start_date = self.parse_date(data)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_S_TIMES):
            self.times += data
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_S_LOCATION):
            self.stateStack.change(self.ScreeningsParseState.AFTER_SCREENING)
            self.location = data
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_S_INFO):
            self.stateStack.pop()
            self.set_screening_info(data)


class FilmInfoPageParser(HtmlPageParser):
    class CombinationsParseState(Enum):
        IDLE = auto()
        IN_ARTICLE = auto()
        IN_PARAGRAPH = auto()
        IN_EMPHASIS = auto()
        IN_COMBINATION = auto()
        AWAITING_SCREENED_FILMS = auto()
        IN_SCREENED_FILMS = auto()
        IN_SCREENED_FILM = auto()
        FOUND_SCREENED_URL = auto()
        IN_SCREENED_TITLE = auto()
        AWAITING_SCREENED_DESCRIPTION = auto()
        IN_SCREENED_DESCRIPTION = auto()
        DONE = auto()

    def __init__(self, iffr_data, film):
        HtmlPageParser.__init__(self, iffr_data, 'CP')
        self.iffr_data = iffr_data
        self.film = film
        self.debugging = True
        self.article_paragraphs = []
        self.article_paragraph = ''
        self.article = None
        self.combination_urls = []
        self.screened_url = None
        self.screened_title = None
        self.screened_description = None
        self.screened_films = []
        self.stateStack = self.StateStack(self.print_debug, self.CombinationsParseState.IDLE)
        self.init_screened_film_data()

        # Get the film info of the current film. Its unique existence is guaranteed in AzPageParser.
        self.film_info = self.film.film_info(self.iffr_data)

    def init_screened_film_data(self):
        self.screened_url = None
        self.screened_title = None
        self.screened_description = None

    def add_screened_film(self):
        self.print_debug('Found screened film:', f'{self.screened_title}')
        try:
            film = self.iffr_data.get_film_by_key(self.screened_title, self.screened_url)
        except KeyError:
            Globals.error_collector.add('No screened URL found', f'{self.screened_title}')
        else:
            if film is not None:
                screened_film = planner.ScreenedFilm(film.filmid, self.screened_title, self.screened_description)
                self.screened_films.append(screened_film)
            else:
                Globals.error_collector.add(f"{self.screened_title} not found as film", self.screened_url)
        finally:
            self.init_screened_film_data()

    def add_paragraph(self):
        self.article_paragraphs.append(self.article_paragraph)
        self.article_paragraph = ''

    def set_article(self):
        self.article = '\n\n'.join(self.article_paragraphs)
        self.film_info.article = self.article

    def store_combination_from_title(self, combination_title):
        films = [f for f in self.iffr_data.films if f.title == combination_title]
        self.store_combination(films[0].filmid)

    def store_combination_from_url(self, url):
        combination_url = self.repair_url(url)
        combination_film = self.iffr_data.get_film_by_key(None, combination_url)
        self.store_combination(combination_film.filmid)

    def store_combination(self, combination_film_id):
        screened_film_id = self.film.filmid
        if combination_film_id in Globals.extras_by_main.keys():
            Globals.extras_by_main[combination_film_id].append(screened_film_id)
        else:
            Globals.extras_by_main[combination_film_id] = [screened_film_id]

    @staticmethod
    def repair_url(url):
        parts = url.split('/')
        if parts[4] != url_festival:
            parts.insert(4, az_url_path.split('/')[2])
            return '/'.join(parts)
        return url

    def set_screened_films(self):
        # Set the screened films list of the film info of the current film.
        self.film_info.screened_films = self.screened_films
        self.print_debug(
            f'SCREENED FILMS of {self.film.title} UPDATED', f'{len(self.screened_films)} screened films added.')
        self.print_debug(f'SCREENED FILMS LIST of {self.film} is now in info:', f'\n{self.film_info}')

        # Append the film being analysed to the combination programs of the screened films.
        for screened_film in self.screened_films:
            screened_film_infos = [i for i in self.iffr_data.filminfos if i.filmid == screened_film.filmid]
            screened_film_info = screened_film_infos[0]
            combination_urls = screened_film_info.combination_urls
            if len(combination_urls) == 0:
                combination_urls = [self.film.url]
            else:
                combination_urls.append(self.film.url)
            screened_film_info.combination_urls = combination_urls
            self.print_debug(f'COMBINATION PROGRAM INFO of {screened_film.title} UPDATED:',
                             f'\n{", ".join(u for u in combination_urls)}')

    def update_screenings(self):
        urls = self.film.film_info(self.iffr_data).combination_urls
        if len(urls) > 0:
            program = self.iffr_data.get_film_by_key(None, urls[0])
            screenings = [s for s in self.iffr_data.screenings if s.film.filmid == self.film.filmid]
            for screening in screenings:
                screening.combination_program = program

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.CombinationsParseState.IDLE) and tag == 'div' and len(attrs) > 0:
            if attrs[0][1] == '[object Object]':
                self.stateStack.push(self.CombinationsParseState.IN_ARTICLE)
        elif self.stateStack.state_is(self.CombinationsParseState.IN_ARTICLE) and tag == 'p':
            self.stateStack.push(self.CombinationsParseState.IN_PARAGRAPH)
        elif self.stateStack.state_is(self.CombinationsParseState.IN_PARAGRAPH) and tag == 'em':
            self.stateStack.push(self.CombinationsParseState.IN_EMPHASIS)
        elif self.stateStack.state_is(self.CombinationsParseState.IN_COMBINATION) and tag == 'a' and len(attrs) > 0:
            if attrs[0][0] == 'href':
                self.store_combination_from_url(attrs[0][1])
        elif self.stateStack.state_is(self.CombinationsParseState.IDLE) and tag == 'h3' and len(attrs) > 0:
            if attrs[0][0] == 'class' and attrs[0][1] == 'sc-crzoAE hwJoPF':
                self.stateStack.change(self.CombinationsParseState.AWAITING_SCREENED_FILMS)
        elif self.stateStack.state_is(self.CombinationsParseState.IN_SCREENED_FILMS) and tag == 'article':
            self.stateStack.push(self.CombinationsParseState.IN_SCREENED_FILM)
        elif self.stateStack.state_is(self.CombinationsParseState.IN_SCREENED_FILM) and tag == 'a' and len(attrs) > 1:
            if attrs[1][0] == 'href':
                self.screened_url = f'{iffr_hostname}{attrs[1][1]}'
                self.stateStack.push(self.CombinationsParseState.FOUND_SCREENED_URL)
        elif self.stateStack.state_is(self.CombinationsParseState.FOUND_SCREENED_URL) and tag == 'h4':
            if attrs[0][1].endswith('tile__title'):
                self.stateStack.change(self.CombinationsParseState.IN_SCREENED_TITLE)
        elif self.stateStack.state_is(self.CombinationsParseState.AWAITING_SCREENED_DESCRIPTION) and tag == 'p':
            self.stateStack.change(self.CombinationsParseState.IN_SCREENED_DESCRIPTION)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.stateStack.state_in([self.CombinationsParseState.IN_EMPHASIS,
                                     self.CombinationsParseState.IN_COMBINATION]) and tag == 'em':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.CombinationsParseState.IN_PARAGRAPH) and tag == 'p':
            self.stateStack.pop()
            self.add_paragraph()
        elif self.stateStack.state_is(self.CombinationsParseState.IN_ARTICLE) and tag == 'div':
            self.stateStack.pop()
            self.set_article()
        elif self.stateStack.state_is(self.CombinationsParseState.IN_SCREENED_FILM) and tag == 'article':
            self.stateStack.pop()
            self.add_screened_film()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.stateStack.state_is(self.CombinationsParseState.IN_EMPHASIS):
            prefixes = ['Voorfilm bij ', 'Te zien na ']
            for prefix in prefixes:
                if data.startswith(prefix):
                    if data == prefix:
                        self.stateStack.change(self.CombinationsParseState.IN_COMBINATION)
                    else:
                        self.store_combination_from_title(data.removeprefix(prefix))
        if self.stateStack.state_in([self.CombinationsParseState.IN_PARAGRAPH,
                                     self.CombinationsParseState.IN_EMPHASIS,
                                     self.CombinationsParseState.IN_COMBINATION]):
            self.article_paragraph += data.replace('\n', ' ')
        elif self.stateStack.state_is(self.CombinationsParseState.AWAITING_SCREENED_FILMS):
            if data == 'In dit verzamelprogramma':
                self.stateStack.change(self.CombinationsParseState.IN_SCREENED_FILMS)
            else:
                self.stateStack.change(self.CombinationsParseState.DONE)
        elif self.stateStack.state_is(self.CombinationsParseState.IN_SCREENED_FILMS):
            if data.startswith('Programma IFFR'):
                self.stateStack.change(self.CombinationsParseState.DONE)
                self.set_screened_films()
                self.update_screenings()
        elif self.stateStack.state_is(self.CombinationsParseState.IN_SCREENED_TITLE):
            self.stateStack.change(self.CombinationsParseState.AWAITING_SCREENED_DESCRIPTION)
            self.screened_title = data
        elif self.stateStack.state_is(self.CombinationsParseState.IN_SCREENED_DESCRIPTION):
            self.stateStack.pop()
            self.screened_description = data


class IffrData(planner.FestivalData):

    def _init__(self, planner_data_dir):
        planner.FestivalData.__init__(self, planner_data_dir)

    def _filmkey(self, film, url):
        return url

    def film_can_go_to_planner(self, filmid):
        return True


if __name__ == "__main__":
    main()
