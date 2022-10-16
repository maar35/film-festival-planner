#!/usr/bin/env python3

import os
import sys
import datetime
import urllib.request
import urllib.error
from enum import Enum, auto
from typing import Dict

import Shared.planner_interface as planner
import Shared.application_tools as app_tools
from Shared.parse_tools import HtmlPageParser
from Shared.web_tools import iripath_to_uripath, UrlFile, UrlReader

# Parameters.
festival = 'MTMF'
festival_year = 2022
home_city = 'Den Haag'
on_demand_start_dt = datetime.datetime.fromisoformat('2022-04-08 12:00:00')
on_demand_end_dt = datetime.datetime.fromisoformat('2022-04-16 23:59:00')

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
        comment(f'Encountered {Globals.error_collector.error_count()} error(s):')
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
        get_one_film(iri, festival_data)

    comment('Applying combinations')
    FilmPageParser.apply_combinations(festival_data)


def get_one_film(iri, festival_data):
    # Get the URL from the IRI.
    iri_path = iri[len(mtmf_hostname):]
    url = mtmf_hostname + iripath_to_uripath(iri_path)

    # Load the film HTML.
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
        url_file = UrlFile(url, film_file, Globals.error_collector)
        try:
            film_html = url_file.get_text(f'Downloading site {url}')
        except urllib.error.HTTPError:
            print(f'\nWeb site {url} of {festival_data.get_film_by_id(film_id)} not found.\n')

    # Parse the HTML.
    if film_html is not None:
        print(f'\nAnalysing downloaded film HTML from URL {url}')
        film_parser = FilmPageParser(url, festival_data)
        film_parser.feed(film_html)
        ScreeningsPageParser(festival_data, film_parser.film, film_parser.subtitles).feed(film_html)


def load_url(url, encoding='utf-8'):
    reader = UrlReader(Globals.error_collector)
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
        festival_data.write_screens()
        festival_data.write_screenings()
    else:
        print("Screens and screenings NOT WRITTEN")


class Globals:
    error_collector = None
    debug_recorder = None
    mtmf_urls = []
    combination_urls_by_film_id = {}
    screened_film_urls_by_film_id = {}


