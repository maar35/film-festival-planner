#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 10 18:13:42 2020

@author: maarten
"""

import os

interface_dir = os.path.expanduser("~/Projects/FilmFestivalPlanner/FilmFestivalLoader/Shared")
ucode_file = os.path.join(interface_dir, "unicodemap.txt")


class UnicodeMapper:
    
    def __init__(self):
        with open(ucode_file) as f:
            self.umap_keys = f.readline().rstrip("\n").split(";")
            self.umap_values = f.readline().rstrip("\n").split(";")
        
    def toascii(self, s):            
        for (u, a) in zip(self.umap_keys, self.umap_values):
            s = s.replace(u, a)
    
        return s


class Film:

    filmcategory_by_string = {}
    filmcategory_by_string["films"] = "Films"
    filmcategory_by_string["verzamelprogrammas"] = "CombinedProgrammes"
    filmcategory_by_string["events"] = "Events"
    mapper = UnicodeMapper()

    def __init__(self, seqnr, filmid, title, url):
        self.seqnr = seqnr
        self.filmid = filmid
        self.sorted_title = title
        self.sortstring = self.lower(self.sorted_title)
        self.title = title
        self.title_language = ""
        self.section = ""
        self.duration = None
        self.url = url
        self.medium_category = url.split("/")[5]
        self.combination_url = ""

    def __str__(self):
        return "; ".join([self.title, self.medium_category, self.combination_url])

    def film_repr_csv_head(self):
        text = ";".join([
            "seqnr",
            "filmid",
            "sort",
            "title",
            "titlelanguage",
            "section",
            "duration",
            "mediumcategory",
            "url"
        ])
        return "{}\n".format(text)

    def __repr__(self):
        text = ";".join([
            (str)(self.seqnr),
            (str)(self.filmid),
            self.sortstring.replace(";", ".,"),
            self.title.replace(";", ".,"),
            self.title_language,
            self.section,
            self.duration_str(),
            self.filmcategory_by_string[self.medium_category],
            self.url
        ])
        return "{}\n".format(text)

    def lower(self, s):
        return self.mapper.toascii(s).lower()
 
    def duration_to_minutes(duration):
        return int(duration.total_seconds() / 60)

    def duration_str(self):
        minutes = Film.duration_to_minutes(self.duration)
        return str(minutes) + "′"

class Screen():

    type_by_onlocation = {}
    type_by_onlocation[True]= "Location"
    type_by_onlocation[False] = "OnLine"
    
    def __init__(self, screen_id, city, name, abbr, on_location=True):
        self.screen_id = screen_id
        self.city = city
        self.name = name
        self.abbr = abbr
        self.type = self.type_by_onlocation[on_location]

    def __str__(self):
        return self.abbr

    def __repr__(self):
        text = ";".join([str(self.screen_id), self.city, self.name, self.abbr, self.type])
        return "{}\n".format(text)

    def _key(self):
        return (self.city, self.name)


class Screening:

    def __init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience):
        self.film = film
        self.screen = screen
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self.extra = extra
        self.films_in_screening = 1 if len(extra) == 0 else 2
        self.q_and_a = qa
        self.audience = audience

    def screening_repr_csv_head(self):
        text = ";".join([
            "filmid",
            "date",
            "screen",
            "starttime",
            "endtime",
            "filmsinscreening",
            "extra",
            "qanda"
        ])
        return "{}\n".format(text)

    def __repr__(self):
        start_date = self.start_datetime.date()
        start_time = self.start_datetime.time()
        end_time = self.end_datetime.time()
        text = ";".join([
            (str)(self.film.filmid),
            start_date.isoformat(),
            self.screen.abbr,
            start_time.isoformat(timespec='minutes'),
            end_time.isoformat(timespec='minutes'),
            (str)(self.films_in_screening),
            self.extra,
            self.q_and_a
        ])
        return "{}\n".format(text)
   

class FestivalData:

    curr_screen_id = None

    def __init__(self, plandata_dir):
        self.nff_films = []
        self.films = []
        self.screenings = []
        self.filmid_by_url = {}
        self.screen_by_location = {}
        self.films_file = os.path.join(plandata_dir, "films.csv")
        self.screens_file = os.path.join(plandata_dir, "screens.csv")
        self.screenings_file = os.path.join(plandata_dir, "screenings.csv")
        self.read_screens()

    def get_screen(self, city, name):
        screen_key = (city, name)
        try:
            screen = self.screen_by_location[screen_key]
        except KeyError:
            self.curr_screen_id += 1
            screen_id = self.curr_screen_id
            abbr = name.replace(" ", "").lower()
            print(f"NEW LOCATION:  '{city} {name}' => {abbr}")
            self.screen_by_location[screen_key] =  Screen(screen_id, city, name, abbr)
            screen = self.screen_by_location[screen_key]
        return screen
            
    def splitrec(self, line, sep):
        end = sep + '\r\n'
        return line.rstrip(end).split(sep)

    def read_screens(self):
        def create_screen(fields):
            screen_id = int(fields[0])
            city = fields[1]
            name = fields[2]
            abbr = fields[3]
            screen_type_str = fields[4]
            screen_types = [k for (k, v) in Screen.type_by_onlocation.items() if v == screen_type_str]
            screen_type = screen_types[0]
            return Screen(screen_id, city, name, abbr, screen_type)

        try:
            with open(self.screens_file, 'r') as f:
                screens = [create_screen(self.splitrec(line, ';')) for line in f]
            self.screen_by_location = {screen._key(): screen for screen in screens}
        except OSError:
            pass
        try:
            self.curr_screen_id = max([screen.screen_id for screen in self.screen_by_location.values()])
        except ValueError:
            self.curr_screen_id = 0

    def read_filmids(self):
        try:
            with open(self.films_file, 'r') as f:
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
        with open(self.screens_file, 'w') as f:
            for screen in self.screen_by_location.values():
                f.write(repr(screen))
        print(f"Done writing {len(self.screen_by_location)} records to {self.screens_file}.")

    def write_films(self):
        if len(self.films):
            with open(self.films_file, 'w') as f:
                f.write(self.films[0].film_repr_csv_head())
                for film in self.films:
                    f.write(repr(film))
        print(f"Done writing {len(self.films)} records to {self.films_file}.")

    def write_screenings(self):
        if len(self.screenings):
            with open(self.screenings_file, 'w') as f:
                f.write(self.screenings[0].screening_repr_csv_head())
                for screening in [s for s in self.screenings if s.audience == "publiek"]:
                    f.write(repr(screening))
        print(f"Done writing {len(self.screenings)} records to {self.screenings_file}.")


if __name__ == "__main__":
    print("This module is not executable.")
