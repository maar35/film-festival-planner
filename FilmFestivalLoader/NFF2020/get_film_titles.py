#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct  2 21:35:14 2020

@author: maarten
"""

import sys
import re
import os
from html.parser import HTMLParser
import datetime
import inspect

sys.path.insert(0, "/Users/maarten/Projects/FilmFestivalPlanner/FilmFestivalLoader/PlannerInterface")
import planner_interface as planner

# Parameters.
festival_year = 2020
az_page_count = 6

# Directories.
project_dir = os.path.expanduser("~/Documents/Film/NFF/NFF2020")
webdata_dir = os.path.join(project_dir, "_website_data")
plandata_dir = os.path.join(project_dir, "_planner_data")

# Filename formats.
az_copy_paste_file_format = os.path.join(webdata_dir, "copy_paste_az_{:02d}.txt")
film_file_format = os.path.join(webdata_dir, "filmpage_{:03d}.html")

# Files.
filmdata_file = os.path.join(plandata_dir, "filmdata.csv")
films_file = os.path.join(plandata_dir, "films.csv")
screens_file = os.path.join(plandata_dir, "screens.csv")
screenings_file = os.path.join(plandata_dir, "screenings.csv")
debug_file = os.path.join(plandata_dir, "debug.txt")

# URL information.
films_webroot = "https://www.filmfestival.nl/en/films/"
premiere_prefix = "festivalpremiere-"

# Regular expressions.
filmparts_re = re.compile(
r"""
    ^.*Films\ from\ A\ to\ Z  # Ignorable head stuff
    (?P<filmparts>.*)         # Information of each film
    \n1\n\ \n.*$              # Ignorable tail stuff
""", re.DOTALL|re.VERBOSE)
film_re = re.compile(
r"""
     \n\ \n(?P<title>[^\n]*)\n\n           # Title is preceeded by a line consisting of one space
     Duration:\ (?P<duration>[0-9]+)min\n  # Duration in minutes
     (?P<description>[^\n]*)\n             # Description is one line of text following Duration
     Director\(s\):\ (?P<directors>[^\n]*) # Directors, optionally followed by competitions
""", re.DOTALL|re.VERBOSE)
competitions_re = re.compile(
r"""
    (?P<directors>[^\n]*)                     # Directors list, header stripped off
    \ Competitions:\ (?P<competitions>[^\n]*) # Pattern when competitions list indeed exists
