#!/usr/bin/env python3

import os
import sys
import datetime
import urllib.request
import urllib.error
from enum import Enum, auto
from typing import Dict

shared_dir = os.path.expanduser("~/Projects/FilmFestivalPlanner/FilmFestivalLoader/Shared")
sys.path.insert(0, shared_dir)
import planner_interface as planner
import application_tools as app_tools
import web_tools

# Parameters.
festival = 'MTMF'
festival_year = 2022
home_city = 'Den Haag'

# Preferences.
always_read_web = False

# Directories.
documents_dir = os.path.expanduser("~/Documents/Film/{0}/{0}{1}".format(festival, festival_year))
webdata_dir = os.path.join(documents_dir, "_website_data")
plandata_dir = os.path.join(documents_dir, "_planner_data")

# Filename formats.
film_file_format = os.path.join(webdata_dir, "filmpage_{:03d}.html")
screenings_file_format = os.path.join(webdata_dir, "screenings_{:03d}_{:02d}.html")
details_file_format = os.path.join(webdata_dir, "details_{:03d}_{:02d}.html")

# Files.
az_urls_file = os.path.join(plandata_dir, 'urls.txt')
debug_file = os.path.join(plandata_dir, 'debug.txt')

# URL information.
mtmf_hostname = 'https://moviesthatmatter.nl'
url_festival = mtmf_hostname.split('/')[2].split('.')[0]


def main():
    # Initialize globals.
    Globals.error_collector = app_tools.ErrorCollector()
    Globals.debug_recorder = app_tools.DebugRecorder(debug_file)

    # Initialize a festival data object.
    mtmf_data: MtmfData = MtmfData(plandata_dir)

    # Try parsing the websites.
    write_film_list = False
    write_other_lists = True
    try:
        parse_festival_sites(mtmf_data)
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
    comment(f'Done loading {festival} data.')
    write_lists(mtmf_data, write_film_list, write_other_lists)
    Globals.debug_recorder.write_debug()


def parse_festival_sites(festival_data):
    # Make sure the web- and data-directories exist.
    if not os.path.isdir(webdata_dir):
        os.mkdir(webdata_dir)
    if not os.path.isdir(plandata_dir):
        os.mkdir(plandata_dir)

    # Get the films.
    comment('Getting URL\'s.')
    get_films(festival_data)


def get_films(festival_data):
    # Read the manually selected URL's.
    with open(az_urls_file, 'r') as f:
        for iri in f.readlines():
            Globals.mtmf_urls.append(iri.strip('\n'))
    count = len(Globals.mtmf_urls)
    print(f'{count} URL\'s read.')

    # Get basic film data from the URL's.
    for iri in Globals.mtmf_urls:
        iri_path = iri[len(mtmf_hostname):]
        url = mtmf_hostname + web_tools.iripath_to_uripath(iri_path)
        film_html = None
        try:
            film_id = festival_data.film_id_by_url[url]
        except KeyError:
            try:
                film_html = load_url(url)
            except urllib.error.HTTPError as error:
                print(f'\nError {error} while loading {url}.\n')
                Globals.error_collector.add(error, f'while loading {url}')
        else:
            film_file = film_file_format.format(film_id)
            url_file = web_tools.UrlFile(url, film_file, Globals.error_collector)
            try:
                film_html = url_file.get_text(f'Downloading site {url}')
            except urllib.error.HTTPError:
                print(f'\nWeb site {url} of {festival_data.get_film_from_id(film_id)} not found.\n')
        if film_html is not None:
            print(f'\nAnalysing downloaded film HTML from URL {url}')
            FilmPageParser(url, festival_data).feed(film_html)
            ScreeningsPageParser(festival_data, Globals.current_film).feed(film_html)


def load_url(url, encoding='utf-8'):
    reader = web_tools.UrlReader(Globals.error_collector)
    request = reader.get_request(url)
    with urllib.request.urlopen(request) as response:
        html_bytes = response.read()
    return html_bytes.decode(encoding=encoding)


def comment(text):
    print(f"\n{datetime.datetime.now()}  - {text}")


def write_lists(festival_data, write_film_list, write_other_lists):
    if write_film_list or write_other_lists:
        print("\n\nWRITING LISTS")

    if write_film_list:
        festival_data.write_films()
    else:
        print("Films NOT WRITTEN")

    if write_other_lists:
        festival_data.write_filminfo()
        festival_data.write_sections()
        festival_data.write_subsections()
        festival_data.write_screens()
        festival_data.write_screenings()
    else:
        print("Screens and screenings NOT WRITTEN")


