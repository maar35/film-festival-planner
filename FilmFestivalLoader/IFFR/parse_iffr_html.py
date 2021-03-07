#!/Users/maarten/opt/anaconda3/bin/python3

import os
import sys
import re
import datetime
from enum import Enum, auto

shared_dir = os.path.expanduser("~/Projects/FilmFestivalPlanner/FilmFestivalLoader/Shared")
sys.path.insert(0, shared_dir)
import planner_interface as planner
import application_tools as app_tools
import web_tools

# Parameters.
festival = 'IFFR'
year = 2021
city = 'Rotterdam'

# Directories:
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
az_url_path = "/nl/programma/" + str(year) + "/a-z"


def main():
    # Initialize globals.
    Globals.error_collector = app_tools.ErrorCollector()
    Globals.debug_recorder = app_tools.DebugRecorder(debug_file)

    # Initialize a festival data object.
    iffr_data = IffrData(plandata_dir)

    # Try parsing the web sites.
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
    films_loader = FilmsLoader()
    films_loader.get_films(iffr_data)

    comment('Parsing film pages.')
    film_detals_loader = FilmDetailsLoader()
    film_detals_loader.get_film_details(iffr_data)


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


class Globals:
    error_collector = None
    debug_recorder = None


class FilmsLoader:

    def get_films(self, iffr_data):
        if os.path.isfile(az_file):
            charset = web_tools.get_charset(az_file)
            with open(az_file, 'r', encoding=charset) as f:
                az_html = f.read()
        else:
            az_url = iffr_hostname + az_url_path
            az_html = web_tools.UrlReader(Globals.error_collector).load_url(az_url, az_file)
        if az_html is not None:
            AzPageParser(iffr_data).feed(az_html)


class FilmDetailsLoader:

    def __init__(self):
        pass

    def get_film_details(self, iffr_data):
        for film in iffr_data.films:
            html_data = None
            film_file = film_file_format.format(film.filmid)
            if os.path.isfile(film_file):
                charset = web_tools.get_charset(film_file)
                with open(film_file, 'r', encoding=charset) as f:
                    html_data = f.read()
            else:
                print(f"Downloading site of {film.title}: {film.url}")
                html_data = web_tools.UrlReader(Globals.error_collector).load_url(film.url, film_file)
            if html_data is not None:
                print(f"Analysing html file {film.filmid} of {film.title} {film.url}")
                FilmPageParser(iffr_data, film).feed(html_data)


class HtmlPageParser(web_tools.HtmlPageParser):

    def __init__(self, iffr_data, debug_prefix):
        web_tools.HtmlPageParser.__init__(self, Globals.debug_recorder, debug_prefix)
        self.iffr_data = iffr_data
        self.debugging = False

    def attr_str(self, attr, index):
        return (str)(attr[index])


class AzPageParser(HtmlPageParser):

    props_re = re.compile(
        r"""
            "bookings":\[[^]]*?\],"title":"(?P<title>[^"]+)           # Title
            .*?"url\(\{\\"language\\":\\"nl\\"\}\)":"(?P<url>[^"]+)"  # URL
            ,"description\(\{.*?\}\)":"(?P<grid_desc>[^"]+)"          # Grid description
            ,"description\(\{.*?\}\)":"(?P<list_desc>[^"]+)"          # List description
            .*?"sortedTitle":"(?P<sorted_title>[^"]+)"                # Sorted Title
            (?:.*?"duration":(?P<duration>\d+)\})?                    # Duration
        """, re.VERBOSE)

    def __init__(self, iffr_data):
        HtmlPageParser.__init__(self, iffr_data, 'AZ')
        self.matching_attr_value = ""
        self.debugging = False
        self.init_film_data()

    def parse_props(self, data):
        for g in [m.groupdict() for m in self.props_re.finditer(data)]:
            self.title = g['title']
            self.url = iffr_hostname + web_tools.iripath_to_uripath(g['url'])
            self.description = g['list_desc']
            self.sorted_title = g['sorted_title'].lower()
            minutes_str = g['duration']
            minutes = 0 if minutes_str is None else int(minutes_str)
            self.duration = datetime.timedelta(minutes=minutes)
            self.add_film()
            if self.film is not None:
                self.add_filminfo()

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
            self.film.medium_category = self.url.split('/')[5]
            self.film.duration = self.duration
            self.film.sortstring = self.sorted_title
            print(f'Adding FILM: {self.title} ({self.film.duration_str()}) {self.film.medium_category}')
            self.iffr_data.films.append(self.film)

    def add_filminfo(self):
        filminfo = planner.FilmInfo(self.film.filmid, self.description, '')
        self.iffr_data.filminfos.append(filminfo)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
        if data.startswith('{"props":'):
            self.parse_props(data)


