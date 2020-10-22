#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 10 18:13:42 2020

@author: maarten
"""

import os
import datetime

interface_dir = os.path.expanduser("~/Projects/FilmFestivalPlanner/FilmFestivalLoader/PlannerInterface")
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
 
    def duration_str(self):
        minutes = int(self.duration.total_seconds() / 60)
        return str(minutes) + "′"

class Screen():

    def __init__(self, name_abbr_tuple):
        self.name = name_abbr_tuple[0]
        self.abbr = name_abbr_tuple[1]

    def __str__(self):
        return self.abbr

    def __repr__(self):
        text = ";".join([self.name, self.abbr])
        return "{}\n".format(text)

    def _key(self):
        return self.name


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


if __name__ == "__main__":
    print("This module is not executable.")