class Globals:
    error_collector = None
    debug_recorder = None
    mtmf_urls = []
    current_film = None
    current_screen = None
    extras_by_main = {}


class HtmlPageParser(web_tools.HtmlPageParser):
    debugging = False

    def __init__(self, festival_data, debug_prefix, encoding=None):
        web_tools.HtmlPageParser.__init__(self, Globals.debug_recorder, debug_prefix)
        self.festival_data = festival_data
        if encoding is not None:
            self.print_debug(f'Encoding: {encoding}', '')


class FilmPageParser(HtmlPageParser):
    class FilmsParseState(Enum):
        IDLE = auto()
        IN_TITLE = auto()
        IN_PROPERTIES = auto()
        IN_LABEL = auto()
        AWAITING_VALUE = auto()
        IN_VALUE = auto()
        DONE = auto()

    category_by_branch = dict(film='films')
    debugging = True

    def __init__(self, url, festival_data, encoding=None):
        HtmlPageParser.__init__(self, festival_data, 'F', encoding)
        self.url = url
        self.festival_data = festival_data
        Globals.current_film = None
        self.print_debug(f"{40 * '-'} ", f'Analysing URL {url}')
        self.film = None
        self.title = None
        self.description = None
        self.label = None
        self.section_name = None
        self.subsection_name = None
        self.subsection_url = None
        self.stateStack = self.StateStack(self.print_debug, self.FilmsParseState.IDLE)
        self.film_property_by_label = {}

    def add_film(self):
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            Globals.error_collector.add(f'Could\'t create film from {self.title}', self.url)
        else:
            self.film.medium_category = self.category_by_branch[self.url.split('/')[4]]
            minutes_str = self.film_property_by_label['Duur']
            self.film.duration = datetime.timedelta(minutes=int(minutes_str.split()[0]))
            print(f'Adding FILM: {self.title} ({self.film.duration_str()}) {self.film.medium_category}')
            self.festival_data.films.append(self.film)
            self.add_film_info()
            Globals.current_film = self.film

    def add_film_info(self):
        print(f'Description:\n{self.description}')
        film_info = planner.FilmInfo(self.film.filmid, self.description, '')
        self.festival_data.filminfos.append(film_info)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if tag == 'meta' and len(attrs) >1:
            if attrs[0][1] == 'og:description':
                self.description = attrs[1][1]
        elif tag == 'h1' and len(attrs) > 0:
            if attrs[0][1] == 'film-detail__title heading--small':
                self.stateStack.change(self.FilmsParseState.IN_TITLE)
        elif tag == 'dl' and len(attrs) > 0 and attrs[0][1] == 'data-list data-list--details':
            self.stateStack.change(self.FilmsParseState.IN_PROPERTIES)
        elif self.stateStack.state_is(self.FilmsParseState.IN_PROPERTIES) and tag == 'span':
            if len(attrs) == 1 and attrs[0][1] == 'data-list__label':
                self.stateStack.push(self.FilmsParseState.IN_LABEL)
        elif self.stateStack.state_is(self.FilmsParseState.AWAITING_VALUE) and tag == 'dd':
            self.stateStack.change(self.FilmsParseState.IN_VALUE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.stateStack.state_is(self.FilmsParseState.IN_PROPERTIES) and tag == 'dl':
            self.stateStack.change(self.FilmsParseState.DONE)
            self.add_film()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.stateStack.state_is(self.FilmsParseState.IN_TITLE):
            self.title = data.strip()
            self.stateStack.change(self.FilmsParseState.IDLE)
        elif self.stateStack.state_is(self.FilmsParseState.IN_LABEL):
            self.label = data
            self.stateStack.change(self.FilmsParseState.AWAITING_VALUE)
        elif self.stateStack.state_is(self.FilmsParseState.IN_VALUE):
            self.film_property_by_label[self.label] = data
            self.stateStack.pop()


class ScreeningsPageParser(HtmlPageParser):
    class ScreeningsParseState(Enum):
        IDLE = auto()
        IN_SCREENINGS = auto()
        IN_DATE = auto()
        AFTER_DATE = auto()
        IN_TIMES = auto()
        AFTER_TIMES = auto()
        IN_LOCATION = auto()
        AFTER_LOCATION = auto()
        IN_LABEL = auto()
        DONE = auto()

    debugging = True
    nl_month_by_name: Dict[str, int] = {'apr': 4}

    def __init__(self, iffr_data, film):
        HtmlPageParser.__init__(self, iffr_data, "S")
        self.film = film
        self.screening_nr = 0
        self.screen_name = None
        self.start_date = None
        self.subtitles = None
        self.qa = None
        self.times = None
        self.end_dt = None
        self.start_dt = None
        self.extra = None
        self.audience = None
        self.screen = None
        self.print_debug(f"{40 * '-'} ", f"Analysing FILM {film}, {film.url}")

        self.init_screening_data()
        self.stateStack = self.StateStack(self.print_debug, self.ScreeningsParseState.IDLE)

    def init_screening_data(self):
        self.audience = 'publiek'
        self.extra = ''
        self.qa = ''
        self.subtitles = ''
        self.screen_name = None
        self.screen = None
        self.start_dt = None
        self.end_dt = None

    def add_screening_if_possible(self):
        if self.screen is not None:
            self.add_screening()
        else:
            self.init_screening_data()
            print(f'No screening added.')
            Globals.error_collector.add('Screening has no screen', f'Film {self.film}')

    def add_screening(self):
        self.print_debug(
            '--- ',
            f'SCREEN={self.screen}, START TIME={self.start_dt}, END TIME={self.end_dt}, AUDIENCE={self.audience}')

        # Print the screening properties.
        if self.audience == 'publiek' and self.film.medium_category != 'events':
            print()
            print(f"---SCREENING {self.screening_nr} OF {self.film.title}")
            print(f"--  screen:     {self.screen}")
            print(f"--  start time: {self.start_dt}")
            print(f"--  end time:   {self.end_dt}")
            print(f"--  duration:   film: {self.film.duration_str()}  screening: {self.end_dt - self.start_dt}")
            print(f"--  audience:   {self.audience}")
            print(f"--  category:   {self.film.medium_category}")
            print(f"--  q and a:    {self.qa}")
            print(f"--  extra:      {self.extra}")
            print(f"--  subtitles:  {self.subtitles}")

        # Create a new screening object.
        program = None
        screening = planner.Screening(self.film, self.screen, self.start_dt,
                                      self.end_dt, self.qa, self.extra,
                                      self.audience, program, self.subtitles)

        # Add the screening to the list.
        self.festival_data.screenings.append(screening)
        print("---SCREENING ADDED")

        # Initialize the next round of parsing.
        self.init_screening_data()

    def parse_date(self, data):
        items = data.split()  # zo 10 apr
        day = int(items[1])
        month = self.nl_month_by_name[items[2]]
        year = festival_year
        return datetime.date(year, month, day)

    def parse_label(self, data):
        if data == 'Invitation only':
            self.audience = 'genodigden'

    def set_screening_times(self, data):
        items = data.split()  # 10:15  - 11:48
        start_time = datetime.time.fromisoformat(items[0])
        end_time = datetime.time.fromisoformat(items[2])
        self.start_dt = datetime.datetime.combine(self.start_date, start_time)
        end_date = self.start_date if end_time > start_time else self.start_date + datetime.timedelta(days=1)
        self.end_dt = datetime.datetime.combine(end_date, end_time)

    def set_screen(self, data):
        items = data.split(',')    # Den Haag, Filmhuis Den Haag
        city = items[0]
        theater = items[1].strip()
        screen_name = self.screen_name if self.screen_name is not None else theater
        if screen_name is not None:
            self.screen = self.festival_data.get_screen(city, screen_name)
        else:
            self.print_debug('NO THEATER', f'city={city}, theater={theater}, screen={screen_name}')
        if city != home_city:
            self.print_debug('OTHER CITY', f'city={city}, theater={theater}, screen={self.screen}')

    def read_screen(self, url, film_id, screening_nr):
        locations_file = screenings_file_format.format(film_id, screening_nr)
        url_file = web_tools.UrlFile(url, locations_file, Globals.error_collector)
        try:
            locations_html = url_file.get_text(f'Downloading shop[p[ing cart site {url}')
        except ValueError:
            pass
        else:
            if locations_html is not None:
                ShoppingCartPageParser(self.festival_data, self.film, screening_nr, url).feed(locations_html)
                self.screen_name = Globals.current_screen
                Globals.current_screen = None

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.ScreeningsParseState.IDLE) and tag == 'div' and len(attrs) > 0:
            if attrs[0][1] == 'film-detail__viewings tile-side':
                self.stateStack.change(self.ScreeningsParseState.IN_SCREENINGS)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'div' and len(attrs) > 0:
            if attrs[0][1] == 'tile-date':
                self.stateStack.push(self.ScreeningsParseState.IN_DATE)
            elif attrs[0][1].startswith('tile-time'):
                self.stateStack.push(self.ScreeningsParseState.AFTER_DATE)
        elif self.stateStack.state_is(self.ScreeningsParseState.AFTER_DATE) and tag == 'a' and len(attrs) > 1:
            if attrs[0][1] == 'time':
                self.screening_nr += 1
                self.read_screen(attrs[1][1], self.film.filmid, self.screening_nr)
                self.stateStack.change(self.ScreeningsParseState.IN_TIMES)
        elif self.stateStack.state_is(self.ScreeningsParseState.AFTER_TIMES) and tag == 'p' and len(attrs) > 0:
            if attrs[0][1] == 'location':
                self.stateStack.change(self.ScreeningsParseState.IN_LOCATION)
        elif self.stateStack.state_is(self.ScreeningsParseState.AFTER_LOCATION) and tag == 'span' and len(attrs) > 0:
            if attrs[0][1] == 'label label__verdieping':
                self.qa = 'met verdieping'
            elif attrs[0][1] == 'label':
                self.stateStack.push(self.ScreeningsParseState.IN_LABEL)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'script' and len(attrs) > 0:
            if attrs[0][1] == 'application/json':
                self.stateStack.change(self.ScreeningsParseState.DONE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.stateStack.state_is(self.ScreeningsParseState.AFTER_LOCATION) and tag == 'div':
            self.add_screening_if_possible()
            self.stateStack.pop()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.stateStack.state_is(self.ScreeningsParseState.IN_DATE):
            self.start_date = self.parse_date(data)
            self.stateStack.change(self.ScreeningsParseState.AFTER_DATE)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_TIMES):
            self.set_screening_times(data)
            self.stateStack.change(self.ScreeningsParseState.AFTER_TIMES)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_LOCATION):
            self.set_screen(data)
            self.stateStack.change(self.ScreeningsParseState.AFTER_LOCATION)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_LABEL):
            self.parse_label(data)
            self.stateStack.pop()