class FilmPageParser(HtmlPageParser):

    class ScreeningsParseState(Enum):
        AWAITING_OD = auto()
        IN_ON_DEMAND = auto()
        IN_OD_STARTTIME = auto()
        BETWEEN_OD_TIMES = auto()
        IN_OD_ENDTIME = auto()
        AFTER_ON_DEMAND = auto()
        AWAITING_S = auto()
        IN_SCREENINGS = auto()
        IN_S_TIMES = auto()
        IN_S_LOCATION = auto()
        IN_S_INFO = auto()
        AFTER_SCREENING = auto()
        DONE = auto()

    class StateStack:

        def __init__(self, print_debug, state):
            self.print_debug = print_debug
            self.stack = [state]

        def push(self, state):
            self.stack.append(state)
            self.print_debug(f'Screenings parsing state after PUSH is {state}', '')

        def pop(self):
            self.stack[-1:] = []
            self.print_debug(f'Screenings parsing state after POP is {self.stack[-1]}', '')

        def change(self, state):
            self.stack[-1] = state
            self.print_debug(f'Entered a new SCREENING STATE {state}', '')

        def state_is(self, state):
            return state == self.stack[-1]

    on_demand_location = "OnDemand"
    nl_month_by_name = {}
    nl_month_by_name['januari'] = 1
    nl_month_by_name['februari'] = 2

    def __init__(self, iffr_data, film):
        HtmlPageParser.__init__(self, iffr_data, "F")
        self.film = film
        self.debugging = False
        self.article_paragraphs = []
        self.paragraph = None
        self.article = None
        self.combination_urls = []
        self.await_article = False
        self.in_article = False
        self.await_paragraph = False
        self.in_paragraph = False
        self.print_debug(f"{40 * '-'} ", f"Analysing FILM {film}, {film.url}")

        self.init_screened_film_data()
        self.screened_films = []
        self.in_screened_films = False

        self.init_screening_data()
        self.stateStack = self.StateStack(self.print_debug, self.ScreeningsParseState.AWAITING_OD)

    def init_screened_film_data(self):
        self.screened_url = None
        self.screened_title = None
        self.screened_description = None
        self.in_screened_film = False
        self.in_screened_url = False
        self.in_screened_title = False
        self.await_screened_description = False
        self.in_screened_description = False

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

    def create_article(self):
        if len(self.article) == 0:
            self.article = '\n\n'.join(self.article_paragraphs)
        self.print_debug(f"Found ARTICLE of {self.film.title}:", self.article)

    def add_screened_film(self):
        print(f'Found screened film: {self.screened_title}')
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

    def update_filminfo(self):
        filminfos = [filminfo for filminfo in self.iffr_data.filminfos if filminfo.filmid == self.film.filmid]
        if len(filminfos) == 1:
            filminfo = filminfos[0]
            if self.article is not None and len(self.article) > 0:
                filminfo.article = self.article
            elif self.article is None:
                Globals().error_collector.add('Article is None', f'{self.film} {self.film.duration_str()}')
                filminfo.article = ''
            else:
                Globals().error_collector.add('Article is empty string', f'{self.film} {self.film.duration_str()}')
                filminfo.article = ''
            filminfo.combination_urls = self.combination_urls
            filminfo.screened_films = self.screened_films
            self.print_debug(f'FILMINFO of {self.film.title} updated', f'ARTICLE: {filminfo.article}')
        else:
            filminfo = planner.FilmInfo(self.film.filmid, '', self.article, self.screened_films)
            self.iffr_data.filminfos.append(filminfo)
            Globals.error_collector.add(f'No unique FILMINFO found for {self.film}', f'{len(filminfos)} linked filminfo records')

    def update_screenings(self):
        urls = self.film.film_info(self.iffr_data).combination_urls
        if len(urls) > 0:
            program = self.iffr_data.get_film_by_key(None, urls[0])
            screenings = [s for s in self.iffr_data.screenings if s.film.filmid == self.film.filmid]
            for screening in screenings:
                screening.combination_program = program
            if self.audience == 'publiek':
                print(f'--  combination:{program}')
                print("---SCREENINGS UPDATED")
                print()

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
        self.print_debug("--- ", f"SCREEN={self.screen}, START TIME={self.start_dt}, END TIME={self.end_dt}, AUDIENCE={self.audience}")

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

        # Get data for film info.
        if tag == 'a' and len(attrs) > 0:
            attr = attrs[0]
            if attr[0] == 'href':
                combine_attr = f'/nl/{year}/events/'
                if attr[1].startswith(combine_attr):
                    url_path = web_tools.iripath_to_uripath(attr[1])
                    combination_url = f'{iffr_hostname}{url_path}'
                    print(f'Part of COMBINATION: {combination_url}')
                    self.print_debug('Found COMBINATION url', combination_url)
                    self.combination_urls.append(combination_url)
        if self.await_article and tag == 'div' and len(attrs) > 0:
            if attrs[0] == ('class', 'grid__Grid-enb6co-0 ejdVvQ'):
                self.await_article = False
                self.in_article = True
                self.await_paragraph = True
                self.article = ''
                self.print_debug('Entering ARTICLE section', f'{self.film.title}')
        elif self.await_paragraph and tag == 'p':
            self.await_paragraph = False
            self.in_paragraph = True
            self.paragraph = ''
        elif self.await_screened_description and tag == 'p':
            self.await_screened_description = False
            self.in_screened_description = True
        elif not self.in_screened_films and tag == 'h3' and len(attrs) > 0:
            attr = attrs[0]
            if attr == ('class', 'typography__H3-sc-1jflaau-4 eqGgqi'):
                if self.film.medium_category != 'films':
                    self.in_screened_films = True
                    self.print_debug('Entering SCREENED FILMS section', f'{self.film.title}')
        elif self.in_screened_films and tag == 'article':
            self.in_screened_film = True
        elif self.in_screened_film and tag == 'a' and len(attrs) > 0:
            attr = attrs[0]
            if attr[0] == 'href':
                url_path = web_tools.iripath_to_uripath(attr[1])
                self.screened_url = f'{iffr_hostname}{url_path}'
        elif self.in_screened_film and tag == 'h4':
            self.in_screened_title = True
        if tag == 'h3' and len(attrs) > 0 and attrs[0][1] == 'typography__H3-sc-1jflaau-4 dNhFS':
            if self.in_screened_films:
                self.print_debug('Leaving SCREENED FILMS section', f'{self.film.title}')
            self.in_screened_films = False
            self.in_screened_film = False
            self.stateStack.change(self.ScreeningsParseState.DONE)
            self.print_debug('Done finding SREENINGS', f'Attribute name: {attrs[0][0]}')
            self.update_filminfo()
            self.update_screenings()

        # Get data for screenings.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_ON_DEMAND) and tag == 'span':
            if attrs[0][1] == 'bookingtable-on-demand__date-value':
                self.stateStack.change(self.ScreeningsParseState.IN_OD_STARTTIME)
        elif self.stateStack.state_is(self.ScreeningsParseState.BETWEEN_OD_TIMES) and tag == 'span':
            if attrs[0][1] == 'bookingtable-on-demand__date-value':
                self.stateStack.change(self.ScreeningsParseState.IN_OD_ENDTIME)
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

        # Get data for film info.
        if self.in_screened_film and tag == 'article':
            self.in_screened_film = False
        elif self.in_paragraph and tag == 'p':
            self.in_paragraph = False
            self.await_paragraph = True
            self.article_paragraphs.append(self.paragraph)
            self.paragraph = ''
        elif self.in_article and tag == 'div':
            self.in_article = False
            self.await_paragraph = False
            self.print_debug('Leaving ARTICLE section', f'{self.film.title}')
            self.stateStack.change(self.ScreeningsParseState.IN_ON_DEMAND)
            self.create_article()

        # Get data for screenings.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_S_TIMES) and tag == 'time':
            self.set_screening_times(self.times)
        elif self.stateStack.state_is(self.ScreeningsParseState.AFTER_ON_DEMAND) and tag == 'section':
            self.add_on_demand_screening()
            self.stateStack.change(self.ScreeningsParseState.AWAITING_S)
        elif self.stateStack.state_is(self.ScreeningsParseState.AFTER_SCREENING) and tag == 'section':
            self.add_on_location_screening()
            self.stateStack.change(self.ScreeningsParseState.DONE)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        # Get data for film info.
        if data == 'Toevoegen aan favorieten' or data == 'Add to favourites':
            self.await_article = True
        if self.in_paragraph:
            self.paragraph += data.replace('\n', ' ')
        elif self.in_article:
            self.article += data.replace('\n', ' ')
        elif self.in_screened_title:
            self.in_screened_title = False
            self.await_screened_description = True
            self.screened_title = data
        elif self.in_screened_description:
            self.in_screened_description = False
            self.screened_description = data
            self.add_screened_film()

        # Get data for screenings.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_OD_STARTTIME):
            self.stateStack.change(self.ScreeningsParseState.BETWEEN_OD_TIMES)
            self.start_dt = self.parse_datetime(data)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_OD_ENDTIME):
            self.stateStack.change(self.ScreeningsParseState.AFTER_ON_DEMAND)
            self.end_dt = self.parse_datetime(data)
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


class IffrData(planner.FestivalData):

    def _init__(self, plandata_dir):
        planner.FestivalData.__init__(self, plandata_dir)

    def _filmkey(self, film, url):
        return url


if __name__ == "__main__":
    main()
