#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load films, screens and screenings from the actual NNF website.

Created on Fri Oct  2 21:35:14 2020

@author: maarten
"""

import datetime
import os
import re
from enum import Enum, auto
from html.parser import HTMLParser

from Shared.application_tools import DebugRecorder, ErrorCollector, Counter, comment
from Shared.parse_tools import ScreeningKey, FileKeeper, try_parse_festival_sites, HtmlPageParser
from Shared.planner_interface import UnicodeMapper, Film, Screening, FestivalData, FilmInfo
# from Shared.web_tools import get_charset
from Shared.web_tools import get_encoding_from_file, iri_slug_to_url, UrlFile

festival = 'NFF'
festival_year = 2023
festival_city = 'Utrecht'
az_page_count = 6

# Files
file_keeper = FileKeeper(festival, festival_year)
debug_file = file_keeper.debug_file

# Directories.
webdata_dir = file_keeper.webdata_dir
plandata_dir = file_keeper.plandata_dir

# Filename formats.
# az_copy_paste_file_format = os.path.join(webdata_dir, "copy_paste_az_{:02d}.txt")
film_file_format = file_keeper.film_file_format

# Files.
filmdata_file = os.path.join(plandata_dir, 'filmdata.csv')
filminfo_xml_file = os.path.join(plandata_dir, 'filminfo.xml')
az_screenshot_file = os.path.join(webdata_dir, 'az-screencopies.txt')

# URL information.
nff_hostname = "https://www.filmfestival.nl"
films_webroot = "https://www.filmfestival.nl/en/films/"
premiere_prefix = "festivalpremiere-"

# Global unicode mapper.
unicode_mapper = UnicodeMapper()

# Application tools.
error_collector = ErrorCollector()
debug_recorder = DebugRecorder(debug_file)
counter = Counter()


def main():
    # initialize a festival data object.
    festival_data: NffData = NffData(plandata_dir)

    # Setup counters.
    counter.start('screenings')
    counter.start('films')
    counter.start('film links')

    # Try parsing the websites.
    try_parse_festival_sites(parse_nff_sites, festival_data, error_collector, debug_recorder, festival, counter)


def parse_nff_sites(festival_data):
    comment("Parsing AZ pages.")
    # get_films(festival_data)
    films_loader = FilmsLoader(az_screenshot_file)
    films_loader.get_films(festival_data)

    # comment("Parsing premiêre pages.")
    # premieres_loader = PremieresLoader()
    # premieres_loader.get_screenings(festival_data)
    #
    # comment("Parsing regular film pages.")
    # screenings_loader = ScreeningsLoader()
    # screenings_loader.get_screenings(festival_data)


def get_films(festival_data):
    az_url_path = 'programma'
    az_url = iri_slug_to_url(nff_hostname, az_url_path)
    az_file = file_keeper.az_file()
    url_file = UrlFile(az_url, az_file, error_collector, debug_recorder, byte_count=200)
    az_html = url_file.get_text()
    if az_html is not None:
        AzPageParser(festival_data).feed(az_html)


class AzPageParser(HtmlPageParser):
    class AzParseState(Enum):
        IDLE = auto()
        DONE = auto()

    def __init__(self, festival_date):
        super().__init__(festival_date, debug_recorder, 'AZ', debugging=True)


class NffFilm:
    
    def __init__(self, title, duration, description, directors, competitions):
        self.title = title
        self.duration = duration
        self.description = description
        self.directors = directors
        self.competitions = competitions
        
    def __str__(self):
        return ";".join([self.title,
                         str(Film.duration_to_minutes(self.duration)),
                         self.description,
                         self.directors,
                         self.competitions]) + ";"

    
class NffScreening(Screening):
    
    def __init__(self, screening, subscreenings):
        film = screening.film
        screen = screening.screen
        start_datetime = screening.start_datetime
        end_datetime = screening.end_datetime
        qa = screening.q_and_a
        extra = screening.extra
        audience = screening.audience
        Screening.__init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience)
        self.subscreenings = subscreenings
        self.exclude = False


class Subscreening:
    
    def __init__(self, time, title, description):
        self.time = time
        self.title = title
        self.description = description

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash((self.time, self.title, self.description))


class FilmsLoader:
    nl_month_by_name = {"september": 9}

    filmparts_re = re.compile(
        r"""
            ^.*Films\ from\ A\ to\ Z  # Ignorable head stuff
            (?P<filmparts>.*)         # Information of each film
            \n1\n\ \n.*$              # Ignorable tail stuff
        """, re.DOTALL|re.VERBOSE
    )
    film_re = re.compile(
        r"""
             \n\ \n(?P<title>[^\n]*)\n\n           # Title is preceeded by a line consisting of one space
             Duration:\ (?P<duration>[0-9]+)min\n  # Duration in minutes
             (?P<description>[^\n]*)\n             # Description is one line of text following Duration
             Director\(s\):\ (?P<directors>[^\n]*) # Directors, optionally followed by competitions
        """, re.DOTALL|re.VERBOSE
    )
    competitions_re = re.compile(
        r"""
            (?P<directors>[^\n]*)                     # Directors list, header stripped off
            \ Competitions:\ (?P<competitions>[^\n]*) # Pattern when competitions list indeed exists
        """, re.VERBOSE
    )
    screening_re = re.compile(
        r"""
            \n(?P<title>[^\n]*)\nDatum\n        # Title
            (?P<month_day>\d+)\s+               # Day of month
            (?P<month_name>[a-z]+)\s+           # Dutch name of month
            om\s+(?P<start_time>\d\d:\d\d)\n    # Start time
            Locatie\s+(?P<location>[^\n]+)\n    # Location
        """, re.DOTALL | re.VERBOSE
    )
    num_screen_re = re.compile(r'^(?P<theater>.*?) (?P<number>\d+)$')
    name_screen_re = re.compile(r'^(?P<theater>.*?) - (?P<name>.+)$')

    def __init__(self, az_file):
        self.title = None
        self.start_dt = None
        self.screen = None
        with open(az_file, 'r') as f:
            az_text = f.read()
        self.az_text = az_text
    
    def get_films(self, nff_data):
        
        # Parse AZ page.
        self.parse_az_page(nff_data)
        # nff_data.write_nff_films()
        
        # # Convert NFF films to the format expected by the C# planner.
        # nff_data.fill_films_list()
        # nff_data.write_films()

    def parse_az_page(self, festival_data):
        screening_matches = [match for match in self.screening_re.finditer(self.az_text)]
        groups = [m.groupdict() for m in screening_matches]
        for group in groups:
            self.title = group['title']
            month = self.nl_month_by_name[group['month_name']]
            start_date = datetime.date.fromisoformat(f'{festival_year}-{month:02d}-{group["month_day"]}')
            start_time = datetime.time.fromisoformat(group['start_time'])
            screen_parse_name = group['location']
            theater_parse_name, screen_abbreviation = self.split_location(screen_parse_name)
            self.screen = festival_data.get_screen(
                festival_city,
                screen_parse_name,
                theater_parse_name=theater_parse_name,
                screen_abbreviation=screen_abbreviation
            )
            self.start_dt = datetime.datetime.combine(start_date, start_time)
            counter.increase('screenings')

    def split_location(self, location):
        theater_parse_name = location
        screen_abbreviation = None
        num_match = self.num_screen_re.match(location)
        if num_match:
            theater_parse_name = num_match.group(1)
            screen_abbreviation = num_match.group(2)
        else:
            name_match = self.name_screen_re.match(location)
            if name_match:
                theater_parse_name = name_match.group(1)
                screen_abbreviation = name_match.group(2)
        return theater_parse_name, screen_abbreviation

    # def parse_az_pages(self, nff_data):
    #     pass
    #     for page_number in range(self.page_count):
    #         az_file = az_copy_paste_file_format.format(page_number)
    #         print(f"Searching {az_file}...", end="")
    #         try:
    #             with open(az_file, 'r') as f:
    #                 az_text = f.read()
    #             film_count = self.parse_one_az_page(az_text, nff_data.nff_films)
    #             print(f" {film_count} films found")
    #         except FileNotFoundError as e:
    #             error_collector.add(e, "while parsing az pages in FilmsLoader")
    
    def parse_one_az_page(self, az_text, nff_films):
        filmparts = self.filmparts_re.match(az_text)
        if filmparts is not None:
            filmparts_text = filmparts.group('filmparts')
            film_count = 0
            for film_match in self.film_re.finditer(filmparts_text):
                film_count += 1
                duration = datetime.timedelta(minutes=int(film_match.group('duration')))
                description = re.sub(';', ',', film_match.group('description'))
                directors = film_match.group('directors')
                competitions_match = self.competitions_re.match(directors)
                if competitions_match is not None:
                    directors = competitions_match.group('directors')
                    competitions = competitions_match.group('competitions')
                else:
                    competitions = ""
                nff_films.append(NffFilm(film_match.group('title'),
                                         duration,
                                         description,
                                         directors,
                                         competitions))
            return film_count


class PremieresLoader:
    
    def __init__(self):
        self.film = None
        self.url = ""
        
    def print_debug(self, str1, str2):
        debug_recorder.add('AZ ' + str(str1) + ' ' + str(str2))

    def get_screenings(self, nff_data):
        nff_data.read_screens()
        files_read_count = 0
        for film in nff_data.films:
            self.film = film
            self.url = re.sub("en/films/", premiere_prefix, film.url)
            url_file = os.path.join(webdata_dir, self.url.split("/")[3]) + ".html"
            if os.access(url_file, os.F_OK):
                print(f"Now reading {self.url}")
                self.get_screenings_of_one_film(url_file, nff_data)
                files_read_count += 1
        print(f"\nDone reading screenings of {files_read_count} premiêre.")
        nff_data.write_new_screens()
        nff_data.write_screenings()

    def get_screenings_of_one_film(self, film_html_file, nff_data):
        title = self.film.title
        if os.path.isfile(film_html_file):
            self.print_debug("--  Analysing premiêre page of title:", title)
            premiere_parser = PremierePageParser(self.film, nff_data)
            charset = get_encoding_from_file(film_html_file, debug_recorder)
            with open(film_html_file, 'r', encoding=charset) as f:
                text = '\n' + '\n'.join([line for line in f])
            premiere_parser.feed(text)


class ScreeningsLoader:
    
    def __init__(self):
        self.nff_screenings = []
        self.films_by_samescreening = None
        self.subsset_by_screening = None
        self.common_keys = None
        
    def print_debug(self, str1, str2):
        debug_recorder.add('RF ' + str(str1) + ' ' + str(str2))

    def get_screenings(self, nff_data):
        self.parse_film_pages(nff_data)
        self.add_unique_screenings(nff_data)
        nff_data.write_screenings()
        
    def parse_film_pages(self, nff_data):
        for film in nff_data.films:
            film_file = film_file_format.format(film.film_id)
            print(f"Now reading {film_file} - {film.title} ({film.duration_str()})")
            try:
                charset = get_encoding_from_file(film_file, debug_recorder)
                with open(film_file, 'r', encoding=charset) as f:
                    film_text = f.read()
                self.parse_one_film_page(film, film_text, nff_data)
            except FileNotFoundError as e:
                error_collector.add(e, "while parsing film pages in ScreeningsLoader")
            
    def parse_one_film_page(self, film, film_text, nff_data):
        self.print_debug(f"--  Analysing regular film page of title:", "{film.title} ({film.duration_str()})")
        film_parser = FilmPageParser(film, nff_data, self.nff_screenings)
        film_parser.feed(film_text)
        
    def add_unique_screenings(self, nff_data):
        """
        Repair all coinciding screenings that are listed on the web-site.
        
        The following constructions exist on the NFF 2020 web-site:
        - Premiêres
            A number of films have premiere screenings in 102 theaters through
            the country. On the film's site it looks like there is one
            screening in a theater called '102 filmtheaters door het land'. A
            link leads to a "premiêre site", where the screenings in all towns
            are listed.
        - Combination programs
            Some films are screened as part of a combination program. On the
            site of each of these films the whole program is listed as one
            screening. This leads to a number of coinciding screenings equal
            to the number of films in the program.
            Within these screenings, a subscreening in found for each film in
            the program. Since the combination programs have no name, only the
            subscreeninings are loaded, after being de-duplicated.
        - Walk-in events
            Some screenings are way longer then the film that is screened. If
            more than one of such screenings coincide, it is assumed that
            these films are continuously screened on separate screens within
            the theater. Since those screens are not explicitly named, new
            screens are created, based on theater abbreviation and film title,
            in order to load unique screenings.
            In the code, the original screenings are referred to as walk-in
            events.
        - Repeater events
            A repeater event is a screening that reapeats the same film as
            subscreenings.
            The subcreenings are loaded, not the repeater event.
        - Regular screenings
            Regular screenings are unique screenings where one film is
            screened once.
            All screenings on premiêre sites are regular.
            Regular screenings are loaded as is.
            
        A more simple way could have been:
        - Prefer subscreenings above screenings.
        - De-duplicate coinciding screenings with different films by creating
            new screens.
        - De-duplicate remaining screenings by keeping one of each duplicate
            combination of screen, start-time and end-time.
        """

        film_by_en_name = {}

        def main():
        
            # Get films and subscreenings of screenings with equal screen, start time and end time.
            get_films_by_samescreening()
            print(f"\n{len(self.films_by_samescreening)} coinsiding film screenings.")
    
            # Get subscreenings of screenings with more than one subscreening.
            get_subscreeningsset_by_screening()
            print(f"{len(self.subsset_by_screening)} compilations and walk-ins.")
            
            # Combine the screening keys with multiple films with those with compilations.
            get_common_keys()
    
            # Add the screenings with no simultaneous other screening.
            self.regular_count = 0
            self.repeater_count = 0
            add_singlet_screenings()
            
            # Add walk-in screenings and combination programs.
            self.combi_count = 0
            self.walkin_count = 0
            add_unmultipled_screenings()
            
            print()
            print(f"{self.regular_count:3d} Regular screenings added.")
            print(f"{self.repeater_count:3d} Repeater instances added.")
            print(f"{self.combi_count:3d} Combination program parts added.")
            print(f"{self.walkin_count:3d} Walk-in events added.")
            print()

        def print_heading(msg):
            text = "-- " + msg + ":"
            print(f"{text:24}", end="")
        
        def find_film(name, descr, films):
            if name in film_by_en_name.keys():
                return film_by_en_name[name]
            films = [f for f in films if f.title == name]
            if len(films) == 1:
                film_by_en_name[name] = films[0]
                return films[0]
            nff_films = [n for n in nff_data.nff_films if n.description == descr]
            if len(nff_films) == 1:
                nff_film = nff_films[0]
                films = [f for f in nff_data.films if f.title == nff_film.title]
                if len(films) == 1:
                    film_by_en_name[name] = films[0]
                    return films[0]
            return None
        
        def add_screening_from_sub(key, sub, films, is_walk_in=False):
            film = find_film(sub.title, sub.description, films)
            if film is not None:
                if is_walk_in:
                    screen = nff_data.get_screen("Utrecht", f"{key.screen}-{film.title}")
                    start_dt = key.start_dt
                    end_dt = key.end_dt
                else:
                    screen = key.screen
                    start_date = key.start_dt.date()
                    start_time_str = sub.time
                    start_time = datetime.time.fromisoformat(start_time_str)
                    start_dt = datetime.datetime.combine(start_date, start_time)
                    end_dt = start_dt + film.duration
                add_screening(film, screen, start_dt, end_dt)
            else:
                error_collector.add(f"Subscreening name {sub.name} not found as film",
                                            "in add_screening_from_sub")
                
        def add_screening(film, screen, start_dt, end_dt, dry_run=False):
            qa = ""
            extra = ""
            audience = "publiek"
            screening = Screening(film, screen, start_dt, end_dt, qa, extra, audience)
            screening_minutes = f"({Film.duration_to_minutes(end_dt - start_dt)}')"
            description = "{:24} {} {}-{} {:8}{} ({})".format(
                    str(screen),
                    start_dt.date(),
                    start_dt.time().isoformat(timespec='minutes'),
                    end_dt.time().isoformat(timespec='minutes'),
                    screening_minutes,
                    film.title,
                    film.duration_str())
            print(description, end="")
            if not dry_run:
                nff_data.screenings.append(screening)
                print(" ---SCREENING ADDED")
            else:
                print(" ---NOT ADDED")

        def get_films_by_samescreening():
            unique_films_by_screening = {}
            for film, key in [(s.film, ScreeningKey(s)) for s in self.nff_screenings]:
                if key in unique_films_by_screening.keys():
                    unique_films_by_screening[key].add(film)
                else:
                    unique_films_by_screening[key] = set([film])
            self.films_by_samescreening = {k: films for (k, films) in unique_films_by_screening.items() if len(films) > 1}

        def get_subscreeningsset_by_screening():
            subs_by_screening = {}
            for subs, key in [(s.subscreenings, ScreeningKey(s)) for s in self.nff_screenings]:
                if key in subs_by_screening:
                    subs_by_screening[key].append(subs)
                else:
                    subs_by_screening[key] = [subs]
            compilations = [(k, s) for (k, s) in subs_by_screening.items() if len(s) > 1]
            self.subsset_by_screening = {}
            for key, subslist in compilations:
                subsset = []
                for subs in subslist:
                    if not (subs in subsset):
                        subsset.append(subs)
                self.subsset_by_screening[key] = subsset
        
        def get_common_keys():
            self.common_keys = set(self.films_by_samescreening.keys() & set(self.subsset_by_screening.keys()))
            common_count = len(self.common_keys)
            print(f"{common_count} Combined coinsiding film screenings and compilations.")
            but = " but no compilation program"
            comment = "while combining coinsiding films and compilations"
            excess_samescreening_count = len(self.films_by_samescreening) - common_count
            if excess_samescreening_count > 0:
                error_collector.add(f"{excess_samescreening_count} screenings exist with coinsiding films {but}",
                                            comment)
            excess_multi_subscreenings_count = len(self.subsset_by_screening) - common_count
            if excess_multi_subscreenings_count > 0:
                error_collector.add(f"{excess_multi_subscreenings_count} screenings exist with multiple subscreenings {but}",
                                            comment)
        
        def add_singlet_screenings():
            all_keys = [ScreeningKey(s) for s in self.nff_screenings]
            singlet_keys = set(all_keys) - set(self.films_by_samescreening.keys()) - set(self.subsset_by_screening.keys())
            for key in singlet_keys:
                singlet_screenings = [s for s in self.nff_screenings if (ScreeningKey(s) == key)]
                if len(singlet_screenings) != 1:
                    error_collector.add(f"Regular screening has {len(singlet_screenings)} variations",
                                                "while adding regular screenings")
                screening = singlet_screenings[0]
                if len(screening.subscreenings) > 1:
                    print(f"- Event at {key}:")
                    for sub in screening.subscreenings:
                        print_heading("repeater event")
                        add_screening_from_sub(key, sub, [screening.film])
                        self.repeater_count +=1
                else:
                    print_heading("regular screening")
                    add_screening(screening.film, screening.screen, screening.start_datetime, screening.end_datetime)
                    self.regular_count += 1
        
        def add_unmultipled_screenings():
            for key in self.common_keys:
                films = self.films_by_samescreening[key]
                subsset = self.subsset_by_screening[key]
                print(f"- Event at {key}:")
                for subs in subsset:
                    if len(subs) > 1:
                        for sub in subs:
                            print_heading("combination program")
                            add_screening_from_sub(key, sub, films)
                            self.combi_count += 1
                    elif len(subs) == 1:
                        sub = subs[0]
                        print_heading("walk-in event")
                        add_screening_from_sub(key, sub, films, True)
                        self.walkin_count += 1
        
        main()


class HtmlPageParser(HTMLParser):
    
    def __init__(self, film, nff_data):
        HTMLParser.__init__(self)
        self.film = film
        self.nff_data = nff_data
        self.init_screening_data()
        self.debugging = False
        self.debug_text = ""
        self.in_date = False
        self.in_town = False
        self.in_location = False
        self.in_time = False
        self.en_month_by_abbr = {}
        self.en_month_by_abbr["Sep"] = 9
        self.en_month_by_abbr["Oct"] = 10
        self.en_month_by_abbr["September"] = 9
        self.en_month_by_abbr["October"] = 10
        self.en_month_by_abbr['November'] = 11
        self.en_month_by_abbr['December'] = 12
        self.nl_month_by_name = {}
        self.nl_month_by_name["september"] = 9
        self.nl_month_by_name["oktober"] = 10

    def print_debug(self, str1, str2):
        if self.debugging:
            debug_recorder.add('F ' + str(str1) + ' ' + str(str2))

    def init_screening_data(self):
        self.location = None
        self.screen = None
        self.start_time = None
        self.end_time = None
        self.start_dt = None
        self.end_dt = None
        self.audience = "publiek"
        self.qa = ""
        self.extra = ""

    def new_screening(self):
        pass
    
    def add_screening(self, dry_run=False):
        print()
        print(f"---SCREENING OF {self.film.title}")
        print(f"--  screen:     {self.screen}")
        print(f"--  start date: {self.start_date}")
        print(f"--  start time: {self.start_time}")
        print(f"--  duration:   {self.film.duration_str()}")
        print(f"--  audience:   {self.audience}")
        print(f"--  category:   {self.film.medium_category}")
        print(f"--  q and a:    {self.qa}")
        print(f"--  extra:      {self.extra}")
        start_datetime = datetime.datetime.combine(self.start_date, self.start_time)
        if self.start_dt is not None and self.end_dt is not None:
            start_datetime = self.start_dt
            end_datetime = self.end_dt
        elif self.end_time is None:
            end_datetime = start_datetime + self.film.duration
            self.end_time = datetime.time(end_datetime.hour, end_datetime.minute)
        else:
            end_date = self.start_date if self.end_time > self.start_time else self.start_date + datetime.timedelta(days=1) 
            end_datetime = datetime.datetime.combine(end_date, self.end_time)
            self.print_debug("--- ", f"START TIME = {start_datetime}, END TIME = {end_datetime}")
        screening = Screening(self.film, self.screen, start_datetime, end_datetime, self.qa, self.extra, self.audience)
        if not dry_run:
            self.nff_data.screenings.append(screening)
            print("---SCREENING ADDED")
        else:
            print("---NOT ADDED")
        self.init_screening_data()
        return screening

    def set_screen(self, city, location):
        self.screen = self.nff_data.get_screen(city, location)

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
   
    
class PremierePageParser(HtmlPageParser):

    re_date = re.compile("\d+ \w+")
    re_time = re.compile("\d+:\d+")

    def __init__(self, film, nff_data):
        HtmlPageParser.__init__(self, film, nff_data)
        self.city = None
           
    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
        if self.in_town and tag == "strong":
            self.in_location = True
        if tag == "h4":
            self.in_date = True
            self.debugging = True
        for attr in attrs:
            self.print_debug("Handling attr:      ", attr)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)
        if self.in_location and tag == "strong":
            self.in_location = False
        if self.in_date:
            if tag == "h4":
                self.in_date = False
                self.debugging = False

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
        if self.in_date:
            self.print_debug("--", f"DATE found: {data}")
            start_date_str = ""
            try:
                start_date_str = self.re_date.findall(data)[0]
                month = self.nl_month_by_name[start_date_str.split(" ")[1]]
                day = int(start_date_str.split(" ")[0])
                self.start_date = datetime.date(festival_year, month, day)
            except IndexError:
                self.print_debug("--", f"ERROR can't construct date from '{data}'.")
        if data == "Amsterdam":
            self.city = data
            self.in_town = True
            self.debugging = True
        if data == "Apeldoorn":
            self.city = data
            self.in_town = False
            self.in_time = False
            self.debugging = False
        if self.in_time and data.strip().startswith("Start:"):
            self.print_debug("-- ", f"START TIME found: {data}")
            start_time_str = None
            try:
                start_time_str = self.re_time.findall(data)[0]
                hour = int(start_time_str.split(":")[0])
                minute = int(start_time_str.split(":")[1])
                self.start_time = datetime.time(hour, minute)
                self.in_time = False
                self.set_screen(self.city, self.location)
                self.add_screening()
            except IndexError:
                self.print_debug("-- ", f"ERROR can't construct time from: '{data}'.")
        if self.in_location:
            location = data.strip()
            if len(location) > 0:
                self.print_debug("LOCATION", location)
                self.location = location
                self.in_location = False
                self.print_debug("-- ", "LEAVING LOCATION")
                self.in_time = True


class FilmPageParser(HtmlPageParser):

    re_datetime = re.compile("(?P<day>\d+) (?P<month>\w+) (?P<starttime>\d\d:\d\d) - (?P<endtime>\d\d:\d\d)")
    re_extratime = re.compile("^(?P<time>\d\d:\d\d)$")
    re_online = re.compile(
    r"""
        ^available\ from
        \ (?P<start_day>\d+)\ (?P<start_month>\w+)\ (?P<start_time>\d\d:\d\d)
        \ until
        \ (?P<end_day>\d+)\ (?P<end_month>\w+)\ (?P<end_time>\d\d:\d\d)$
    """, re.VERBOSE)

    def __init__(self, film, nff_data, nff_screenings):
        HtmlPageParser.__init__(self, film, nff_data)
        self.debugging = True
        self.in_online = True;
        self.nff_screenings = nff_screenings
 
    def init_screening_data(self):
        HtmlPageParser.init_screening_data(self)
        self.in_extratimes = False
        self.in_extrafilm = False
        self.await_descr = False
        self.in_descr = False
        self.last_tag = None
        self.subscreenings = []
        self.extra_time = None
        self.part_name = None
        self.part_descr = None

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
        self.last_tag = tag
        if self.in_extratimes and tag == "h3":
            self.in_extratimes = False
            self.set_screen("Utrecht", self.location)
            if self.screen.abbr == "102filmtheatersdoorhetland":
                self.print_debug("-- ", f"NATIONAL PREMIERE {self.film.title} REFERENCE skipped")
            else:
                subscreenings = self.subscreenings
                screening = self.add_screening(True)
                self.nff_screenings.append(NffScreening(screening, subscreenings))
                self.print_debug("-- ", "{} SUBSCREENINGS: {}".format(
                        len(subscreenings),
                        ", ".join([f"{sub.time}/{sub.title}" for sub in subscreenings])))
        if self.in_extratimes and tag == "h4":
            self.in_extrafilm = True
        if self.await_descr and tag == "p":
            self.await_descr = False
            self.in_descr = True
            self.part_descr = ""

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)
        if self.in_descr and tag == "p":
            self.in_descr = False
            self.part_descr = self.part_descr.strip()
            self.print_debug("-- ", f"SUBSCREENING found: {self.extra_time} {self.part_name} - '{self.part_descr}'")
            self.subscreenings.append(Subscreening(self.extra_time, self.part_name, self.part_descr))
            self.extra_time = None
            self.part_descr = None
            self.part_name = None
 
    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
        stripped_data = data.strip()
        if self.in_online and stripped_data.startswith("available"):
            self.in_online = False
            self.print_debug("--", f"ONLINE screening of {self.film} found: '{stripped_data}'")
            m = self.re_online.match(stripped_data)
            if m is not None:
                start_day = int(m.group('start_day'))
                start_month = self.en_month_by_abbr[m.group('start_month')]
                start_time = m.group('start_time')
                self.start_date = datetime.date(festival_year, start_month, start_day)
                self.start_time = datetime.time.fromisoformat(start_time)
                end_day = int(m.group('end_day'))
                end_month = self.en_month_by_abbr[m.group('end_month')]
                end_time = m.group('end_time')
                end_date = datetime.date(festival_year, end_month, end_day)
                self.end_time = datetime.time.fromisoformat(end_time)
                self.start_dt = datetime.datetime.combine(self.start_date, self.start_time)
                self.end_dt = datetime.datetime.combine(end_date, self.end_time)
                self.set_screen('', 'On-Line')
                self.add_screening()
            else:
                self.print_debug("---", f"ERROR: {self.re_online} NOT MATCHED")
        elif data == "On location":
            self.in_location = True
        elif self.in_location and len(stripped_data) > 0:
            self.location = stripped_data
            self.print_debug("-- ", f"LOCATION found: {self.location}")
            self.in_location = False
            self.in_time = True
        elif self.in_time and len(stripped_data) > 0:
            self.print_debug("-- ", f"TIMES found: {data}")
            self.in_time = False
            self.in_extratimes = True
            m = self.re_datetime.search(stripped_data)
            day = int(m.group('day'))
            month = self.en_month_by_abbr[m.group('month')]
            self.start_date = datetime.date(festival_year, month, day)
            self.start_time = datetime.time.fromisoformat(m.group('starttime'))
            self.end_time = datetime.time.fromisoformat(m.group('endtime'))
        elif self.in_extratimes and self.last_tag == "div" and len(stripped_data) > 0:
            m = self.re_extratime.match(stripped_data)
            self.print_debug("-- ", f"LOOKING for an extra time in '{stripped_data}'")
            if m is not None:
                self.print_debug("--- ", f"Found MATCH {m.group('time')}")
                self.extra_time = m.group('time')
        elif self.in_extrafilm:
            self.part_name = stripped_data
            self.in_extrafilm = False
            self.await_descr = True
        elif self.in_descr:
            self.part_descr += data


class NffData(FestivalData):

    # Dictionary for unconstructable URL's.
    url_by_title = {}
    url_by_title['Flodder'] = 'https://www.filmfestival.nl/en/films/flodder-5'
    url_by_title['De Futurotheek'] = 'https://www.filmfestival.nl/en/films/futurotheek'
    url_by_title['Gooische vrouwen'] = 'https://www.filmfestival.nl/en/archive/gooische-vrouwen-2'
    url_by_title['Teledoc Campus - When You Hear the Divine Call'] = 'https://www.filmfestival.nl/en/films/teledoc-campus-a-divine-call'
    url_by_title['The Undercurrent'] = 'https://www.filmfestival.nl/en/films/-1'

    def __init__(self, plan_dir):
        super().__init__(festival_city, plan_dir)
        self.nff_films = []

    def __repr__(self):
        return "\n".join([str(film) for film in self.nff_films])

    def fill_films_list(self):
        filmid = 0
        for nff_film in self.nff_films:
            filmid += 1
            seqnr = filmid
            title = nff_film.title
            url = self.get_url(nff_film.title)
            film = Film(seqnr, filmid, title, url)
            film.medium_category = "films"
            film.duration = nff_film.duration
            self.films.append(film)
            self.add_filminfo(filmid, nff_film.description)

    def get_url(self, title):
        if title in self.url_by_title.keys():
            return self.url_by_title[title]
        lower = title.lower()
        ascii_string = unicode_mapper.toascii(lower)
        disquoted = re.sub(r'["\']+', '', ascii_string)
        connected = re.sub(r'\W+', '-', disquoted)
        frontstripped = re.sub(r'^\W+', '', connected)
        stripped = re.sub(r'\W+$', '', frontstripped)
        url = films_webroot + stripped
        return url

    def write_nff_films(self):
        with open(filmdata_file, 'w') as f:
            text = repr(self) + "\n"
            f.write(text)
        print(f"\nDone writing {len(self.nff_films)} records to {filmdata_file}.\n")

    def add_filminfo(self, filmid, description):
        filminfo = FilmInfo(filmid, description, '')
        self.filminfos.append(filminfo)


if __name__ == "__main__":
    main()
