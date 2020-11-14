#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load films, film information, screens and screenings from the IDFA 2020
website.

Created on Wed Nov  4 20:36:18 2020

@author: maarten
"""

import os
import sys
import re
import datetime
import html.parser

sys.path.insert(0, "/Users/maarten/Projects/FilmFestivalPlanner/FilmFestivalLoader/Shared")
import planner_interface as planner
import application_tools as app_tools
import web_tools

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
az_webroot_format="https://www.idfa.nl/nl/collectie/documentaires?page={:d}&filters[edition.year]=2020"
films_hostname = "https://www.idfa.nl"


def main():
    # Initialize globals.
    Globals.error_collector = app_tools.ErrorCollector()
    Globals.debug_recorder = app_tools.DebugRecorder(debug_file)
    
    # initialize a festival data object.
    idfa_data = IdfaData(plandata_dir)
    
    comment("Parsing AZ pages.")
    films_loader = FilmsLoader(az_page_count)
    films_loader.get_films(idfa_data)
    
    comment("Parsing film pages.")
    film_detals_loader = FilmDetailsLoader()
    film_detals_loader.get_film_details(idfa_data)
    
    if(Globals.error_collector.error_count() > 0):
        comment("Encountered some errors:")
        print(Globals.error_collector)
        
    comment("Done laoding IDFA data.")
    idfa_data.write_films()
    idfa_data.write_filminfo()
    idfa_data.write_screens()
    idfa_data.write_screenings()
    Globals.debug_recorder.write_debug()

def comment(text):
    print(f"\n{datetime.datetime.now()}  - {text}")


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
                charset = web_tools.get_charset(az_file)
                with open(az_file, 'r', encoding=charset) as f:
                    az_data = f.read()
            else:
                az_page = az_webroot_format.format(page_number)
                print(f"Downloading {az_page}.")
                url_reader = web_tools.UrlReader(Globals.error_collector)
                az_data = url_reader.load_url(az_page, az_file)
            parser = AzPageParser(data)
            parser.feed(az_data)


class FilmDetailsLoader:

    def __init__(self):
        pass

    def get_film_details(self, idfa_data):
        for film in idfa_data.films:
            print(f'Getting FILM DETAILS of: {film.title}')
            parser = FilmPageParser(idfa_data, film)
            FilmDetailsLoader.get_details_of_one_film(idfa_data, film, parser)

    def get_details_of_one_film(idfa_data, film, parser):
        film_data = None
        film_file = film_file_format.format(film.filmid)
        if os.path.isfile(film_file):
            charset = web_tools.get_charset(film_file)
            with open(film_file, 'r', encoding=charset) as f:
                film_data = f.read()
        else:
            print(f"Downloading site of {film.title}: {film.url}")
            url_reader = web_tools.UrlReader(Globals.error_collector)
            film_data = url_reader.load_url(film.url, film_file)
        if film_data is not None:
            parser.feed(film_data)


class HtmlPageParser(html.parser.HTMLParser):
    
    def __init__(self, idfa_data, debug_prefix):
        html.parser.HTMLParser.__init__(self)
        self.idfa_data = idfa_data
        self.debug_prefix = debug_prefix
        self.debugging = False
        self.debug_text = ""

    def print_debug(self, str1, str2):
        if self.debugging:
            Globals.debug_recorder.add(self.debug_prefix + ' ' + str(str1) + ' ' + str(str2))

    def handle_starttag(self, tag, attrs):
        self.print_debug(f"Encountered a start tag: '{tag}' with attributes {attrs}", "")

    def handle_endtag(self, tag):
        self.print_debug("Encountered an end tag :", tag)

    def handle_data(self, data):
        self.print_debug("Encountered some data  :", data)

    def handle_comment(self, data):
        self.print_debug("Comment  :", data)

    def handle_decl(self, data):
        self.print_debug("Decl     :", data)


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
#        try:
        
        film = idfa_data.create_film(title, url)
        if film is not None:
            film.medium_category = medium_category
            film.duration = duration
            print(f"Adding FILM: {film.title}")
            
#            except AttributeError as e:
#                print(f"Error: {e}")
#                Globals.error_collector.add(str(e), f"{self.title}")
            idfa_data.films.append(film)
        return film

    def add_filminfo(idfa_data, film, description, article):
        if description is not None or article is not None:
            filminfo = planner.FilmInfo(film.filmid, description, article)
            idfa_data.filminfos.append(filminfo)

    def add_film_finding_duration(self):
        if self.duration == None:
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
                elif self.in_link and  attr[0] == 'href':
                    iri_path = web_tools.uripath_to_iripath(attr[1])
                    self.url = films_hostname + iri_path
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

    def __init(self, idfa_data, film, debug_prefix='S'):
        pass


class FilmPageParser(HtmlPageParser):

    re_times = re.compile(r'(?P<day>\d+) (?P<month>\w+)\. \d\d:\d\d - \d\d:\d\d \((?P<start_time>\d\d:\d\d) - (?P<end_time>\d\d:\d\d) AMS\)')
    nl_month_by_name = {}
    nl_month_by_name['nov'] = 11
    nl_month_by_name['dec'] = 12
    compilation_by_title = {}
    
    def __init__(self, idfa_data, film, debug_prefix='F'):
        HtmlPageParser.__init__(self, idfa_data, debug_prefix)
        self.film = film
        self.debugging = True
        self.init_screening_data()

    def init_screening_data(self):
        self.screening_name = None
        self.screen = None
        self.start_date = None
        self.start_time = None
        self.end_time = None
        self.audience = 'publiek'
        self.compilation_url_path = None
        self.compilation_title = None
        self.compilation = None
        self.qa = ''
        self.extra = ''
        self.film_description = None
        self.film_article = None
        self.in_article = False
        self.in_screenings = False
        self.in_compilation_title = None
        self.in_screening = False
        self.in_screening_name = False
        self.in_times = False
        self.in_location = False
        self.in_compilation = False
        self.await_content = False

    def add_article(self, article):
        filminfos = [filminfo for filminfo in self.idfa_data.filminfos if filminfo.filmid == self.film.filmid]
        try:
            filminfo = filminfos[0]
            filminfo.article = article
        except IndexError as e:
            Globals.error_collector.add(str(e), f'No filminfo description found for: {self.film.title}')
            filminfo = planner.FilmInfo(self.film.filmid, '', article)
            self.idfa_data.filminfos.append(filminfo)

    def add_compilation(self):
        print(f'Found COMPILATION {self.compilation_url_path}')
        self.print_debug('--', f'Found COMPILATION {self.compilation_url_path}')
        if self.compilation_title:
            title = self.compilation_title
        else:
            title = self.compilation_url_path.split('/')[-1]
        iri_path = web_tools.uripath_to_iripath(self.compilation_url_path)
        compilation = self.idfa_data.create_film(title, films_hostname + iri_path)
        if compilation is not None:
            start_dt, end_dt = self.get_datetimes()
            compilation.duration = end_dt - start_dt
            compilation.medium_category = 'verzamelprogrammas'
            parser = CompilationPageParser(self.idfa_data, compilation)
            print(f'Finding details of COMPILATION {compilation.title}')
            FilmDetailsLoader.get_details_of_one_film(self.idfa_data, compilation, parser)
            self.print_debug('--', f'Adding new COMPILATION {title}')
            self.idfa_data.films.append(compilation)
            AzPageParser.add_filminfo(self.idfa_data, compilation, self.film_description, self.film_article)
            self.compilation = compilation
            self.compilation_by_title[title] = compilation
        else:
            print(f'COMPILATION already exists in list {title} - {films_hostname + iri_path}')
            categories = [f.medium_category for f in self.idfa_data.films if f.title == title]
            if len(categories) > 0:
                category = categories[0]
                if category == 'films':
                    self.print_debug('--PROBLEM', f'Compilation {title} has same title as an existing film')
                else:
                    self.print_debug('--', f'ALREADY created COMPILATION {title}')
                    self.compilation = self.compilation_by_title[title]
    
    def add_screening(self):
        start_datetime, end_datetime = self.get_datetimes()
        self.print_debug(f"--- Adding SCREENING of {self.film.title}", f"SCREEN = {self.screen}, START TIME = {start_datetime}, END TIME = {end_datetime}")
        print()
        print(f"---SCREENING OF {self.film.title}")
        print(f"--  screening name: {self.screening_name}")
        print(f"--  screen:         {self.screen}")
        print(f"--  times:          {start_datetime} - {end_datetime}")
        print(f"--  q and a:        {self.qa}")
        print(f"--  extra:          {self.extra}")
        print(f"--  audience:       {self.audience}")
        print(f"--  duration:       Film: {self.film.duration_str()}   Screening: {end_datetime - start_datetime}")
        print(f"--  category:       {self.film.medium_category}")
        print(f"--  in compilation: {self.compilation.title if self.compilation is not None else ''}")
        screening = planner.Screening(self.film, self.screen, start_datetime, end_datetime, self.qa, self.extra, self.audience, self.compilation)
        if not self.is_coinciding(screening):
            self.idfa_data.screenings.append(screening)
            print("---SCREENING ADDED")
            self.init_screening_data()
#        if self.compilation_url_path is not None:
#            self.add_compilation()

    def get_datetimes(self):
        start_datetime = datetime.datetime.combine(self.start_date, self.start_time)
        end_date = self.start_date if self.end_time > self.start_time else self.start_date + datetime.timedelta(days=1) 
        end_datetime = datetime.datetime.combine(end_date, self.end_time)
        return start_datetime, end_datetime

    def is_coinciding(self, screening):
        sep = self.debug_prefix + 2*' '
        nl = '\n'
        screening_summ = lambda s: f'{sep}{s.film.medium_category} {repr(s).rstrip(nl)} - {s.film.title} ({s.film.duration_str()}){nl}'
#        if screening.film.medium_category == 'verzamelprogrammas':
#            print(f'FIRST COMPILATION: {screening_summ(screening)}')
#            self.print_debug('--', f'FIRST COMPILATION: {screening_summ}')
#            self.crash()
        dupls = [s for s in self.idfa_data.screenings if  s.screen == screening.screen and s.start_datetime == screening.start_datetime]
        for dupl in dupls:
            print(f'DUPLICATE screening: {dupl.film.title} - {repr(dupl)}{dupl.film.url}\n{screening.film.url}')
            dupl_summ = f'\n{screening_summ(dupl)}{screening_summ(screening)}'
            self.print_debug('--', f'DUPLICATE screenings: {dupl_summ}')
            if dupl.film.filmid == screening.film.filmid and dupl.film.medium_category == 'films':
                Globals.error_collector.add('Coinciding screenings of two {dupl.film.medium_category}', f'{dupl_summ}')
                return True
            elif screening.combination_program is not None:
                return False
            elif dupl.combination_program is not None:
                return False
            elif dupl.film.medium_category != 'verzamelprogrammas' and screening.film.medium_category != 'verzamelprogrammas':
                Globals.error_collector.add('Combining films as compilation not implemented', f'{dupl_summ}')
                return True
            elif dupl.film.medium_category == 'verzamelprogrammas' and screening.film.medium_category != 'verzamelprogrammas':
                Globals.error_collector.add('Adding film to compilation not implemented', f'{dupl_summ}')
                return True
            elif screening.film.medium_category == 'verzamelprogrammas' and dupl.film.medium_category != 'verzamelprogrammas':
                Globals.error_collector.add('Adding film to compilation not implemented', f'{dupl_summ}')
                return True
            self.crash()

    def crash(self):
        none_by_key = {}
        Globals.debug_recorder.write_debug()
        none_by_key['666']

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        # Parse for filminfo data.
        if self.in_article and tag == 'meta':
            for attr in attrs:
                if attr == ('name', 'description'):
                    self.await_content = True
                elif self.await_content and attr[0] == 'content':
                    self.await_content = False
                    self.in_article = False
                    article = attr[1]
                    self.print_debug(f"Found ARTICLE of {self.film.title}:", f"{article}")
                    self.add_article(article)

        # Parse for screening data.
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
                self.compilation_url_path = attr[1]
                self.add_compilation()

        # Parse for compilation data.
        if tag == 'h1':
            attr = attrs[0]
            if attr[0] == 'class' and attr[1].startswith('hero-module__title_'):
                self.print_debug('--', 'Start looking for COMPILATION title')
                self.in_compilation_title = True

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        # Parse for filminfo data.
        if tag == 'title':
            self.in_article = True

        # Parse for screening data.
        elif self.in_screening and tag == 'section' and self.start_date is not None:
            self.in_screening = False
            self.add_screening()
        elif tag == 'body':
            self.in_screenings = False
 
    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        # Parse for screening data.
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
                Globals.error_collectot.add('Pattern not recognized', f'{self.film.title}: \'{data}\'.')
        elif self.in_location:
            self.in_location = False
            self.screen = self.idfa_data.get_screen(festival_city, data)
            self.in_compilation = True

        # Parse for compilation data.
#        if self.in_compilation_title:
#            self.in_compilation_title = False
#            self.compilation_title = data
#            self.print_debug('--', f'Found COMPILATION TITLE: \'{data}\'')


class CompilationPageParser(FilmPageParser):

    def __init__(self, idfa_data, film):
        print(f'Passing {film.title} to CompilationPageParser')
        FilmPageParser.__init__(self, idfa_data, film, 'CP')
        self.print_debug('--', f'After PASSING title is {self.film.title}')
        self.screened_films = []
        self.duration = None
        self.film_description = None
        self.film_article = None
        self.screenings = []        

    def add_article(self, article):
        filminfo = planner.FilmInfo(self.film.filmid, 'Verzamelprogramma', article)
        self.idfa_data.filminfos.append(filminfo)

    def add_compilation(self):
        print(f'Compilation within compilation not added.')
        self.print_debug('--', 'Recursive instantion of COMPILATION {self.compilation_url_path} prevented.')

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
        FilmPageParser.handle_starttag(self, tag, attrs)
#        if tag == 'h1':
#            if attrs[0] == 'class' and attrs[1].startswith('hero-module__title_'):
#                self.print_debug('--', 'Start looking for COMPILATION title')
#                self.in_compilation_title = True
 
    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
        if self.in_compilation_title:
            self.in_compilation_title = False
            self.compilation_title = data
            self.print_debug('--', f'Found COMPILATION TITLE: \'{data}\'')


class IdfaData(planner.FestivalData):

    def _init__(self, plandata_dir):
        planner.FestivalData.__init__(self, plandata_dir)
        self.combination_title_by_url = {}


if __name__ == "__main__":
    main()
    