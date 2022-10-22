#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load films, film information, screens and screenings from the IDFA 2020
website.

Created on Wed Nov  4 20:36:18 2020

@author: maarten
"""

import datetime
import html.parser
import os
import re

from Shared.application_tools import ErrorCollector, DebugRecorder
from Shared.planner_interface import FilmInfo, ScreenedFilm, Film, Screening, FestivalData
from Shared.web_tools import get_charset, UrlReader, HtmlPageParser, iripath_to_uripath

# Parameters.
festival = 'IDFA'
festival_city = 'Amsterdam'
festival_year = 2020
az_page_count = 27

# Directories.
project_dir = os.path.expanduser(f"~/Documents/Film/{festival}/{festival}{festival_year}")
webdata_dir = os.path.join(project_dir, "_website_data")
plandata_dir = os.path.join(project_dir, "_planner_data")

# Filename formats.
az_file_format = os.path.join(webdata_dir, "azpage_{:02d}.html")
film_file_format = os.path.join(webdata_dir, "filmpage_{:03d}.html")

# Files.
filmdata_file = os.path.join(plandata_dir, "filmdata.csv")
filminfo_file = os.path.join(plandata_dir, "filminfo.xml")
debug_file = os.path.join(plandata_dir, "debug.txt")

# URL information.
az_webroot_format = "https://www.idfa.nl/nl/collectie/documentaires?page={:d}&filters[edition.year]=2020"
films_hostname = "https://www.idfa.nl"

# Application tools.
error_collector = ErrorCollector()
debug_recorder = DebugRecorder(debug_file)


def main():
    # Initialize a festival data object.
    idfa_data = IdfaData(plandata_dir)

    # Store known title languages.
    store_title_languages()

    comment("Parsing AZ pages.")
    films_loader = FilmsLoader(az_page_count)
    films_loader.get_films(idfa_data)

    comment("Parsing film pages.")
    film_details_loader = FilmDetailsLoader()
    film_details_loader.get_film_details(idfa_data)

    comment("Parsing combination program pages.")
    combinations_loader = CombinationProgramsLoader()
    combinations_loader.get_combination_details(idfa_data)

    if(Globals.error_collector.error_count() > 0):
        comment("Encountered some errors:")
        print(Globals.error_collector)

    comment("Done laoding IDFA data.")
    idfa_data.sort_films()
    idfa_data.write_films()
    idfa_data.write_filminfo()
    idfa_data.write_screens()
    idfa_data.write_screenings()
    Globals.debug_recorder.write_debug()


def comment(text):
    print(f"\n{datetime.datetime.now()}  - {text}")


def store_title_languages():
    Film.language_by_title['El Sicario, Room 164'] = 'es'
    Film.language_by_title['Il mio corpo'] = 'it'
    Film.language_by_title['Le temps perdu'] = 'fr'
    Film.language_by_title['O arrais do mar'] = 'pt'


class Globals:
    idfa_data = None
    error_collector = None
    debug_recorder = None


class FilmsLoader:

    def __init__(self, az_page_count):
        self.page_count = az_page_count

    def get_films(self, data):
        for page_number in range(1, self.page_count + 1):
            az_data = None
            az_file = az_file_format.format(page_number)
            if os.path.isfile(az_file):
                charset = get_charset(az_file)
                with open(az_file, 'r', encoding=charset) as f:
                    az_data = f.read()
            else:
                az_page = az_webroot_format.format(page_number)
                print(f"Downloading {az_page}.")
                url_reader = UrlReader(Globals.error_collector)
                az_data = url_reader.load_url(az_page, az_file)
            parser = AzPageParser(data)
            parser.feed(az_data)


class FilmDetailsLoader:

    def __init__(self):
        pass

    def get_film_details(self, idfa_data):
        for film in idfa_data.films:
            print(f'Getting FILM DETAILS of: {film.title}')
            self.get_details_of_one_film(idfa_data, film)

    def get_details_of_one_film(self, idfa_data, film):
        film_data = None
        film_file = film_file_format.format(film.filmid)
        if os.path.isfile(film_file):
            charset = get_charset(film_file)
            with open(film_file, 'r', encoding=charset) as f:
                film_data = f.read()
        else:
            print(f"Downloading site of {film.title}: {film.url}")
            url_reader = UrlReader(Globals.error_collector)
            film_data = url_reader.load_url(film.url, film_file)
        if film_data is not None:
            print(f'Parsing FILM INFO of: {film.title}')
            filminfo_parser = FilmPageParser(idfa_data, film)
            filminfo_parser.feed(film_data)
            print(f'Parsing SCREENINGS of: {film.title}')
            screenings_parser = ScreeningsParser(idfa_data, film)
            screenings_parser.feed(film_data)


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
            filmid = idfa_data.film_id_by_url[url]
            film_file = film_file_format.format(filmid)
            if os.path.isfile(film_file):
                charset = get_charset(film_file)
                with open(film_file, 'r', encoding=charset) as f:
                    compilation_data = f.read()
        if compilation_data is None:
            print(f'Downloading site of combination program: {url}')
            url_reader = UrlReader(Globals.error_collector)
            compilation_data = url_reader.read_url(url)
        if compilation_data is not None:
            print(f'Parsing FILM INFO from: {url}')
            film = CompilationPageParser(idfa_data, url, film).feed(compilation_data)
            if film is not None:
                film_file = film_file_format.format(filmid)
                if not os.path.isfile(film_file):
                    print(f'Writing HTML data of: {film.title}')
                    with open(film_file, 'w') as f:
                        f.write(compilation_data)
                print(f'Parsing SCREENINGS of combination program: {film.title}')
                ScreeningsParser(idfa_data, film).feed(compilation_data)
            else:
                Globals.error_collector.add('Parsing of COPMBINATION PROGRAM site failed', url)
        return film


class HtmlPageParser(HtmlPageParser):

    def __init__(self, idfa_data, debug_prefix):
        HtmlPageParser.__init__(self, Globals.debug_recorder, debug_prefix)
        self.idfa_data = idfa_data
        self.debugging = False


class AzPageParser(HtmlPageParser):

    re_duration = re.compile(r"(?P<duration>\d+) min")

    def __init__(self, idfa_data):
        HtmlPageParser.__init__(self, idfa_data, "AZ")
        self.debugging = False
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

    def add_film(idfa_data, title, url, duration, medium_category='films'):
        film = idfa_data.create_film(title, url)
        if film is not None:
            film.medium_category = medium_category
            film.duration = duration
            print(f"Adding FILM: {film.title}")
            idfa_data.films.append(film)
        return film

    def add_filminfo(idfa_data, film, description, article, screened_films=[]):
        if description is not None or article is not None:
            filminfo = FilmInfo(film.filmid, description, article, screened_films)
            idfa_data.filminfos.append(filminfo)

    def add_film_finding_duration(self):
        if self.duration is None:
            try:
                minutes = self.last_data[3]
                self.print_debug("--", f"Unrecognized DURATION, {minutes} used")
                print(f"-- Unrecognized DURATION, {minutes} used")
                self.duration = datetime.timedelta(minutes=int(minutes))
            except IndexError as e:
                Globals.error_collector.add(str(e), f"Can't reconstruct a duration for {self.title}")
                self.duration = datetime.timedelta(minutes=0)
        self.print_debug('--', f'Adding FILM {self.title}')
        self.film = AzPageParser.add_film(self.idfa_data, self.title, self.url, self.duration)
        if self.film is not None:
            AzPageParser.add_filminfo(self.idfa_data, self.film, self.description, None)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
        if tag == "article":
            self.init_film_data()
        if self.await_duration and tag == 'ul':
            self.in_duration = True
            self.await_duration = False
        for attr in attrs:
            if tag == "a":
                if attr[0] == "class" and attr[1].startswith("collectionitem-module__link_"):
                    self.in_link = True
                elif self.in_link and attr[0] == 'href':
                    uri_path = iripath_to_uripath(attr[1])
                    self.url = films_hostname + uri_path
                    self.in_link = False
            elif tag == "h2":
                if attr[0] == "class" and attr[1].startswith("collectionitem-module__title_"):
                    self.in_title = True
            elif tag == "p":
                if attr[0] == "class" and attr[1].startswith("collectionitem-module__description_"):
                    self.in_description = True

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)
        if self.in_duration and tag == 'ul':
            self.in_duration = False
        if tag == "article":
            self.add_film_finding_duration()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
        if self.in_title:
            self.in_title = False
            self.title = data
            self.await_duration = True
        elif self.in_duration:
            self.last_data.append(data)
            m = self.re_duration.match(data)
            if m is not None:
                duration = m.group('duration')
                self.duration = datetime.timedelta(minutes=int(duration))
        elif self.in_description:
            self.description = data
            self.in_description = False


class ScreeningsParser(HtmlPageParser):

    re_times = re.compile(r'(?P<day>\d+) (?P<month>\w+)\. \d\d:\d\d - \d\d:\d\d \((?P<start_time>\d\d:\d\d) - (?P<end_time>\d\d:\d\d) AMS\)')
    nl_month_by_name = {}
    nl_month_by_name['nov'] = 11
    nl_month_by_name['dec'] = 12

    def __init__(self, idfa_data, film, debug_prefix='S'):
        HtmlPageParser.__init__(self, idfa_data, debug_prefix)
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
            self.idfa_data.screenings.append(screening)
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

        dupls = [s for s in self.idfa_data.screenings if s.screen == screening.screen and s.start_datetime == screening.start_datetime]
        for dupl in dupls:
            print(f'DUPLICATE screening: {dupl.film.title} - {repr(dupl)}{dupl.film.url}\n{screening.film.url}')
            dupl_summ = f'\n{screening_summ(dupl)}{screening_summ(screening)}'
            self.print_debug('--', f'DUPLICATE screenings: {dupl_summ}')
            if dupl.film.filmid == screening.film.filmid and dupl.film.medium_category == screening.film.medium_category:
                Globals.error_collector.add(f'Coinciding screenings of two {dupl.film.medium_category}', f'{dupl_summ}')
                return True
            if screening.combination_program_url is not None:
                return False
            if dupl.combination_program_url is not None:
                return False
            Globals.error_collector.add(f'Combining {dupl.film.medium_category} and {screening.film.medium_category} not implemented',
                                        f'{dupl_summ}')
        return False

    def add_compilation_url(self):
        print(f'Found COMPILATION URL {self.compilation_url}')
        self.print_debug('--', f'Found COMPILATION URL {self.compilation_url}')
        self.idfa_data.compilation_by_url[self.compilation_url] = None

    def get_url(self, iri):
        return films_hostname + iripath_to_uripath(iri)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
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
        HtmlPageParser.handle_endtag(self, tag)
        if self.in_screening and tag == 'section' and self.start_date is not None:
            self.in_screening = False
            self.add_screening()
        elif tag == 'body':
            self.in_screenings = False

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
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
                Globals.error_collector.add('Pattern not recognized', f'{self.film.title}: \'{data}\'.')
        elif self.in_location:
            self.in_location = False
            self.screen = self.idfa_data.get_screen(festival_city, data)
            self.in_compilation = True


class FilmPageParser(HtmlPageParser):

    def __init__(self, idfa_data, film, debug_prefix='F'):
        HtmlPageParser.__init__(self, idfa_data, debug_prefix)
        self.film = film
        self.debugging = False
        self.film_description = None
        self.film_article = None
        self.in_article = False
        self.await_content = False

    def add_film_article(self, article):
        filminfos = [filminfo for filminfo in self.idfa_data.filminfos if filminfo.filmid == self.film.filmid]
        try:
            filminfo = filminfos[0]
            filminfo.article = article
        except IndexError as e:
            Globals.error_collector.add(str(e), f'No filminfo description found for: {self.film.title}')
            filminfo = FilmInfo(self.film.filmid, '', article)
            self.idfa_data.filminfos.append(filminfo)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
        if self.in_article and tag == 'meta':
            for attr in attrs:
                if attr == ('name', 'description'):
                    self.await_content = True
                elif self.await_content and attr[0] == 'content':
                    self.await_content = False
                    self.in_article = False
                    self.film_article = attr[1]
                    self.print_debug("Found ARTICLE:", f"{self.film_article}")
                    self.add_film_article(self.film_article)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)
        if tag == 'title':
            self.in_article = True

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)


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
            Globals.error_collector.add('No title fonud of Combination Program', self.compilation_url)
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
                    Globals.error_collector.add('Duplicate title', message)

    def add_screened_film(self):
        film = self.idfa_data.get_film_by_key(self.screened_title, None)
        screened_film = ScreenedFilm(film.filmid, self.screened_title, self.screened_description)
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


class Film(Film):

    def __init__(self, film):
        Film.__init__(self, film.seqnr, film.filmid, film.title, film.url)

    def __lt__(self, other):
        self_is_alpha = self.re_alpha.match(self.sortstring) is not None
        other_is_alpha = self.re_alpha.match(other.sortstring) is not None
        if self_is_alpha and not other_is_alpha:
            return True
        if not self_is_alpha and other_is_alpha:
            return False
        return self.sortstring < other.sortstring


class Screening(Screening):
    def __init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience, combination_program_url):
        Screening.__init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience)
        self.combination_program_url = combination_program_url


class IdfaData(FestivalData):

    def __init__(self, plandata_dir):
        FestivalData.__init__(self, plandata_dir)
        self.compilation_by_url = {}

    def create_film(self, title, url):
        return Film(FestivalData.create_film(self, title, url))


if __name__ == "__main__":
    main()