""", re.VERBOSE)
re_date = re.compile("\d+ \w+")
re_time = re.compile("\d+:\d+")
re_datetime = re.compile("(?P<day>\d+) (?P<month>\w+) (?P<starttime>\d\d:\d\d) - (?P<endtime>\d\d:\d\d)")
re_extratime = re.compile("^(?P<time>\d\d:\d\d)$")

# Global unicode mapper.
unicode_mapper = planner.UnicodeMapper()

# Dictionary for unconstructable URL's.
url_by_title = {}
url_by_title['Flodder'] = 'https://www.filmfestival.nl/en/films/flodder-5'
url_by_title['De Futurotheek'] = 'https://www.filmfestival.nl/en/films/futurotheek'
url_by_title['Gooische vrouwen'] = 'https://www.filmfestival.nl/en/archive/gooische-vrouwen-2'
url_by_title['Teledoc Campus - When You Hear the Divine Call'] = 'https://www.filmfestival.nl/en/films/teledoc-campus-a-divine-call'
url_by_title['The Undercurrent'] = 'https://www.filmfestival.nl/en/films/-1'


def main():
    # Initialize globals.
    Globals.error_collector = ErrorCollector()
    Globals.debug_recorder = DebugRecorder()
    
    # initialize a festival data object.
    festival_data = FestivalData()
    
    comment("Parsing AZ pages.")
    films_loader = FilmsLoader(az_page_count)
    films_loader.get_films(festival_data)
    
    comment("Parsing premiêre pages.")
    premieres_loader = PremieresLoader()
    premieres_loader.get_screenings(festival_data)
    
    comment("Parsing generic film pages.")
    screenings_loader = ScreeningsLoader()
    screenings_loader.get_screenings(festival_data)
    
    if(Globals.error_collector.error_count() > 0):
        comment("Encountered some errors:")
        print(Globals.error_collector)
        
    comment("Done laoding NFF data.")
    festival_data.write_screens()
    festival_data.write_screenings()
    Globals.debug_recorder.write_debug()


def comment(text):
    print("\n{}  - {}".format(datetime.datetime.now(), text))

def get_url(title):
    if title in url_by_title.keys():
        return url_by_title[title]
    lower = title.lower()
    ascii_string = unicode_mapper.toascii(lower)
    disquoted = re.sub("['\"]+", "", ascii_string)
    connected = re.sub("\W+", "-", disquoted)
    frontstripped = re.sub("^\W+", "", connected)
    stripped = re.sub("\W+$", "", frontstripped)
    url = films_webroot + stripped
    return url


class Globals:
    error_collector = None
    debug_recorder = None


class ErrorCollector:
    
    def __init__(self):
        self.errors = []
        
    def __str__(self):
        return "\n".join(self.errors) + "\n"
    
    def add(self, err, msg):
        lineno = inspect.currentframe().f_back.f_lineno
        error = f"{datetime.datetime.now()} - ERROR {err} at line {lineno} - {msg}"
        print(error)
        self.errors.append(error)
        
    def error_count(self):
        return len(self.errors)


class DebugRecorder:

    def __init__(self):
        self.debug_lines = []

    def __str__(self):
        return "\n".join(self.debug_lines) + "\n"
    
    def add(self, line):
        self.debug_lines.append(line)
    
    def write_debug(self):
        if len(self.debug_lines) > 0:
            with open(debug_file, 'w') as f:
                f.write(str(self))
            print("Debug text written to {}.".format(debug_file))
        else:
            print("No debug text, nothing written to".format(debug_file))


class NffFilm:
    
    def __init__(self, title, duration, description, directors, competitions):
        self.title = title
        self.duration = duration
        self.description = description
        self.directors = directors
        self.competitions = competitions
        
    def __str__(self):
        return ";".join([self.title,
                         self.duration,
                         self.description,
                         self.directors,
                         self.competitions]) + ";"

    
class NffScreening(planner.Screening):
    
    def __init__(self, screening, extra_times, subscreenings):
        film = screening.film
        screen = screening.screen
        startDateTime = screening.startDateTime
        endDateTime = screening.endDateTime
        qa = screening.qAndA
        extra = screening.extra
        audience = screening.audience
        planner.Screening.__init__(self, film, screen, startDateTime, endDateTime, qa, extra, audience)
        self.extra_times = extra_times
        self.subscreenings = subscreenings
        self.exclude = False
    

class FilmsLoader():
    
    def __init__(self, page_count):
        self.page_count = page_count
    
    def get_films(self, festival_data):
        
        # Parse AZ pages.
        self.parse_az_pages(festival_data)
        festival_data.write_nff_films()
        
        # Convert NFF films to the format expected by the C# planner.
        festival_data.fill_films_list()
        festival_data.write_films()

    def parse_az_pages(self, festival_data):
        for page_number in range(self.page_count):
            az_file = az_copy_paste_file_format.format(page_number)
            print("Searching {}...".format(az_file), end="")
            try:
                with open(az_file, 'r') as f:
                    az_text = f.read()
                film_count = self.parse_one_az_page(az_text, festival_data.nff_films)
                print(" {} films found".format(film_count))
            except FileNotFoundError as e:
                Globals.error_collector.add(e, "while parsing az pages in FilmsLoader")
    
    def parse_one_az_page(self, az_text, nff_films):
        filmparts = filmparts_re.match(az_text)
        if filmparts is not None:
            filmparts_text = filmparts.group('filmparts')
            film_count = 0
            for film_match in film_re.finditer(filmparts_text):
                film_count += 1
                description = re.sub(';', ',', film_match.group('description'))
                directors = film_match.group('directors')
                competitions_match = competitions_re.match(directors)
                if competitions_match is not None:
                    directors = competitions_match.group('directors')
                    competitions = competitions_match.group('competitions')
                else:
                    competitions = ""
                nff_films.append(NffFilm(film_match.group('title'),
                                       film_match.group('duration'),
                                       description,
                                       directors,
                                       competitions))
            return film_count


class PremieresLoader():
    
    def __init__(self):
        self.film = None
        self.url = ""
        
    def print_debug(self, str1, str2):
        Globals.debug_recorder.add('AZ ' + str(str1) + ' ' + str(str2))

    def get_screenings(self, festival_data):
        festival_data.read_screens()
        files_read_count = 0
        for film in festival_data.films:
            self.film = film
            self.url = re.sub("en/films/", premiere_prefix, film.url)
            url_file = os.path.join(webdata_dir, self.url.split("/")[3]) + ".html"
            if os.access(url_file, os.F_OK):
                print("Now reading {}".format(self.url))
                self.get_screenings_of_one_film(url_file, festival_data)
                files_read_count += 1
        print("\nDone reading screenings of {} premiêre.".format(files_read_count))
        festival_data.write_screens()
        festival_data.write_screenings()

    def get_screenings_of_one_film(self, film_html_file, festival_data):
        title = self.film.title
        if os.path.isfile(film_html_file):
            self.print_debug("--  Analysing premiêre page of title:", title)
            premiere_parser = PremierePageParser(self.film, festival_data)
            with open(film_html_file, 'r') as f:
                text = '\n' + '\n'.join([line for line in f])
            premiere_parser.feed(text)
 

class ScreeningsLoader():
    
    def __init__(self):
        self.nff_screenings = []
        
    def print_debug(self, str1, str2):
        Globals.debug_recorder.add('RF ' + str(str1) + ' ' + str(str2))

    def get_screenings(self, festival_data):
        self.parse_film_pages(festival_data)
        self.add_unique_screenings(festival_data)
        festival_data.write_screenings()
        
    def parse_film_pages(self, festival_data):
        for film in festival_data.films:
            film_file = film_file_format.format(film.filmid)
            print("Searching {}...".format(film_file), end="")
            try:
                with open(film_file, 'r') as f:
                    film_text = f.read()
                film_count = self.parse_one_film_page(film, film_text, festival_data)
                print(" {} screenings found".format(film_count))
            except FileNotFoundError as e:
                Globals.error_collector.add(e, "while parsing film pages in ScreeningsLoader")
            
    def parse_one_film_page(self, film, film_text, festival_data):
        self.print_debug("--  Analysing regular film page of title:", "{} ({}')".format(film.title, film.duration))
        film_parser = FilmPageParser(film, festival_data, self.nff_screenings)
        film_parser.feed(film_text)
        
    def add_unique_screenings(self, festival_data):
        def key_string(key):
            screen = key[0]
            start_dt = key[1]
            end_dt = key[2]
            start_date = start_dt.date()
            start_time = start_dt.time()
            end_time = end_dt.time()
            return "at {} {}-{} in {}".format(start_date.isoformat(),
                       start_time.isoformat(timespec='minutes'),
                       end_time.isoformat(timespec='minutes'),
                       screen)
        def screening_key(s):
#            return (s.screen, s.startDateTime, s.endDateTime, "|".join(s.extra_times))
            # TEMP, later first find coinciding screenings, then check if extra times and subscreenings are equal.
            return (s.screen, s.startDateTime, s.endDateTime)
        def find_film(name, descr, films):
            films = [f for f in films if f.title == name]
            if len(films) == 1:
                return films[0]
            nff_films = [n for n in festival_data.nff_films if n.description == descr]
            if len(nff_films) == 1:
                nff_film = nff_films[0]
                films = [f for f in festival_data.films if f.title == nff_film.title]
                if len(films) == 1:
                    return films[0]
            return None
        def add_screening_from_sub(key, sub, films, is_walk_in=False):
            time = sub[0]
            name = sub[1]
            descr = sub[2]
            film = find_film(name, descr, films)
            if film is not None:
                key_screen = key[0]
                if is_walk_in:
                    screen = festival_data.get_screen("{}-{}".format(key_screen, film.title))
                    start_dt = key[1]
                    end_dt = key[2]
                else:
                    screen = key_screen
                    start_date = key[1].date()
                    start_time_str = time
                    start_time = datetime.time.fromisoformat(start_time_str)
                    start_dt = datetime.datetime.combine(start_date, start_time)
                    duration = datetime.timedelta(minutes=int(film.duration))
                    end_dt = start_dt + duration
                add_screening(film, screen, start_dt, end_dt)
            else:
                Globals.error_collector.add("Subscreening name {} not found as film".format(name), "in add_unique screening")
        def add_screening(film, screen, start_dt, end_dt, dry_run=False):
            qa = ""
            extra = ""
            audience = "publiek"
            screening = planner.Screening(film, screen, start_dt, end_dt, qa, extra, audience)
            screening_duration = end_dt - start_dt
            screening_minutes = int(screening_duration.total_seconds() / 60)
            description = (f"    {str(screen):32} {start_dt.date()} {start_dt.time().isoformat(timespec='minutes')}-{end_dt.time().isoformat(timespec='minutes')} ({screening_minutes:0d}')  {film.title} ({film.duration}')")
            print(description, end="")
            if not dry_run:
                festival_data.screenings.append(screening)
                print(" ---SCREENING ADDED")
            else:
                print(" ---NOT ADDED")
       
        # Get films and subscreenings of screenings with equal screen, start time and end time.
        unique_films_by_screening = {}
        for film, key in [(s.film, screening_key(s)) for s in self.nff_screenings]:
            if key in unique_films_by_screening.keys():
                unique_films_by_screening[key].add(film)
            else:
                unique_films_by_screening[key] = set([film])
        films_by_samescreening = {k: films for (k, films) in unique_films_by_screening.items() if len(films) > 1}
        print("\n{} simultaneous film screenings.".format(len(films_by_samescreening)))

# TEMP wrong: we need the subscreenings!
        # Get events that repeat the same film.
        filmlist_by_screening = {}
        for film, key in [(s.film, screening_key(s)) for s in self.nff_screenings]:
            if key in filmlist_by_screening.keys():
                filmlist_by_screening[key].append(film)
            else:
                filmlist_by_screening[key] = [film]
        repeat_program_by_screening = {k: filmlist[0] for (k, filmlist) in filmlist_by_screening.items() if len(set(filmlist)) == 1}
        repeaters_count = len(repeat_program_by_screening)
        print(f"{repeaters_count:3d} Events that repeat a film.")
        for key, film in repeat_program_by_screening.items():
            print("-- Not adding yet event that repeats a film:")
            screening = [s for s in self.nff_screenings if (screening_key(s) == key)][0]
            add_screening(screening.film, screening.screen, screening.startDateTime, screening.endDateTime, True)

        # Get subsreenings of screenings with more than one subscreening.
        subs_by_screening = {}
        for subs, key in [(s.subscreenings, screening_key(s)) for s in self.nff_screenings]:
            if key in subs_by_screening:
                subs_by_screening[key].append(subs)
            else:
                subs_by_screening[key] = [subs]
        compilations = [(k, s) for (k, s) in subs_by_screening.items() if len(s) > 1]
        subsset_by_screening = {}
        print("{} compilations and walk-ins.".format(len(compilations)))
        for key, subslist in compilations:
            subsset = []
            for subs in subslist:
                if not (subs in subsset):
                    subsset.append(subs)
            subsset_by_screening[key] = subsset
        
        # Combine the screening keys with multiple films with those with complilations.
        common_keys = set(films_by_samescreening.keys() & set(subsset_by_screening.keys()))
        print(f"{len(common_keys)} Combined simultaneous film screenings and compilations.")
        comment = "while combining simultaneous films and compilations"
        excess_simultaneous_count = len(common_keys) - len(films_by_samescreening)
        if excess_simultaneous_count > 0:
            Globals.error_collector.add(f"{excess_simultaneous_count} screenings exist with simultaneous films but no compilation program", comment)
        excess_combined_count = len(common_keys) - len(subsset_by_screening)
        if excess_combined_count > 0:
            Globals.error_collector.add(f"{excess_combined_count} screenings exist with compilation program but no simultaneous films", comment)

        # Add the screenings with no simulateous other screening.
        all_keys = [screening_key(s) for s in self.nff_screenings]
        single_keys = set(all_keys) - set(films_by_samescreening.keys()) - set(subsset_by_screening.keys())
        singlet_count = 0
        repeater_count = 0
        for key in single_keys:
            singlet_screenings = [s for s in self.nff_screenings if (screening_key(s) == key)]
            if len(singlet_screenings) == 1:
                Globals.error_collector.add(f"Regular screening has {len(singlet_screenings)} variations", "while adding regular screenings")
            screening = singlet_screenings[0]
            if len(screening.subscreenings) > 1:
                for sub in screening.subscreenings:
                    print("-- Adding repeater event:")
                    add_screening_from_sub(key, sub, [screening.film])
                    repeater_count +=1
            else:
                print("-- Adding regular screening:")
                add_screening(screening.film, screening.screen, screening.startDateTime, screening.endDateTime)
                singlet_count += 1
        
        # Add walk-in screenings and combination programs.
        combi_count = 0
        walkin_count = 0
        for key in common_keys:
            films = films_by_samescreening[key]
            subsset = subsset_by_screening[key]
            print(f"- Event {key_string(key)}:")
            for subs in subsset:
                if len(subs) > 1:
                    for sub in subs:
                        print("-- Adding combination program:")
                        add_screening_from_sub(key, sub, films)
                        combi_count += 1
                else:
                    sub = subs[0]
                    print("-- Adding walk-in event:")
                    add_screening_from_sub(key, sub, films, True)
                    walkin_count += 1
        
        print(f"{singlet_count:3d} Singlet screenings added.")
        print(f"{repeaters_count:3d} Events that repeat the same film.")
        print(f"{combi_count:3d} Combination programs added.")
        print(f"{walkin_count:3d} Walk-in events added.")
        print()

class HtmlPageParser(HTMLParser):
    
    def __init__(self, film, festival_data):
        HTMLParser.__init__(self)
        self.film = film
        self.festival_data = festival_data
        self.init_screening_data()
#        self.start_date = None
        self.debugging = False
        self.debug_text = ""
        self.in_date = False
        self.in_town = False
        self.in_location = False
        self.in_time = False
        self.en_month_by_abbr = {}
        self.en_month_by_abbr["Sep"] = 9
        self.en_month_by_abbr["Oct"] = 10
        self.nl_month_by_name = {}
        self.nl_month_by_name["september"] = 9
        self.nl_month_by_name["oktober"] = 10

    def print_debug(self, str1, str2):
        if self.debugging:
            Globals.debug_recorder.add('F ' + str(str1) + ' ' + str(str2))

    def init_screening_data(self):
        self.location = None
        self.screen = None
        self.start_time = None
        self.end_time = None
        self.audience = "publiek"
        self.qa = ""
        self.extra = ""

    def add_screening(self, append_now=True):
        print()
        print("---SCREENING OF {}".format(self.film.title))
        print("--  screen:     {}".format(self.screen))
        print("--  start date: {}".format(self.start_date))
        print("--  start time: {}".format(self.start_time))
        print("--  duration:   {}".format(self.film.duration))
        print("--  audience:   {}".format(self.audience))
        print("--  category:   {}".format(self.film.medium_category))
        print("--  q and a:    {}".format(self.qa))
        print("--  extra:      {}".format(self.extra))
        startDateTime = datetime.datetime.combine(self.start_date, self.start_time)
        if self.end_time is None:
            duration = datetime.timedelta(minutes=int(self.film.duration))
            endDateTime = startDateTime + duration
            self.end_time = datetime.time(endDateTime.hour, endDateTime.minute)
        else:
            end_date = self.start_date if self.end_time > self.start_time else self.start_date + datetime.timedelta(days=1) 
            endDateTime = datetime.datetime.combine(end_date, self.end_time)
            self.print_debug("--- ", "START TIME = {}, END TIME = {}".format(startDateTime, endDateTime))
        screening = planner.Screening(self.film, self.screen, startDateTime, endDateTime, self.qa, self.extra, self.audience)
        if append_now:
            self.festival_data.screenings.append(screening)
            print("---SCREENING ADDED")
        self.init_screening_data()
        return screening

    def set_screen(self, location):
        self.screen = self.festival_data.get_screen(location)

    def handle_starttag(self, tag, attrs):
        self.print_debug("Encountered a start tag:", tag)

    def handle_endtag(self, tag):
        self.print_debug("Encountered an end tag :", tag)

    def handle_data(self, data):
        self.print_debug("Encountered some data  :", data)

    def handle_comment(self, data):
        self.print_debug("Comment  :", data)

    def handle_decl(self, data):
        self.print_debug("Decl     :", data)
   
    
class PremierePageParser(HtmlPageParser):
 
    def __init__(self, film, festival_data):
        HtmlPageParser.__init__(self, film, festival_data)
           
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
            self.print_debug("--", "DATE found: {}".format(data))
            start_date_str = ""
            try:
                start_date_str = re_date.findall(data)[0]
                month = self.nl_month_by_name[start_date_str.split(" ")[1]]
                day = int(start_date_str.split(" ")[0])
                self.start_date = datetime.date(festival_year, month, day)
            except IndexError:
                self.print_debug("--", "ERROR can't construct date from '{}'.".format(data))
        if data == "Amsterdam":
            self.in_town = True
            self.debugging = True
        if data == "Apeldoorn":
            self.in_town = False
            if self.in_time:
                Globals.error_collector.add("'in_time' still true when arriving in {}".format(data), "while PremiérePageParser parses {}".format(self.film.title))
                self.in_time = False
            self.debugging = False
        if self.in_time and data.strip().startswith("Start:"):
            self.print_debug("-- ", "START TIME found: {}".format(data))
            start_time_str = None
            try:
                start_time_str = re_time.findall(data)[0]
                hour = int(start_time_str.split(":")[0])
                minute = int(start_time_str.split(":")[1])
                self.start_time = datetime.time(hour, minute)
                self.in_time = False
                self.set_screen(self.location)
                self.add_screening()
            except IndexError:
                self.print_debug("-- ", "ERROR can't construct time from: '{}'.".format(data))
        if self.in_location:
            location = data.strip()
            if len(location) > 0:
                print("--  LOCATION:   {}   CATEGORY: {}".format(location, self.film.medium_category))
                self.print_debug("LOCATION", location)
                self.location = location
                self.in_location = False
                self.print_debug("-- ", "LEAVING LOCATION")
                self.in_time = True


class FilmPageParser(HtmlPageParser):
    
    def __init__(self, film, festival_data, nff_screenings):
        HtmlPageParser.__init__(self, film, festival_data)
        self.debugging = True
        self.nff_screenings = nff_screenings
 
    def init_screening_data(self):
        HtmlPageParser.init_screening_data(self)
        self.in_extratimes = False
        self.in_extrafilm = False
        self.await_descr = False
        self.in_descr = False
        self.last_tag = None
        self.extra_times = []
        self.subscreenings = []
        self.extra_time = None
        self.part_name = None
        self.part_descr = None

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
        self.last_tag = tag
        if self.in_extratimes and tag == "h3":
            self.in_extratimes = False
            self.set_screen(self.location)
            if self.screen.abbr == "102filmtheatersdoorhetland":
                self.print_debug("-- ", f"NATIONAL PREMIERE {self.film.title} REFERENCE skipped")
            else:
                extra_times = self.extra_times
                subscreenings = self.subscreenings
                screening = self.add_screening(False)
                self.nff_screenings.append(NffScreening(screening, extra_times, subscreenings))
                self.print_debug("-- ", "EXTRA TIMES: {}".format(", ".join(extra_times)))
                self.print_debug("-- ", "{} SUBSCREENINGS: {}".format(len(subscreenings), ", ".join(["{}/{}".format(t, n) for t, n, d in subscreenings])))
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
            self.print_debug("-- ", "SUBSCREENING found: {} {} - '{}'".format(self.extra_time, self.part_name, self.part_descr))
            self.subscreenings.append((self.extra_time, self.part_name, self.part_descr))
            self.extra_time = None
            self.part_descr = None
            self.part_name = None
 
    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
        stripped_data = data.strip()
        if data == "On location":
            self.in_location = True
        elif self.in_location and len(stripped_data) > 0:
            self.location = stripped_data
            self.print_debug("-- ", "LOCATION found: {}".format(self.location))
            self.in_location = False
            self.in_time = True
        elif self.in_time and len(stripped_data) > 0:
            self.print_debug("-- ", "TIMES found: {}".format(data))
            self.in_time = False
            self.in_extratimes = True
            m = re_datetime.search(stripped_data)
            day = int(m.group('day'))
            month = self.en_month_by_abbr[m.group('month')]
            self.start_date = datetime.date(festival_year, month, day)
            self.start_time = datetime.time.fromisoformat(m.group('starttime'))
            self.end_time = datetime.time.fromisoformat(m.group('endtime'))
        elif self.in_extratimes and self.last_tag == "div" and len(stripped_data) > 0:
            m = re_extratime.match(stripped_data)
            self.print_debug("-- ", "LOOKING for an extra time in '{}'".format(stripped_data))
            if m is not None:
                self.print_debug("--- ", "Found MATCH {}".format(m.group('time')))
                self.extra_time = m.group('time')
                self.extra_times.append(self.extra_time)
        elif self.in_extrafilm:
            self.part_name = stripped_data
            self.in_extrafilm = False
            self.await_descr = True
        elif self.in_descr:
            self.part_descr += data
   

class FestivalData:
    
    def __init__(self):
        self.nff_films = []
        self.films = []
        self.screenings = []
        self.filmid_by_url = {}
        self.screen_by_location = {}
        self.read_screens()
        
    def __repr__(self):
        return "\n".join([str(film) for film in self.nff_films])

    def fill_films_list(self):
        filmid = 0
        for nff_film in self.nff_films:
            filmid += 1
            seqnr = filmid
            title = nff_film.title
            url = get_url(nff_film.title)
            film = planner.Film(seqnr, filmid, title, url)
            film.medium_category = "films"
            film.duration = nff_film.duration
            self.films.append(film)
            
    def get_screen(self, location):
        try:
            screen = self.screen_by_location[location]
        except KeyError:
            abbr = location.replace(" ", "").lower()
            print("NEW LOCATION:  '{}' => {}".format(location, abbr))
            self.screen_by_location[location] =  planner.Screen((location, abbr))
            screen = self.screen_by_location[location]
        return screen
            
    def splitrec(self, line, sep):
        end = sep + '\r\n'
        return line.rstrip(end).split(sep)

    def read_screens(self):
        try:
            with open(screens_file, 'r') as f:
                screens = [planner.Screen(self.splitrec(line, ';')) for line in f]
            self.screen_by_location = {screen._key(): screen for screen in screens}
        except OSError:
            pass

    def read_filmids(self):
        try:
            with open(films_file, 'r') as f:
                records = [self.splitrec(line, ';') for line in f]
            for record in records[1:]:
                filmid = int(record[1]);
                url = record[8]
                self.filmid_by_url[url] = filmid
        except OSError:
            pass
        try:
            self.curr_film_id = max(self.filmid_by_url.values())
        except ValueError:
            self.curr_film_id = 0
 
    def write_screens(self):
        with open(screens_file, 'w') as f:
            for screen in self.screen_by_location.values():
                f.write(repr(screen))
        print("Done writing {} records to {}.".format(len(self.screen_by_location), screens_file))
   
    def write_nff_films(self):
        with open(filmdata_file, 'w') as f:
            text = repr(self) + "\n"
            f.write(text)
        print("\nDone writing {} records to {}.\n".format(len(self.nff_films), filmdata_file))

    def write_films(self):
        if len(self.films):
            with open(films_file, 'w') as f:
                f.write(self.films[0].film_repr_csv_head())
                for film in self.films:
                    f.write(repr(film))
        print("Done writing {} records to {}.".format(len(self.films), films_file))

    def write_screenings(self):
        if len(self.screenings):
            with open(screenings_file, 'w') as f:
                f.write(self.screenings[0].screening_repr_csv_head())
                for screening in [s for s in self.screenings if s.audience == "publiek"]:
                    f.write(repr(screening))
        print("Done writing {} records to {}.".format(len(self.screenings), screenings_file))


if __name__ == "__main__":
    main()