class ShoppingCartPageParser(HtmlPageParser):
    debugging = False

    def __init__(self, festival_data, film, sequence_nr, url):
        HtmlPageParser.__init__(self, festival_data, 'SC')
        self.film = film
        self.sequence_nr = sequence_nr
        self.url = url
        self.print_debug(f"{40 * '-'} ", f'Analysing shopping cart #{sequence_nr} of FILM {film}, {url}')

    def get_theater_screens(self, url):
        details_file = details_file_format.format(self.film.filmid, self.sequence_nr)
        url_file = web_tools.UrlFile(url, details_file, Globals.error_collector)
        try:
            details_html = url_file.get_text(f'Downloading site {url}')
        except ValueError:
            pass
        else:
            if details_html is not None:
                TheaterScreenPageParser(self.festival_data, self.film, url).feed(details_html)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if tag == 'iframe' and len(attrs) > 4 and attrs[0][1] == 'order__iframe order__iframe--crossmarx':
            details_url = attrs[4][1]
            self.get_theater_screens(details_url)


class TheaterScreenPageParser(HtmlPageParser):
    class ScreensParseState(Enum):
        IDLE = auto()
        IN_SCREENING_LOCATION = auto()
        DONE = auto()

    debugging = True

    def __init__(self, festival_data, film, url):
        HtmlPageParser.__init__(self, festival_data, 'TS')
        self.print_debug(f"{40 * '-'} ", f'Analysing screening details of FILM {film}, {url}')
        self.stateStack = self.StateStack(self.print_debug, self.ScreensParseState.IDLE)
        Globals.current_screen = None

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.ScreensParseState.IDLE) and tag == 'div' and len(attrs) > 0:
            if attrs[0][1] == 'at-show-property at-show-location':
                self.stateStack.change(self.ScreensParseState.IN_SCREENING_LOCATION)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.stateStack.state_is(self.ScreensParseState.IN_SCREENING_LOCATION):
            Globals.current_screen = data.strip()
            self.stateStack.change(self.ScreensParseState.DONE)


class MtmfData(planner.FestivalData):

    def _init__(self, planner_data_dir):
        planner.FestivalData.__init__(self, planner_data_dir)

    def _filmkey(self, film, url):
        return url

    def film_can_go_to_planner(self, film_id):
        return True

    def screening_can_go_to_planner(self, screening):
        can_go = planner.FestivalData.screening_can_go_to_planner(self, screening)
        return can_go and screening.screen.city == home_city


if __name__ == "__main__":
    main()
