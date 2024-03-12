#!/usr/bin/env python3
import csv
import datetime
import os
import re
from enum import Enum, auto
from typing import Dict

from Shared.application_tools import ErrorCollector, DebugRecorder, Counter, comment
from Shared.parse_tools import HtmlPageParser, FileKeeper, try_parse_festival_sites
from Shared.planner_interface import FilmInfo, ScreenedFilm, FestivalData
from Shared.web_tools import UrlFile, UrlReader, iri_slug_to_url, get_netloc

ALWAYS_DOWNLOAD = False
DEBUGGING = True
DISPLAY_ADDED_SCREENING = False
ONLY_PARSE_SCREENED_FILMS = True

FESTIVAL = 'MTMF'
FESTIVAL_YEAR = 2024
FESTIVAL_CITY = 'Den Haag'

SHORT_COMBOS = 'Short combinations'
SHORTS = 'Shorts'

# Files.
file_keeper = FileKeeper(FESTIVAL, FESTIVAL_YEAR)

# URL information.
mtmf_hostname = 'https://moviesthatmatter.nl'
mtmf_tickets_hostname = 'https://tickets.moviesthatmatter.nl'

# Application tools.
error_collector = ErrorCollector()
debug_recorder = DebugRecorder(file_keeper.debug_file)
counter = Counter()


def main():
    # Initialize a festival data object.
    festival_data = MtmfData(file_keeper.plandata_dir)

    # Set up counters.
    counter.start('themes')
    counter.start('competitions')
    counter.start('specials')
    counter.start('films')
    counter.start('duplicates')
    counter.start('screenings')
    counter.start('not in dh')
    counter.start('sold out')
    counter.start('screen not recovered')
    counter.start('no theater')
    counter.start('combination films')
    counter.start('combinations parsed')
    counter.start('combinations')
    counter.start('screened films')
    counter.start('screen not found')
    counter.start('screen fixed')

    # Try parsing the websites.
    try_parse_festival_sites(parse_mtmf_sites, festival_data, error_collector, debug_recorder, FESTIVAL, counter)


def parse_mtmf_sites(festival_data):
    # Set up a film url finder.
    url_finder = FilmUrlFinder(festival_data)

    # Read film urls from the section sites.
    comment(f"Find film URL's from the festival section sites")
    url_finder.read_sections()

    # Get the films.
    comment('Get films by URL.')
    get_films(festival_data, url_finder.charset_by_film_url)

    # Link combination programs and screened films.
    comment('Apply combination data')
    FilmPageParser.apply_combinations(festival_data)


def get_films(festival_data, charset_by_film_url):
    for film_url, charset in charset_by_film_url.items():
        get_film_by_url(festival_data, film_url, charset)


def get_film_by_url(festival_data, url, charset):
    # Try if the film to be read already has a number.
    try:
        film_id = festival_data.film_id_by_url[url]
    except KeyError:
        get_film_from_url(festival_data, url, charset)
    else:
        film = festival_data.get_film_by_id(film_id)
        if film is None:
            film_file = file_keeper.film_webdata_file(film_id)
            url_file = UrlFile(url, film_file, error_collector, debug_recorder, byte_count=500)
            comment_at_download = f'Downloading film site: {url}, encoding: {url_file.encoding}'
            film_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=f'{comment_at_download}')
            if film_html is not None:
                print(f'Analysing html file {film_id} of {url}')
                film_parser = FilmPageParser(festival_data, url)
                film_parser.feed(film_html)
                ScreeningsPageParser(festival_data, film_parser.film, film_parser.subtitles).feed(film_html)


def get_film_from_url(festival_data, url, encoding):
    # Get the html data form the url.
    print(f'Requesting film page {url}, encoding={encoding}')
    reader = UrlReader(error_collector)
    film_parser = FilmPageParser(festival_data, url)
    film_html = reader.load_url(url, None, encoding)
    print(f'Analysing film program data from {url}')
    film_parser.feed(film_html)

    # Write the gotten html to file.
    try:
        film_id = festival_data.film_id_by_url[url]
    except KeyError as e:
        error_collector.add(e, 'No film id found with this URL')
    else:
        film_file = file_keeper.film_webdata_file(film_id)
        print(f'Writing film html {festival_data.get_film_by_id(film_id).title} to {film_file}')
        html_bytes = film_html.encode(encoding=encoding)
        with open(film_file, 'wb') as f:
            f.write(html_bytes)