class FilmPageParser(HtmlPageParser):
    class FilmsParseState(Enum):
        IDLE = auto()
        IN_TITLE = auto()
        IN_ARTICLE = auto()
        IN_PARAGRAPH = auto()
        IN_EMPHASIS = auto()
        IN_COMBINATION = auto()
        IN_SCREENED_FILMS = auto()
        IN_PROPERTIES = auto()
        IN_LABEL = auto()
        AWAITING_VALUE = auto()
        IN_VALUE = auto()
        DONE = auto()

    category_by_branch = dict(film='films')
    debugging = False

    def __init__(self, url, festival_data, encoding=None):
        HtmlPageParser.__init__(self, festival_data, Globals.debug_recorder, 'F', encoding)
        self.url = url
        self.festival_data = festival_data
        self.print_debug(self.bar, f'Analysing URL {url}')
        self.film = None
        self.title = None
        self.description = None
        self.subtitles = None
        self.article_paragraphs = []
        self.article_paragraph = ''
        self.article = None
        self.combination_urls = []
        self.screened_film_urls = []
        self.label = None
        self.stateStack = self.StateStack(self.print_debug, self.FilmsParseState.IDLE)
        self.film_property_by_label = {}

    def add_paragraph(self):
        self.article_paragraphs.append(self.article_paragraph)
        self.article_paragraph = ''

    def set_article(self):
        self.article = '\n\n'.join(self.article_paragraphs)

    def add_combination_url(self, url):
        self.combination_urls.append(url)

    def add_screened_film_url(self, url):
        self.screened_film_urls.append(url)

    def add_film(self):
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            Globals.error_collector.add(f"Couldn't create film from {self.title}", self.url)
        else:
            self.film.medium_category = self.category_by_branch[self.url.split('/')[4]]
            self.film.duration = datetime.timedelta(minutes=int(self.film_property_by_label['Duur'].split()[0]))
            print(f'Adding FILM: {self.title} ({self.film.duration_str()}) {self.film.medium_category}')
            self.festival_data.films.append(self.film)
            self.add_film_info()
            self.set_global_film_properties()

    def add_film_info(self):
        print(f'Description:\n{self.description}')
        film_info = planner.FilmInfo(self.film.filmid, self.description, self.article)
        self.festival_data.filminfos.append(film_info)

    def set_global_film_properties(self):
        # Store the combinations urls for the current film.
        if len(self.combination_urls) > 0:
            Globals.combination_urls_by_film_id[self.film.filmid] = self.combination_urls

        # Store the screened film urls for the current film.
        if len(self.screened_film_urls) > 0:
            Globals.screened_film_urls_by_film_id[self.film.filmid] = self.screened_film_urls

        # Set the subtitles for use in the Screenings parser.
        try:
            self.subtitles = self.film_property_by_label['Ondertiteling']
        except KeyError:
            self.subtitles = ''
        if self.subtitles == 'Geen':
            self.subtitles = ''

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if tag == 'meta' and len(attrs) >1:
            if attrs[0][1] == 'og:description':
                self.description = attrs[1][1]
        elif tag == 'h1' and len(attrs) > 0 and attrs[0][1] == 'film-detail__title heading--small':
            self.stateStack.change(self.FilmsParseState.IN_TITLE)
        elif self.stateStack.state_is(self.FilmsParseState.IDLE) and tag == 'div' and len(attrs) > 0:
            if attrs[0][1] == 'film-detail__the-content the-content':
                self.stateStack.push(self.FilmsParseState.IN_ARTICLE)
        elif self.stateStack.state_is(self.FilmsParseState.IN_ARTICLE) and tag == 'p':
            self.stateStack.push(self.FilmsParseState.IN_PARAGRAPH)
        elif self.stateStack.state_is(self.FilmsParseState.IN_PARAGRAPH) and tag == 'em':
            self.stateStack.push(self.FilmsParseState.IN_EMPHASIS)
        elif self.stateStack.state_is(self.FilmsParseState.IN_COMBINATION) and tag == 'a' and len(attrs) > 0:
            if attrs[0][0] == 'href':
                self.add_combination_url(attrs[0][1])
                self.stateStack.pop()
        elif self.stateStack.state_is(self.FilmsParseState.IN_ARTICLE) and tag == 'ul':
            self.stateStack.push(self.FilmsParseState.IN_SCREENED_FILMS)
        elif self.stateStack.state_is(self.FilmsParseState.IN_SCREENED_FILMS) and tag == 'a' and len(attrs) > 0:
            if attrs[0][0] == 'href':
                self.add_screened_film_url(attrs[0][1])
        elif tag == 'dl' and len(attrs) > 0 and attrs[0][1] == 'data-list data-list--details':
            self.stateStack.change(self.FilmsParseState.IN_PROPERTIES)
        elif self.stateStack.state_is(self.FilmsParseState.IN_PROPERTIES) and tag == 'span':
            if len(attrs) == 1 and attrs[0][1] == 'data-list__label':
                self.stateStack.push(self.FilmsParseState.IN_LABEL)
        elif self.stateStack.state_is(self.FilmsParseState.AWAITING_VALUE) and tag == 'dd':
            self.stateStack.change(self.FilmsParseState.IN_VALUE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.stateStack.state_is(self.FilmsParseState.IN_PARAGRAPH) and tag == 'p':
            self.stateStack.pop()
            self.add_paragraph()
        elif self.stateStack.state_is(self.FilmsParseState.IN_EMPHASIS) and tag == 'em':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.FilmsParseState.IN_COMBINATION) and tag == 'em':
            self.stateStack.pop()
            self.stateStack.pop()
            self.stateStack.push(self.FilmsParseState.IN_COMBINATION)
        elif self.stateStack.state_is(self.FilmsParseState.IN_SCREENED_FILMS) and tag == 'ul':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.FilmsParseState.IN_ARTICLE) and tag == 'div':
            self.stateStack.pop()
            self.set_article()
        elif self.stateStack.state_is(self.FilmsParseState.IN_PROPERTIES) and tag == 'dl':
            self.stateStack.change(self.FilmsParseState.DONE)
            self.add_film()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.stateStack.state_is(self.FilmsParseState.IN_TITLE):
            self.title = data.strip()
            self.stateStack.change(self.FilmsParseState.IDLE)
        elif self.stateStack.state_in([self.FilmsParseState.IN_PARAGRAPH, self.FilmsParseState.IN_EMPHASIS]):
            self.article_paragraph += data.replace('\n', ' ')
            if data.strip() == 'Deze korte film maakt deel uit van het programma':
                self.stateStack.push(self.FilmsParseState.IN_COMBINATION)
        elif self.stateStack.state_is(self.FilmsParseState.IN_LABEL):
            self.label = data
            self.stateStack.change(self.FilmsParseState.AWAITING_VALUE)
        elif self.stateStack.state_is(self.FilmsParseState.IN_VALUE):
            self.film_property_by_label[self.label] = data
            self.stateStack.pop()

    @staticmethod
    def apply_combinations(festival_data):
        # Add combination programs to film info.
        print(f'{len(Globals.combination_urls_by_film_id)} screened films found.')
        for (film_id, combination_urls) in Globals.combination_urls_by_film_id.items():
            screened_film = festival_data.get_film_by_id(film_id)
            screened_film_info = screened_film.film_info(festival_data)
            combination_films = []
            for combination_url in combination_urls:
                try:
                    combination_film = festival_data.get_film_by_key(None, combination_url)
                except KeyError as err:
                    Globals.error_collector.add(f'Key error {err} for {screened_film}', 'Unknown combination URL')
                else:
                    combination_films.append(combination_film)
            screened_film_info.combination_films = combination_films

        # Add screened films to film info.
        print(f'{len(Globals.screened_film_urls_by_film_id)} combination films found.')
        for (film_id, screened_film_urls) in Globals.screened_film_urls_by_film_id.items():
            combination_film = festival_data.get_film_by_id(film_id)
            combination_film_info = combination_film.film_info(festival_data)
            screened_films = []
            for url in screened_film_urls:
                try:
                    film = festival_data.get_film_by_key(None, url)
                except KeyError as err:
                    Globals.error_collector.add(f'Key error {err} for {combination_film}', 'Unknown screened film URL')
                else:
                    film_info = film.film_info(festival_data)
                    screened_film = planner.ScreenedFilm(film.filmid, film.title, film_info.description)
                    screened_films.append(screened_film)
            combination_film_info.screened_films = screened_films


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

    debugging = False
    nl_month_by_name: Dict[str, int] = {'apr': 4}

    def __init__(self, iffr_data, film, subtitles):
        HtmlPageParser.__init__(self, iffr_data, Globals.debug_recorder, "S")
        self.film = film
        self.subtitles = subtitles
        self.print_debug(self.bar, f"Analysing FILM {film}, {film.url}")
        self.screening_nr = 0
        self.screen_name = None
        self.start_date = None
        self.qa = None
        self.end_dt = None
        self.start_dt = None
        self.extra = None
        self.audience = None
        self.screen = None

        self.init_screening_data()
        self.stateStack = self.StateStack(self.print_debug, self.ScreeningsParseState.IDLE)

    def init_screening_data(self):
        self.audience = 'publiek'
        self.extra = ''
        self.qa = ''
        self.screen_name = None
        self.screen = None
        self.start_dt = None
        self.end_dt = None

    def add_on_demand_screening(self):
        self.screen = self.festival_data.get_screen(home_city, 'On Demand')
        self.start_dt = on_demand_start_dt
        self.end_dt = on_demand_end_dt
        self.add_screening_if_possible()

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
        url_file = UrlFile(url, locations_file, Globals.error_collector)
        try:
            locations_html = url_file.get_text(f'Downloading shopping cart site {url}')
        except ValueError:
            pass
        else:
            if locations_html is not None:
                shopping_cart_parser = ShoppingCartPageParser(self.festival_data, self.film, screening_nr, url)
                shopping_cart_parser.feed(locations_html)
                self.screen_name = shopping_cart_parser.current_screen

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.ScreeningsParseState.IDLE) and tag == 'div' and len(attrs) > 0:
            if attrs[0][1] == 'film-detail__viewings tile-side':
                self.stateStack.change(self.ScreeningsParseState.IN_SCREENINGS)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'div' and len(attrs) > 0:
            if attrs[0][1] == 'tile-date':
                self.stateStack.push(self.ScreeningsParseState.IN_DATE)
            elif attrs[0][1].startswith('tile-time  '):
                self.stateStack.push(self.ScreeningsParseState.AFTER_DATE)
            elif attrs[0][1] == 'tile-date vod':
                self.add_on_demand_screening()
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
        HtmlPageParser.__init__(self, festival_data, Globals.debug_recorder, 'SC')
        self.film = film
        self.sequence_nr = sequence_nr
        self.print_debug(self.bar, f'Analysing shopping cart #{sequence_nr} of FILM {film}, {url}')
        self.current_screen = None

    def get_theater_screen(self, url):
        details_file = details_file_format.format(self.film.filmid, self.sequence_nr)
        url_file = UrlFile(url, details_file, Globals.error_collector)
        try:
            details_html = url_file.get_text(f'Downloading site {url}')
        except ValueError:
            pass
        else:
            if details_html is not None:
                theater_screen_parser = TheaterScreenPageParser(self.festival_data, self.film, url)
                theater_screen_parser.feed(details_html)
                self.current_screen = theater_screen_parser.current_screen

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if tag == 'iframe' and len(attrs) > 4 and attrs[0][1] == 'order__iframe order__iframe--crossmarx':
            details_url = attrs[4][1]
            self.get_theater_screen(details_url)


class TheaterScreenPageParser(HtmlPageParser):
    class ScreensParseState(Enum):
        IDLE = auto()
        IN_SCREENING_LOCATION = auto()
        DONE = auto()

    debugging = False

    def __init__(self, festival_data, film, url):
        HtmlPageParser.__init__(self, festival_data, Globals.debug_recorder, 'TS')
        self.print_debug(self.bar, f'Analysing screening details of FILM {film}, {url}')
        self.stateStack = self.StateStack(self.print_debug, self.ScreensParseState.IDLE)
        self.current_screen = None

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.ScreensParseState.IDLE) and tag == 'div' and len(attrs) > 0:
            if attrs[0][1] == 'at-show-property at-show-location':
                self.stateStack.change(self.ScreensParseState.IN_SCREENING_LOCATION)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.stateStack.state_is(self.ScreensParseState.IN_SCREENING_LOCATION):
            self.current_screen = data.strip()
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
