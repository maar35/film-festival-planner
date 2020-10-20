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
    
    comment("Parsing regular film pages.")
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
    print(f"\n{datetime.datetime.now()}  - {text}")

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
            print(f"Debug text written to {debug_file}.")
        else:
            print(f"No debug text, nothing written to {debug_file}.")


class NffFilm:
    
    def __init__(self, title, duration, description, directors, competitions):
        self.title = title
        self.duration = duration
        self.description = description
        self.directors = directors
        self.competitions = competitions
        
    def __str__(self):
        return ";".join([self.title,
                         str(NffFilm.duration_to_minutes(self.duration)),
                         self.description,
                         self.directors,
                         self.competitions]) + ";"
 
    def duration_to_minutes(duration):
        return int(duration.total_seconds() / 60)

    
class NffScreening(planner.Screening):
    
    def __init__(self, screening, subscreenings):
        film = screening.film
        screen = screening.screen
        start_datetime = screening.start_datetime
        end_datetime = screening.end_datetime
        qa = screening.q_and_a
        extra = screening.extra
        audience = screening.audience
        planner.Screening.__init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience)
        self.subscreenings = subscreenings
        self.exclude = False


class Subscreening():
    
    def __init__(self, time, title, description):
        self.time = time
        self.title = title
        self.description = description

    def __str__(self):
        return f"{self.time} {self.title} - {self.description}"

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash((self.time, self.title, self.description))


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
            print(f"Searching {az_file}...", end="")
            try:
                with open(az_file, 'r') as f:
                    az_text = f.read()
                film_count = self.parse_one_az_page(az_text, festival_data.nff_films)
                print(f" {film_count} films found")
            except FileNotFoundError as e:
                Globals.error_collector.add(e, "while parsing az pages in FilmsLoader")
    
    def parse_one_az_page(self, az_text, nff_films):
        filmparts = filmparts_re.match(az_text)
        if filmparts is not None:
            filmparts_text = filmparts.group('filmparts')
            film_count = 0
            for film_match in film_re.finditer(filmparts_text):
                film_count += 1
                duration = datetime.timedelta(minutes=int(film_match.group('duration')))
                description = re.sub(';', ',', film_match.group('description'))
                directors = film_match.group('directors')
                competitions_match = competitions_re.match(directors)
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
                print(f"Now reading {self.url}")
                self.get_screenings_of_one_film(url_file, festival_data)
                files_read_count += 1
        print(f"\nDone reading screenings of {files_read_count} premiêre.")
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
        self.films_by_samescreening = None
        self.subsset_by_screening = None
        self.common_keys = None
        
    def print_debug(self, str1, str2):
        Globals.debug_recorder.add('RF ' + str(str1) + ' ' + str(str2))

    def get_screenings(self, festival_data):
        self.parse_film_pages(festival_data)
        self.add_unique_screenings(festival_data)
        festival_data.write_screenings()
        
    def parse_film_pages(self, festival_data):
        for film in festival_data.films:
            film_file = film_file_format.format(film.filmid)
            print(f"Now reading {film_file} - {film.title} ({film.duration_str()})")
            try:
                with open(film_file, 'r') as f:
                    film_text = f.read()
                self.parse_one_film_page(film, film_text, festival_data)
            except FileNotFoundError as e:
                Globals.error_collector.add(e, "while parsing film pages in ScreeningsLoader")
            
    def parse_one_film_page(self, film, film_text, festival_data):
        self.print_debug(f"--  Analysing regular film page of title:", "{film.title} ({film.duration_str()})")
        film_parser = FilmPageParser(film, festival_data, self.nff_screenings)
        film_parser.feed(film_text)
        
    def add_unique_screenings(self, festival_data):
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
            these films are continuously screened on separate screens with the
            theater. Since those screens are not explicitly named, new screens
            are created, based on theater abbreviation and film title, in
            order to load unique screenings.
            In the code, the original screenings are referred to as walk-in
            events.
        - Repeater events
            A repeater event is a screening that reapeats the same film as
            subscreenings.
            The subcreenings are loaded, not the repeater event.
        - Regular screenings
            Regular screenings are unique screenings where one film is
            screened one time.
            Premiêre sites contain regular screenings.
            Regular screenings are loaded as is.
            
        A more simple way could have been:
        - Pefer subscreenings above screenings
        - De-duplicate coinciding screenings with different films by creating
            new screens
        - De-duplicate remaining screenings by keeping one of each duplicate
            combination of screen, start-time and end-time.
        """

        class ScreeningKey:
            
            def __init__(self, screening):
                self.screen = screening.screen
                self.start_dt = screening.start_datetime
                self.end_dt = screening.end_datetime

            def __str__(self):
                return f"{self.screen}, {self.start_dt}, {self.end_dt}"

            def __eq__(self, other):
                return hash(self) == hash(other)

            def __hash__(self):
                return hash((self.screen, self.start_dt, self.end_dt))
                
        def main():
        
            # Get films and subscreenings of screenings with equal screen, start time and end time.
            get_films_by_samescreening()
            print(f"\n{len(self.films_by_samescreening)} simultaneous film screenings.")
    
            # Get subscreenings of screenings with more than one subscreening.
            get_subscreeningsset_by_screening()
            print(f"{len(self.subsset_by_screening)} compilations and walk-ins.")
            
            # Combine the screening keys with multiple films with those with compilations.
            get_common_keys()
    
            # Add the screenings with no simulateous other screening.
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

        def key_string(key):
#            screen = key[0]
#            start_dt = key[1]
#            end_dt = key[2]
            return "at {} {}-{} in {}".format(
                    key.start_dt.date().isoformat(),
                    key.start_dt.time().isoformat(timespec='minutes'),
                    key.end_dt.time().isoformat(timespec='minutes'),
                    key.screen)

        def print_heading(msg):
            text = "-- " + msg + ":"
            print(f"{text:24}", end="")
        
#        def screening_key(s):
#            return (s.screen, s.start_datetime, s.end_datetime)
        
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
#            time = sub[0]
#            name = sub[1]
#            descr = sub[2]
            film = find_film(sub.title, sub.description, films)
            if film is not None:
#                key_screen = key[0]
                if is_walk_in:
                    screen = festival_data.get_screen(f"{key.screen}-{film.title}")
#                    start_dt = key[1]
#                    end_dt = key[2]
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
                Globals.error_collector.add(f"Subscreening name {name} not found as film",
                                            "in add_screening_from_sub")
                
        def add_screening(film, screen, start_dt, end_dt, dry_run=False):
            qa = ""
            extra = ""
            audience = "publiek"
            screening = planner.Screening(film, screen, start_dt, end_dt, qa, extra, audience)
            screening_minutes = f"({NffFilm.duration_to_minutes(end_dt - start_dt)}')"
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
                festival_data.screenings.append(screening)
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
            print(f"{common_count} Combined simultaneous film screenings and compilations.")
            but = " but no compilation program"
            comment = "while combining simultaneous films and compilations"
            excess_samescreening_count = len(self.films_by_samescreening) - common_count
            if excess_samescreening_count > 0:
                Globals.error_collector.add(f"{excess_samescreening_count} screenings exist with simultaneous films {but}",
                                            comment)
            excess_multi_subscreenings_count = len(self.subsset_by_screening) - common_count
            if excess_multi_subscreenings_count > 0:
                Globals.error_collector.add(f"{excess_multi_subscreenings_count} screenings exist with multiple subscreenings {but}",
                                            comment)
        
        def add_singlet_screenings():
            all_keys = [ScreeningKey(s) for s in self.nff_screenings]
            singlet_keys = set(all_keys) - set(self.films_by_samescreening.keys()) - set(self.subsset_by_screening.keys())
            for key in singlet_keys:
                singlet_screenings = [s for s in self.nff_screenings if (ScreeningKey(s) == key)]
                if len(singlet_screenings) != 1:
                    Globals.error_collector.add(f"Regular screening has {len(singlet_screenings)} variations",
                                                "while adding regular screenings")
                screening = singlet_screenings[0]
                if len(screening.subscreenings) > 1:
                    print(f"- Event {key_string(key)}:")
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
                print(f"- Event {key_string(key)}:")
                for subs in subsset:
                    if len(subs) > 1:
                        for sub in subs:
                            print_heading("combination program")
                            add_screening_from_sub(key, sub, films)
                            self.combi_count += 1
                    else:
                        sub = subs[0]
                        print_heading("walk-in event")
                        add_screening_from_sub(key, sub, films, True)
                        self.walkin_count += 1
        
        print(self.add_unique_screenings.__doc__)
        main()

class HtmlPageParser(HTMLParser):
    
    def __init__(self, film, festival_data):
        HTMLParser.__init__(self)
        self.film = film
        self.festival_data = festival_data
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

    def new_screening(self):
        pass
    
    def add_screening(self, append_now=True):
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
        if self.end_time is None:
            end_datetime = start_datetime + self.film.duration
            self.end_time = datetime.time(end_datetime.hour, end_datetime.minute)
        else:
            end_date = self.start_date if self.end_time > self.start_time else self.start_date + datetime.timedelta(days=1) 
            end_datetime = datetime.datetime.combine(end_date, self.end_time)
            self.print_debug(f"--- ", "START TIME = {start_datetime}, END TIME = {end_datetime}")
        screening = planner.Screening(self.film, self.screen, start_datetime, end_datetime, self.qa, self.extra, self.audience)
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
            self.print_debug("--", f"DATE found: {data}")
            start_date_str = ""
            try:
                start_date_str = re_date.findall(data)[0]
                month = self.nl_month_by_name[start_date_str.split(" ")[1]]
                day = int(start_date_str.split(" ")[0])
                self.start_date = datetime.date(festival_year, month, day)
            except IndexError:
                self.print_debug("--", f"ERROR can't construct date from '{data}'.")
        if data == "Amsterdam":
            self.in_town = True
            self.debugging = True
        if data == "Apeldoorn":
            self.in_town = False
            if self.in_time:
                Globals.error_collector.add(f"'in_time' still true when arriving in {data}",
                                            f"while PremiérePageParser parses {self.film.title}")
                self.in_time = False
            self.debugging = False
        if self.in_time and data.strip().startswith("Start:"):
            self.print_debug("-- ", f"START TIME found: {data}")
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
                self.print_debug("-- ", f"ERROR can't construct time from: '{data}'.")
        if self.in_location:
            location = data.strip()
            if len(location) > 0:
                print(f"--  LOCATION:   {location}   CATEGORY: {self.film.medium_category}")
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
                subscreenings = self.subscreenings
                screening = self.add_screening(False)
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
        if data == "On location":
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
            m = re_datetime.search(stripped_data)
            day = int(m.group('day'))
            month = self.en_month_by_abbr[m.group('month')]
            self.start_date = datetime.date(festival_year, month, day)
            self.start_time = datetime.time.fromisoformat(m.group('starttime'))
            self.end_time = datetime.time.fromisoformat(m.group('endtime'))
        elif self.in_extratimes and self.last_tag == "div" and len(stripped_data) > 0:
            m = re_extratime.match(stripped_data)
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
            print(f"NEW LOCATION:  '{location}' => {abbr}")
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
        print(f"Done writing {len(self.screen_by_location)} records to {screens_file}.")
   
    def write_nff_films(self):
        with open(filmdata_file, 'w') as f:
            text = repr(self) + "\n"
            f.write(text)
        print(f"\nDone writing {len(self.nff_films)} records to {filmdata_file}.\n")

    def write_films(self):
        if len(self.films):
            with open(films_file, 'w') as f:
                f.write(self.films[0].film_repr_csv_head())
                for film in self.films:
                    f.write(repr(film))
        print(f"Done writing {len(self.films)} records to {films_file}.")

    def write_screenings(self):
        if len(self.screenings):
            with open(screenings_file, 'w') as f:
                f.write(self.screenings[0].screening_repr_csv_head())
                for screening in [s for s in self.screenings if s.audience == "publiek"]:
                    f.write(repr(screening))
        print(f"Done writing {len(self.screenings)} records to {screenings_file}.")


if __name__ == "__main__":
    main()