class FilmUrlFinder:
    re_segment_str = r'/[^/#"]*/'
    re_films = re.compile(r'https://moviesthatmatter.nl/festival/film/[^/]*/')
    main_sections = {
        'themas': {'singular': 'theme', 'plural': 'themes'},
        'competities': {'singular': 'competition', 'plural': 'competitions'},
        'specials': {'singular': 'special', 'plural': 'specials'},
    }
    color_by_section_name = {
        'themas': 'DodgerBlue',
        'competities': 'Red',
        'specials': 'LimeGreen',
    }
    charset_by_film_url = {}
    subsection_by_film_url = {}

    def __init__(self, festival_data):
        self.festival_data = festival_data
        self.section_urls = None
        self.re_by_section = {section: self.re_section(section) for section in self.main_sections.keys()}
        for section_dict in self.main_sections.values():
            counter.start(section_dict['plural'])

    def __str__(self):
        return '\n'.join(self.charset_by_film_url)

    @staticmethod
    def section_base(section):
        return iri_slug_to_url(mtmf_hostname, f'festival/{section}')

    def re_section(self, section):
        return re.compile(self.section_base(section) + self.re_segment_str)

    def read_sections(self):
        for section_name in self.main_sections.keys():
            self.read_main_section(section_name)

    def read_main_section(self, section_name):
        section_url = self.section_base(section_name)
        section_file = os.path.join(file_keeper.webdata_dir, f'{section_name}.html')
        section = self.festival_data.get_section(section_name, self.color_by_section_name[section_name])
        url_file = UrlFile(section_url, section_file, error_collector, debug_recorder)
        section_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD)
        if section_html is not None:
            subsection_urls = self.re_by_section[section_name].findall(section_html)
            comment(f'{len(subsection_urls)} {section_name} subsection urls found.')
            sep = '\n'
            print(f'{sep.join(subsection_urls)}')
            for i, subsection_url in enumerate(subsection_urls):
                counter.increase(self.main_sections[section_name]['plural'])
                subsection = self.get_subsection(section, subsection_url)
                self.get_film_urls(subsection, self.main_sections[section_name]['singular'], i)

    def get_film_urls(self, subsection, prefix, subsection_index):
        subsection_file = file_keeper.numbered_webdata_file(f'section_{prefix}', subsection_index)
        subsection_url = subsection.url
        url_file = UrlFile(subsection_url, subsection_file, error_collector, debug_recorder, byte_count=500)
        subsection_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD)
        if subsection_html is not None:
            print(f'Getting film urls from {subsection_file}, encoding={url_file.encoding}')
            film_count = 0
            for m in self.re_films.finditer(subsection_html):
                film_url = m.group()
                if film_url in self.charset_by_film_url:
                    counter.increase('duplicates')
                else:
                    film_count += 1
                    counter.increase('films')
                    self.charset_by_film_url[film_url] = url_file.encoding
                    self.subsection_by_film_url[film_url] = subsection
            print(f'{film_count} films in {subsection.section.name}: {subsection.name}')

    def get_subsection(self, section, url):
        lower_name = url.split('/')[-2].replace('-', ' ')
        try:
            subsection_name = lower_name[0].upper() + lower_name[1:]
        except IndexError as e:
            error_collector.add(e, f'{url=}')
            subsection = None
        else:
            if section.name == 'themas' and subsection_name == SHORTS:
                subsection_name = SHORT_COMBOS
            subsection = self.festival_data.get_subsection(subsection_name, url, section)
        return subsection


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
    combination_urls_by_film_id = {}
    screened_film_urls_by_film_id = {}

    def __init__(self, festival_data, url):
        HtmlPageParser.__init__(self, festival_data, debug_recorder, 'F', debugging=DEBUGGING)
        self.url = url
        self.festival_data = festival_data
        self.print_debug(self.bar, f'Analysing film URL {url}')
        self.film = None
        self.title = None
        self.subtitles = None
        self.combination_urls = []
        self.screened_film_urls = []
        self.film_info = None
        self.label = None
        self.state_stack = self.StateStack(self.print_debug, self.FilmsParseState.IDLE)
        self.film_property_by_label = {}

    def add_combination_url(self, url):
        self.combination_urls.append(url)

    def add_screened_film_url(self, url):
        self.screened_film_urls.append(url)

    def add_properties_to_article(self):
        properties_text = '\n'.join([f'{k}: {v}' for k, v in self.film_property_by_label.items()])
        self.article += '\n\nFilm properties\n' + properties_text

    def get_duration(self):
        try:
            minutes = int(self.film_property_by_label['Duur'].split()[0])
        except KeyError:
            minutes = 0
        return datetime.timedelta(minutes=minutes)

    def add_film(self):
        if self.title is None:
            error_collector.add('Cannot create a film without a title', self.url)
            return
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            error_collector.add(f"Couldn't create film from {self.title}", self.url)
        else:
            self.film.medium_category = self.category_by_branch[self.url.split('/')[4]]
            self.film.duration = self.get_duration()
            self.film.subsection = FilmUrlFinder.subsection_by_film_url[self.url]
            print(f'Adding FILM: {self.title} ({self.film.duration_str()}) {self.film.medium_category}')
            self.festival_data.films.append(self.film)
            self.add_film_info()
            self.set_global_film_properties()

    def add_film_info(self):
        self.set_description_from_article(self.film.title)
        print(f'Description:\n{self.description}')
        self.film_info = FilmInfo(self.film.filmid, self.description, self.article)
        self.festival_data.filminfos.append(self.film_info)

    def set_global_film_properties(self):
        # Store the combinations urls for the current film.
        combinations_count = len(self.combination_urls)
        if combinations_count > 0:
            if ONLY_PARSE_SCREENED_FILMS:
                self.combination_urls_by_film_id[self.film.filmid] = self.combination_urls
            counter.increase('combination films', increment=combinations_count)

        # Link the screened film urls to the current film.
        screened_films_count = len(self.screened_film_urls)
        if screened_films_count > 0:
            self.screened_film_urls_by_film_id[self.film.filmid] = self.screened_film_urls
            for url in self.screened_film_urls:
                subsection_name = SHORTS if self.film.subsection.name == SHORT_COMBOS else self.film.subsection.name
                subsection = self.festival_data.subsection_by_name[subsection_name]
                FilmUrlFinder.subsection_by_film_url[url] = subsection
                get_film_by_url(self.festival_data, url, 'utf-8')
            counter.increase('combinations')
            counter.increase('screened films', increment=screened_films_count)

        # Set the subtitles for use in the Screenings parser.
        try:
            self.subtitles = self.film_property_by_label['Ondertiteling']
        except KeyError:
            self.subtitles = ''
        if self.subtitles == 'Geen':
            self.subtitles = ''

    def finish_parsing(self):
        self.add_properties_to_article()
        self.add_film()

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if tag == 'title':
            self.state_stack.change(self.FilmsParseState.IN_TITLE)
        elif self.state_stack.state_is(self.FilmsParseState.IDLE):
            if tag == 'div' and len(attrs) > 0:
                if attrs[0][1] == 'film-detail__the-content the-content':
                    self.state_stack.push(self.FilmsParseState.IN_ARTICLE)
            elif tag == 'dl' and len(attrs) > 0 and attrs[0][1] == 'data-list data-list--details':
                self.state_stack.change(self.FilmsParseState.IN_PROPERTIES)
            elif tag == 'footer':
                self.state_stack.change(self.FilmsParseState.DONE)
                self.finish_parsing()
        elif self.state_stack.state_is(self.FilmsParseState.IN_ARTICLE) and tag == 'p':
            self.state_stack.push(self.FilmsParseState.IN_PARAGRAPH)
        elif self.state_stack.state_is(self.FilmsParseState.IN_PARAGRAPH):
            if tag == 'em':
                self.state_stack.push(self.FilmsParseState.IN_EMPHASIS)
            elif tag == 'br':
                self.add_paragraph()
        elif self.state_stack.state_is(self.FilmsParseState.IN_COMBINATION) and tag == 'a' and len(attrs) > 0:
            if attrs[0][0] == 'href':
                self.add_combination_url(attrs[0][1])
                self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmsParseState.IN_ARTICLE) and tag == 'ul':
            self.state_stack.push(self.FilmsParseState.IN_SCREENED_FILMS)
        elif self.state_stack.state_is(self.FilmsParseState.IN_SCREENED_FILMS) and tag == 'a' and len(attrs) > 0:
            if attrs[0][0] == 'href':
                self.add_screened_film_url(attrs[0][1])
        elif self.state_stack.state_is(self.FilmsParseState.IN_PROPERTIES) and tag == 'dt':
            self.state_stack.push(self.FilmsParseState.IN_LABEL)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_VALUE) and tag == 'dd':
            self.state_stack.change(self.FilmsParseState.IN_VALUE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_is(self.FilmsParseState.IN_PARAGRAPH) and tag == 'p':
            self.state_stack.pop()
            self.add_paragraph()
        elif self.state_stack.state_is(self.FilmsParseState.IN_EMPHASIS) and tag == 'em':
            self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmsParseState.IN_COMBINATION) and tag == 'em':
            self.state_stack.pop()
            self.state_stack.pop()
            self.state_stack.push(self.FilmsParseState.IN_COMBINATION)
        elif self.state_stack.state_is(self.FilmsParseState.IN_SCREENED_FILMS) and tag == 'ul':
            self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmsParseState.IN_ARTICLE) and tag == 'div':
            self.state_stack.pop()
            self.set_article()
        elif self.state_stack.state_is(self.FilmsParseState.IN_PROPERTIES) and tag == 'dl':
            self.state_stack.change(self.FilmsParseState.DONE)
            self.finish_parsing()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.FilmsParseState.IN_TITLE):
            self.title = data.strip()
            unwanted_end = ' – Movies that Matter'
            if self.title.endswith(unwanted_end):
                self.title = self.title[:-len(unwanted_end)]
            self.state_stack.change(self.FilmsParseState.IDLE)
        elif self.state_stack.state_in([self.FilmsParseState.IN_PARAGRAPH, self.FilmsParseState.IN_EMPHASIS]):
            self.article_paragraph += data.replace('\n', ' ')
            if data.strip() == 'Deze korte film maakt deel uit van het programma':
                self.state_stack.push(self.FilmsParseState.IN_COMBINATION)
        elif self.state_stack.state_is(self.FilmsParseState.IN_LABEL):
            self.label = data
            self.state_stack.change(self.FilmsParseState.AWAITING_VALUE)
        elif self.state_stack.state_is(self.FilmsParseState.IN_VALUE):
            self.film_property_by_label[self.label] = data
            self.state_stack.pop()

    @staticmethod
    def apply_combinations(festival_data):
        # Link the screened films to their combination programs.
        for (film_id, combination_urls) in FilmPageParser.combination_urls_by_film_id.items():
            # Find the combination programs of the current film.
            film = festival_data.get_film_by_id(film_id)
            screened_film_info = film.film_info(festival_data)
            combination_films = []
            for combination_url in combination_urls:
                try:
                    combination_film = festival_data.get_film_by_key(None, combination_url)
                except KeyError as e:
                    error_collector.add(f'Key error {e} for screened {film}', 'Unknown combination URL')
                else:
                    # Add combination program to the list.
                    combination_films.append(combination_film)

                    # Add the current screened film to the combination.
                    screened_film = ScreenedFilm(film.filmid, film.title, screened_film_info.description)
                    combination_film_info = combination_film.film_info(festival_data)
                    combination_film_info.screened_films.append(screened_film)

            # Set the combination programs of the screened film.
            unique_combinations = set(screened_film_info.combination_films) and set(combination_films)
            screened_film_info.combination_films = list(unique_combinations)

        # Link the combination programs to their screened films.
        for (film_id, screened_film_urls) in FilmPageParser.screened_film_urls_by_film_id.items():
            combination_film = festival_data.get_film_by_id(film_id)

            # Find screenings with theater instead of screen.
            combination_film_screenings_no_screen = []
            for s in combination_film.screenings(festival_data):
                if s.screen.name == s.screen.theater.name:
                    combination_film_screenings_no_screen.append(s)
                    counter.increase('screen not found')

            # Find the screened films of the current combination.
            screened_films = []
            for screened_film_url in screened_film_urls:
                try:
                    film = festival_data.get_film_by_key(None, screened_film_url)
                except KeyError as e:
                    error_collector.add(f'Key error {e} for {combination_film}', 'Unknown screened film URL')
                except ValueError as e:
                    error_collector.add(f'Value error {e}', f'Combination film {combination_film}')
                else:
                    # Add screened film to the list.
                    film_info = film.film_info(festival_data)
                    screened_film = ScreenedFilm(film.filmid, film.title, film_info.description)
                    screened_films.append(screened_film)

                    # Add the current combination to screened film.
                    film_info.combination_films.append(combination_film)

                    # Fix missing screens in the current combination
                    # from the screened film screenings.
                    for cs in combination_film_screenings_no_screen:
                        for s in film.screenings(festival_data):
                            if cs.start_datetime == s.start_datetime:
                                if cs.screen.name != s.screen.name:
                                    if cs.screen.name == cs.screen.theater.name:
                                        cs.screen = s.screen
                                        counter.increase('screen fixed')
                                        debug_recorder.add(f'FIXED SCREEN {cs.screen} from {s}')

            # Set the screened films of the combination program.
            combination_film_info = combination_film.film_info(festival_data)
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

    nl_month_by_name: Dict[str, int] = {'mrt': 3, 'apr': 4}

    def __init__(self, iffr_data, film, subtitles):
        HtmlPageParser.__init__(self, iffr_data, debug_recorder, 'S', debugging=DEBUGGING)
        self.film = film
        self.subtitles = subtitles
        self.print_debug(self.bar, f"Analysing screenings of {film}, {film.url}")
        self.screening_nr = 0
        self.screen_name = None
        self.start_date = None
        self.qa = None
        self.end_dt = None
        self.start_dt = None
        self.extra = None
        self.audience = None
        self.screen = None
        self.sold_out = None

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
        self.sold_out = False

    def add_screening_if_possible(self):
        if self.screen is not None:
            self.add_mtmf_screening()
        else:
            print(f'No screening added.')
            error_collector.add('Screening has no screen', f'Film {self.film}')
            self.init_screening_data()

    def add_mtmf_screening(self):
        # Maintain statistics.
        counter.increase('screenings')
        if self.screen.theater.city.name != FESTIVAL_CITY:
            counter.increase('not in dh')

        # Add a screening based on the parsed data.
        self.add_screening_from_fields(self.film, self.screen, self.start_dt, self.end_dt, self.qa,
                                       self.subtitles, self.extra, self.audience,
                                       sold_out=self.sold_out, display=DISPLAY_ADDED_SCREENING)

        # Initialize the next round of parsing.
        self.init_screening_data()

    def parse_date(self, data):
        items = data.split()  # zo 10 apr
        day = int(items[1])
        month = self.nl_month_by_name[items[2]]
        year = FESTIVAL_YEAR
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
        city = items[0] or FESTIVAL_CITY
        theater = items[1].strip()
        if self.sold_out:
            counter.increase('sold out')
            self.screen = self.get_screen_from_file()
            if not self.screen:
                error_collector.add('Screen not recovered', f'{city=}, {theater=}, {self.start_dt.isoformat(sep=" ")}')
                counter.increase('screen not recovered')
        else:
            screen_name = self.screen_name if self.screen_name is not None else theater
            if screen_name is not None:
                self.screen = self.festival_data.get_screen(city, screen_name, theater)
            else:
                self.print_debug('NO THEATER', f'city={city}, theater={theater}, screen={screen_name}')
                counter.increase('no theater')
        if city != FESTIVAL_CITY:
            self.print_debug('OTHER CITY', f'city={city}, theater={theater}, screen={self.screen}')

    def get_screen_from_file(self):
        film_id_field = 0
        screen_id_field = 1
        start_time_field = 2
        screenings_filename = os.path.basename(self.festival_data.screenings_file)
        screenings_path = os.path.join(file_keeper.interface_dir, screenings_filename)
        screen_id = None
        with open(screenings_path, newline='') as csvfile:
            screenings_reader = csv.reader(csvfile, delimiter=';', quotechar='"')
            next(screenings_reader)     # Skip header.
            for row in screenings_reader:
                film_id = int(row[film_id_field])
                start_date_str = row[start_time_field]
                if film_id == self.film.filmid and start_date_str == self.start_dt.isoformat(sep=' '):
                    screen_id = int(row[screen_id_field])
                    break
        screen = self.festival_data.get_screen_by_id(screen_id)
        return screen

    def read_screen_if_needed(self, url):
        self.screening_nr += 1
        netloc = get_netloc(url)
        if netloc in [mtmf_hostname, mtmf_tickets_hostname]:
            self.read_screen(url)

    def read_screen(self, url):
        locations_file_format = os.path.join(file_keeper.webdata_dir, "screenings_{:03d}_{:02d}.html")
        locations_file = locations_file_format.format(self.film.filmid, self.screening_nr)
        url_file = UrlFile(url, locations_file, error_collector, debug_recorder)
        comment_at_download = f'Downloading shopping cart site {url}'
        try:
            locations_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
        except ValueError:
            pass
        else:
            if locations_html is not None:
                shopping_cart_parser = ShoppingCartPageParser(self.festival_data, self.film, self.screening_nr, url)
                shopping_cart_parser.feed(locations_html)
                self.screen_name = shopping_cart_parser.current_screen

    def feed(self, data):
        if self.film is None:
            error_collector.add('No film object when parsing screenings', "")
        else:
            super().feed(data)

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
        elif self.stateStack.state_is(self.ScreeningsParseState.AFTER_DATE) and tag == 'a' and len(attrs) > 1:
            if attrs[0][1] == 'time':
                self.read_screen_if_needed(attrs[1][1])
                self.stateStack.change(self.ScreeningsParseState.IN_TIMES)
        elif self.stateStack.state_is(self.ScreeningsParseState.AFTER_TIMES):
            if tag == 'p' and len(attrs) > 0 and attrs[0][1] == 'location':
                self.stateStack.change(self.ScreeningsParseState.IN_LOCATION)
            elif tag == 'span' and len(attrs) and attrs[0][1] == 'label uitverkocht':
                self.sold_out = True
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
    class ShoppingCartState(Enum):
        IDLE = auto()
        IN_SCREEN = auto()
        DONE = auto()

    def __init__(self, festival_data, film, sequence_nr, url):
        HtmlPageParser.__init__(self, festival_data, debug_recorder, 'SC', debugging=DEBUGGING)
        self.film = film
        self.sequence_nr = sequence_nr
        self.print_debug(self.bar, f'Analysing shopping cart #{sequence_nr} of FILM {film}, {url}')
        self.state_stack = self.StateStack(self.print_debug, self.ShoppingCartState.IDLE)
        self.current_screen = None

    def get_theater_screen(self, url):
        details_file_format = os.path.join(file_keeper.webdata_dir, "details_{:03d}_{:02d}.html")
        details_file = details_file_format.format(self.film.filmid, self.sequence_nr)
        url_file = UrlFile(url, details_file, error_collector, debug_recorder)
        comment_at_download = f'Downloading site {url}'
        try:
            details_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
        except ValueError:
            pass
        else:
            if details_html is not None:
                theater_screen_parser = TheaterScreenPageParser(self.festival_data, self.film, url)
                theater_screen_parser.feed(details_html)
                self.print_debug(f'@@ after reading {url}', f'{theater_screen_parser.current_screen=}')
                self.current_screen = theater_screen_parser.current_screen

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.ShoppingCartState.IDLE):
            if tag == 'div' and len(attrs) > 0 and attrs[0][1] == 'at-show-property at-show-location':
                self.state_stack.change(self.ShoppingCartState.IN_SCREEN)
            elif tag == 'iframe' and len(attrs) > 4 and attrs[0][1] == 'order__iframe order__iframe--crossmarx':
                details_url = attrs[4][1]
                self.get_theater_screen(details_url)
                self.state_stack.change(self.ShoppingCartState.DONE)

    def handle_data(self, data):
        if self.state_stack.state_is(self.ShoppingCartState.IN_SCREEN):
            self.current_screen = data.strip()
            self.state_stack.change(self.ShoppingCartState.DONE)


class TheaterScreenPageParser(HtmlPageParser):
    class ScreensParseState(Enum):
        IDLE = auto()
        IN_SCREENING_LOCATION = auto()
        DONE = auto()

    def __init__(self, festival_data, film, url):
        HtmlPageParser.__init__(self, festival_data, debug_recorder, 'TS', debugging=DEBUGGING)
        self.print_debug(self.bar, f'Analysing screening location of FILM {film}, {url}')
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


class MtmfData(FestivalData):

    def __init__(self, planner_data_dir):
        FestivalData.__init__(self, planner_data_dir, FESTIVAL_CITY)

    def film_key(self, film, url):
        return url

    def film_can_go_to_planner(self, film_id):
        return True

    def screening_can_go_to_planner(self, screening):
        can_go = FestivalData.screening_can_go_to_planner(self, screening)
        return can_go and screening.screen.theater.city.name == FESTIVAL_CITY


if __name__ == "__main__":
    main()
