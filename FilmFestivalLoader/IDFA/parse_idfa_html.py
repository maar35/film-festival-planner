#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load films, film information, screens and screenings from the IDFA 2020
website.

Created on Wed Nov  4 20:36:18 2020

@author: maarten
"""

import datetime
import os
import re
from enum import Enum, auto

import Shared.planner_interface as planner
from Shared.application_tools import ErrorCollector, DebugRecorder, comment
from Shared.parse_tools import FileKeeper
from Shared.web_tools import get_charset, UrlReader, iripath_to_uripath, UrlFile, HtmlPageParser

# Parameters.
festival = 'IDFA'
festival_city = 'Amsterdam'
festival_year = 2022
az_page_count = 30

# Files.
fileKeeper = FileKeeper(festival, festival_year)
debug_file = fileKeeper.debug_file

plandata_dir = fileKeeper.plandata_dir
filmdata_file = os.path.join(plandata_dir, "filmdata.csv")
filminfo_file = os.path.join(plandata_dir, "filminfo.xml")

# URL information.
az_webroot_root = 'https://www.idfa.nl/nl/collectie/documentaires'
az_slug = '/nl/collectie/documentaires'
az_param_pattern = '?page={}&filters[edition.year]=2022'
az_hostname = "https://www.idfa.nl"

# Application tools.
error_collector = ErrorCollector()
debug_recorder = DebugRecorder(debug_file)


def main():
    # Initialize a festival data object.
    comment('Creating festival data object.')
    festival_data = IdfaData(plandata_dir)

    # Store known title languages.
    store_title_languages()

    # Try parsing the websites.
    write_film_list = False
    write_other_lists = True
    try:
        parse_idfa_sites(festival_data)
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
        comment("Encountered some errors:")
        print(error_collector)

    # Write parsed information.
    comment("Done loading IDFA data.")
    planner.write_lists(festival_data, write_film_list, write_other_lists)
    debug_recorder.write_debug()


def parse_idfa_sites(festival_data):
    comment("Parsing AZ pages and film pages.")
    get_films(festival_data)


def get_films(festival_data):
    for seq_nr in range(1, az_page_count + 1):
        az_url = az_hostname + az_slug + az_param_pattern.format(seq_nr)
        az_file = fileKeeper.az_file(seq_nr)
        url_file = UrlFile(az_url, az_file, error_collector, byte_count=200)
        az_html = url_file.get_text()
        if az_html is not None:
            comment(f'Analysing az page {seq_nr}')
            AzPageParser(festival_data, True, url_file.encoding).feed(az_html)


def get_film_details(festival_data, url):
    emergency_encoding = 'utf-8'
    comment(f'Analysing film page {url}')
    film_id = festival_data.new_film_id(url)
    film_file = fileKeeper.filmdata_file(film_id)
    url_file = UrlFile(url, film_file, error_collector, byte_count=200)
    if url_file.encoding is None:
        print(f'Manually setting encoding to {emergency_encoding}')
        url_file.encoding = emergency_encoding
    film_html = url_file.get_text(f'Downloading film with ID {film_id} from {url}')
    if film_html is not None:
        print(f'@@ Film file {film_file} downloaded, analysing the HTML')
        FilmPageParser(festival_data, film_id, url, 'F').feed(film_html)
    else:
        error_collector.add('HTML text not found', f'Trying to add new film with ID {film_id}')


def store_title_languages():
    Film.language_by_title['Der Busenfreund'] = 'de'


class CombinationProgramsLoader:

    def __init__(self):
        pass

    def get_combination_details(self, idfa_data):
        for url in idfa_data.compilation_by_url.keys():
            print(f'Getting COMBINATION PROGRAM DETAILS from: {url}')
            film = self.get_details_of_one_compilation(idfa_data, url)
            if film is not None:
                idfa_data.compilation_by_url[url] = film
                screenings = [s for s in idfa_data.screenings if s.combination_program_url == url]
                for screening in screenings:
                    screening.combination_program = film

    def get_details_of_one_compilation(self, idfa_data, url):
        compilation_data = None
        film = None
        if url in idfa_data.film_id_by_url.keys():
            film_id = idfa_data.film_id_by_url[url]
            film_file = fileKeeper.filmdata_file(film_id)
            if os.path.isfile(film_file):
                charset = get_charset(film_file)
                with open(film_file, 'r', encoding=charset) as f:
                    compilation_data = f.read()
        if compilation_data is None:
            print(f'Downloading site of combination program: {url}')
            url_reader = UrlReader(error_collector)
            compilation_data = url_reader.read_url(url)
        if compilation_data is not None:
            print(f'Parsing FILM INFO from: {url}')
            film = CompilationPageParser(idfa_data, url, film).feed(compilation_data)
            if film is not None:
                film_file = fileKeeper.filmdata_file(film.filmid)
                if not os.path.isfile(film_file):
                    print(f'Writing HTML data of: {film.title}')
                    with open(film_file, 'w') as f:
                        f.write(compilation_data)
                print(f'Parsing SCREENINGS of combination program: {film.title}')
                ScreeningsParser(idfa_data, film).feed(compilation_data)
            else:
                error_collector.add('Parsing of COPMBINATION PROGRAM site failed', url)
        return film


class IdfaHtmlPageParser(HtmlPageParser):

    def __init__(self, festival_data, debug_prefix):
        HtmlPageParser.__init__(self, debug_recorder, debug_prefix)
        self.festival_data = festival_data
        self.debugging = False


class AzPageParser(IdfaHtmlPageParser):
    class AzParseState(Enum):
        IDLE = auto()
        IN_FILM_SECTION = auto()

    def __init__(self, festival_data, debugging=False, encoding=None):
        IdfaHtmlPageParser.__init__(self, festival_data, 'AZ')
        self.film = None
        self.title = None
        self.url = None
        self.duration = None
        self.description = None
        self.last_data = None
        self.in_link = None
        self.in_title = None
        self.await_duration = None
        self.in_duration = None
        self.in_description = None
        self.stateStack = self.StateStack(self.print_debug, self.AzParseState.IDLE)
        self.init_film_data()

    def init_film_data(self):
        self.film = None
        self.title = None
        self.url = None
        self.duration = None
        self.description = None
        self.last_data = []
        self.in_link = False
        self.in_title = False
        self.await_duration = False
        self.in_duration = False
        self.in_description = False

    def add_filminfo(self, film, description, article, screened_films=[]):
        if description is not None or article is not None:
            filminfo = planner.FilmInfo(film.filmid, description, article, screened_films)
            self.festival_data.filminfos.append(filminfo)

    def get_film(self):
        get_film_details(self.festival_data, self.url)

    def handle_starttag(self, tag, attrs):
        IdfaHtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.AzParseState.IDLE) and tag == 'article':
            self.stateStack.push(self.AzParseState.IN_FILM_SECTION)
        if self.stateStack.state_is(self.AzParseState.IN_FILM_SECTION) and tag == 'a':
            if len(attrs) > 1 and attrs[0][1] == 'collectionitem-module__link___2NQ6Q':
                slug = attrs[1][1]
                self.url = az_hostname + iripath_to_uripath(slug)
                self.get_film()

    def handle_endtag(self, tag):
        IdfaHtmlPageParser.handle_endtag(self, tag)

    def handle_data(self, data):
        IdfaHtmlPageParser.handle_data(self, data)


class ScreeningsParser(IdfaHtmlPageParser):

    re_times = re.compile(r'(?P<day>\d+) (?P<month>\w+)\. \d\d:\d\d - \d\d:\d\d \((?P<start_time>\d\d:\d\d) - (?P<end_time>\d\d:\d\d) AMS\)')
    nl_month_by_name = {}
    nl_month_by_name['nov'] = 11
    nl_month_by_name['dec'] = 12

    def __init__(self, idfa_data, film, debug_prefix='S'):
        IdfaHtmlPageParser.__init__(self, idfa_data, debug_prefix)
        self.film = film
        self.in_screening_name = None
        self.init_screening_data()

    def init_screening_data(self):
        self.screening_name = None
        self.screen = None
        self.start_date = None
        self.start_time = None
        self.end_time = None
        self.audience = 'publiek'
        self.compilation_url = None
        self.qa = ''
        self.extra = ''
        self.in_screenings = False
        self.in_screening = False
        self.in_screening_name = False
        self.in_times = False
        self.in_location = False
        self.in_compilation = False
        self.film_description = None

    def add_screening(self):
        start_datetime, end_datetime = self.get_datetimes()
        if self.film.duration is None:
            self.film.duration = end_datetime - start_datetime
        self.print_debug(f"--- Adding SCREENING of {self.film.title}",
                         f"SCREEN = {self.screen}, START TIME = {start_datetime}, END TIME = {end_datetime}")
        print()
        print(f"---SCREENING OF {self.film.title}")
        print(f"--  screening name:  {self.screening_name}")
        print(f"--  screen:          {self.screen}")
        print(f"--  times:           {start_datetime} - {end_datetime}")
        print(f"--  q and a:         {self.qa}")
        print(f"--  extra:           {self.extra}")
        print(f"--  audience:        {self.audience}")
        print(f"--  duration:        Film: {self.film.duration_str()}   Screening: {end_datetime - start_datetime}")
        print(f"--  category:        {self.film.medium_category}")
        print(f"--  compilation url: {self.compilation_url}")
        screening = Screening(self.film, self.screen, start_datetime, end_datetime, self.qa, self.extra, self.audience, self.compilation_url)
        if not self.is_coinciding(screening):
            self.festival_data.screenings.append(screening)
            print("---SCREENING ADDED")
            self.init_screening_data()

    def get_datetimes(self):
        start_datetime = datetime.datetime.combine(self.start_date, self.start_time)
        end_date = self.start_date if self.end_time > self.start_time else self.start_date + datetime.timedelta(days=1)
        end_datetime = datetime.datetime.combine(end_date, self.end_time)
        return start_datetime, end_datetime

    def is_coinciding(self, screening):

        def screening_summ(s):
            sep = self.debug_prefix + 2*' '
            nl = '\n'
            return f'{sep}{s.film.medium_category} {repr(s).rstrip(nl)} - {s.film.title} ({s.film.duration_str()}){nl}'

        dupls = [s for s in self.festival_data.screenings if s.screen == screening.screen and s.start_datetime == screening.start_datetime]
        for dupl in dupls:
            print(f'DUPLICATE screening: {dupl.film.title} - {repr(dupl)}{dupl.film.url}\n{screening.film.url}')
            dupl_summ = f'\n{screening_summ(dupl)}{screening_summ(screening)}'
            self.print_debug('--', f'DUPLICATE screenings: {dupl_summ}')
            if dupl.film.filmid == screening.film.filmid and dupl.film.medium_category == screening.film.medium_category:
                error_collector.add(f'Coinciding screenings of two {dupl.film.medium_category}', f'{dupl_summ}')
                return True
            if screening.combination_program_url is not None:
                return False
            if dupl.combination_program_url is not None:
                return False
            error_collector.add(f'Combining {dupl.film.medium_category} and {screening.film.medium_category} not implemented',
                                        f'{dupl_summ}')
        return False

    def add_compilation_url(self):
        print(f'Found COMPILATION URL {self.compilation_url}')
        self.print_debug('--', f'Found COMPILATION URL {self.compilation_url}')
        self.festival_data.compilation_by_url[self.compilation_url] = None

    def get_url(self, iri):
        return az_hostname + iripath_to_uripath(iri)

    def handle_starttag(self, tag, attrs):
        IdfaHtmlPageParser.handle_starttag(self, tag, attrs)
        if tag == 'body':
            self.in_screenings = True
        if tag == 'h3' and len(attrs) == 1:
            attr = attrs[0]
            if attr[0] == 'class' and attr[1].startswith('tickets-module__screeningName_'):
                self.in_screening_name = True
        elif tag == 'div' and len(attrs) == 1:
            attr = attrs[0]
            if attr[0] == 'class' and attr[1].startswith('table-module__name_'):
                if self.start_date is not None and self.in_screening:
                    self.add_screening()
                self.in_times = True
                self.in_screening = True
            elif attr[0] == 'class' and attr[1].startswith('tickets-module__location_'):
                self.in_location = True
        elif self.in_compilation and tag == 'a' and len(attrs) > 1:
            attr = attrs[1]
            if attr[0] == 'href' and attr[1].startswith('/nl/shows/'):
                self.in_compilation = False
                iri = attr[1]
                self.compilation_url = self.get_url(iri)
                self.add_compilation_url()

    def handle_endtag(self, tag):
        IdfaHtmlPageParser.handle_endtag(self, tag)
        if self.in_screening and tag == 'section' and self.start_date is not None:
            self.in_screening = False
            self.add_screening()
        elif tag == 'body':
            self.in_screenings = False

    def handle_data(self, data):
        IdfaHtmlPageParser.handle_data(self, data)
        if self.in_screening_name:
            self.in_screening_name = False
            self.screening_name = data
        elif self.in_times:
            self.in_times = False
            m = self.re_times.match(data)
            if m is not None:
                day_str = m.group('day')
                month_str = m.group('month')
                start_time_str = m.group('start_time')
                end_time_str = m.group('end_time')
                self.start_date = datetime.date(festival_year, self.nl_month_by_name[month_str], int(day_str))
                self.start_time = datetime.time.fromisoformat(start_time_str)
                self.end_time = datetime.time.fromisoformat(end_time_str)
                self.print_debug('-- ', f'Found TIMES: {self.start_date}, {self.start_time}-{self.end_time}')
            else:
                error_collector.add('Pattern not recognized', f'{self.film.title}: \'{data}\'.')
        elif self.in_location:
            self.in_location = False
            self.screen = self.festival_data.get_screen(festival_city, data)
            self.in_compilation = True


class FilmPageParser(IdfaHtmlPageParser):
    class FilmParseState(Enum):
        IDLE = auto()
        AWAITING_DICT = auto()
        IN_DICT = auto()
        AWAITING_TITLE = auto()
        IN_TITLE = auto()
        DONE = auto

    re_dict = re.compile(r'"runtime":(?P<duration>\d+),')

    def __init__(self, festival_data, film_id, url, debug_prefix='F'):
        IdfaHtmlPageParser.__init__(self, festival_data, debug_prefix)
        self.film_id = film_id
        self.url = url
        self.debugging = True
        self.title = None
        self.duration = None
        self.film = None
        self.film_description = None
        self.film_article = None
        self.in_article = False
        self.await_content = False
        self.state_stack = self.StateStack(self.print_debug, self.FilmParseState.IDLE)

    def add_film_article(self, article):
        filminfos = [filminfo for filminfo in self.festival_data.filminfos if filminfo.filmid == self.film.filmid]
        try:
            filminfo = filminfos[0]
            filminfo.article = article
        except IndexError as e:
            error_collector.add(str(e), f'No filminfo description found for: {self.film.title}')
            filminfo = planner.FilmInfo(self.film.filmid, '', article)
            self.festival_data.filminfos.append(filminfo)

    def get_properties_from_dict(self, data):
        matches = self.re_dict.search(data)
        minutes = int(matches.group('duration')) if matches else 0
        self.duration = datetime.timedelta(minutes=minutes)

    def add_film(self):
        # Create a new film.
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            error_collector.add(f'Could not create film:', '{self.title} ({self.url})')
        else:
            # Fill details.
            self.film.duration = self.duration
            self.film.medium_category = 'films'

            # Add the film to the list.
            print(f'@@ created film {self.film}')
            self.festival_data.films.append(self.film)

    def handle_starttag(self, tag, attrs):
        IdfaHtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.FilmParseState.IDLE) and tag == 'script':
            self.state_stack.push(self.FilmParseState.IN_DICT)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_TITLE) and tag == 'h1':
            self.state_stack.change(self.FilmParseState.IN_TITLE)

    def handle_endtag(self, tag):
        IdfaHtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_is(self.FilmParseState.IN_DICT):
            self.state_stack.change(self.FilmParseState.AWAITING_TITLE)

    def handle_data(self, data):
        IdfaHtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.FilmParseState.IN_DICT):
            self.get_properties_from_dict(data)
        elif self.state_stack.state_is(self.FilmParseState.IN_TITLE):
            self.title = data
            self.add_film()
            self.state_stack.change(self.FilmParseState.DONE)

class CompilationPageParser(FilmPageParser):

    compilation_by_title = {}

    def __init__(self, idfa_data, url, film):
        FilmPageParser.__init__(self, idfa_data, film, 'CP')
        self.compilation_url = url
        self.debugging = True
        self.duration = None
        self.film_description = None
        self.film_article = None
        self.screenings = []
        self.screened_films = []
        self.compilation_title = None
        self.compilation = None
        self.in_compilation_title = None
        self.in_screened_films = None
        self.times_shared = 0
        self.init_screened_film()

    def init_screened_film(self):
        self.screened_title = None
        self.screened_description = None
        self.in_screened_title = False
        self.in_screened_description = False

    def add_film_article(self, article):
        pass

    def add_compilation(self):
        self.print_debug('--', f'Creating COMPILATION {self.compilation_url}')
        if self.compilation_title:
            title = self.compilation_title
        else:
            title = self.compilation_url.split('/')[-1]
            error_collector.add('No title fonud of Combination Program', self.compilation_url)
        compilation = self.idfa_data.create_film(title,  self.compilation_url)
        if compilation is not None:
            compilation.medium_category = 'verzamelprogrammas'
            self.print_debug('--', f'Adding new COMPILATION {title}')
            self.idfa_data.films.append(compilation)
            self.film_description = 'Verzamelprogramma'
            self.compilation = compilation
            self.compilation_by_title[title] = compilation
        else:
            print(f'COMPILATION {title} already in list')
            categories = [f.medium_category for f in self.idfa_data.films if f.title == title]
            for category in categories:
                if category == compilation.medium_category:
                    self.print_debug('--', f'ALREADY created COMPILATION {title}')
                    self.compilation = self.compilation_by_title[title]
                else:
                    message = f'New compilation {title} has same title as existing {category}'
                    self.print_debug('--PROBLEM', message)
                    error_collector.add('Duplicate title', message)

    def add_screened_film(self):
        film = self.idfa_data.get_film_by_key(self.screened_title, None)
        screened_film = planner.ScreenedFilm(film.filmid, self.screened_title, self.screened_description)
        self.screened_films.append(screened_film)

    def add_compilation_filminfo(self):
        AzPageParser.add_filminfo(self.idfa_data, self.compilation, self.film_description, self.film_article, self.screened_films)

    def feed(self, data):
        bar = 72 * '-'
        self.print_debug(bar, self.compilation_url)
        html.parser.HTMLParser.feed(self, data)
        return self.compilation

    def handle_starttag(self, tag, attrs):
        FilmPageParser.handle_starttag(self, tag, attrs)
        if tag == 'h1':
            attr = attrs[0]
            if attr[0] == 'class' and attr[1].startswith('hero-module__title_'):
                self.print_debug('--', 'Start looking for COMPILATION title')
                self.in_compilation_title = True
        elif tag == 'h2' and len(attrs) > 0:
            attr = attrs[0]
            if attr[0] == 'class':
                if attr[1].startswith('contentpanel-module__sectionTitle___Z2ucG contentpanel-module__collectionTitle__'):
                    self.in_screened_films = True
                elif attr[1].startswith('collectionitem-module__title__'):
                    self.in_screened_title = True
        elif tag == 'p' and len(attrs) > 0:
            attr = attrs[0]
            if attr[0] == 'class' and attr[1].startswith('collectionitem-module__description__'):
                self.in_screened_description = True
        elif tag == 'g' and len(attrs) > 0:
            attr = attrs[0]
            if attr[0] == 'id' and attr[1] == 'Share':
                self.times_shared += 1
                if self.times_shared == 2:
                    self.in_screened_films = False
                    self.add_compilation_filminfo()

    def handle_endtag(self, tag):
        FilmPageParser.handle_endtag(self, tag)

    def handle_data(self, data):
        FilmPageParser.handle_data(self, data)
        if self.in_compilation_title:
            self.in_compilation_title = False
            self.compilation_title = data
            self.print_debug('--', f'Found COMPILATION TITLE: \'{data}\'')
            self.add_compilation()
        elif self.in_screened_title:
            self.in_screened_title = False
            self.print_debug('--', f'Found SCREENED TITLE: \'{data}\'')
            self.screened_title = data
        elif self.in_screened_description:
            self.in_screened_description = False
            self.screened_description = data
            self.add_screened_film()


class Film(planner.Film):

    def __init__(self, film):
        planner.Film.__init__(self, film.seqnr, film.filmid, film.title, film.url)

    def __lt__(self, other):
        self_is_alpha = self.re_alpha.match(self.sortstring) is not None
        other_is_alpha = self.re_alpha.match(other.sortstring) is not None
        if self_is_alpha and not other_is_alpha:
            return True
        if not self_is_alpha and other_is_alpha:
            return False
        return self.sortstring < other.sortstring


class Screening(planner.Screening):
    def __init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience, combination_program_url):
        planner.Screening.__init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience)
        self.combination_program_url = combination_program_url


class IdfaData(planner.FestivalData):

    def __init__(self, directory):
        planner.FestivalData.__init__(self, directory)
        self.compilation_by_url = {}

    def film_key(self, title, url):
        return url

    def film_can_go_to_planner(self, film_id):
        return True


if __name__ == "__main__":
    main()
