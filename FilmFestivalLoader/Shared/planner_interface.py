#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide all interfaces to the Planner Project, including shared tools.

Created on Sat Oct 10 18:13:42 2020

@author: maarten
"""

import os
import re
import xml.etree.ElementTree as ET

interface_dir = os.path.expanduser("~/Projects/FilmFestivalPlanner/FilmFestivalLoader/Shared")
articles_file = os.path.join(interface_dir, "articles.txt")
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


class Article():

    def __init__(self, language_articles_tuple):
        self.language = language_articles_tuple[0]
        self.articles = language_articles_tuple[1].split()

    def _key(self):
        return self.language

    def isarticle(self, word):
        return word.lower() in self.articles


class Film:

    category_films = "Films"
    category_combinations = "CombinedProgrammes"
    category_events = "Events"
    category_by_string = dict(films=category_films, verzamelprogrammas=category_combinations, events=category_events)
    mapper = UnicodeMapper()
    articles_by_language = {}
    language_by_title = {}
    re_alpha = re.compile(r'^[a-zA-Z]')

    def __init__(self, seqnr, filmid, title, url):
        self.seqnr = seqnr
        self.filmid = filmid
        self.title = title
        self.url = url
        self.title_language = self.language()
        self.section = ""
        self.duration = None
        self.medium_category = url.split("/")[6]
        self.sortstring = self.lower(self.strip_article())

    def __str__(self):
        return "; ".join([self.title, self.medium_category])

    def __lt__(self, other):
        return self.sortstring < other.sortstring

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
            self.category_by_string[self.medium_category],
            self.url
        ])
        return "{}\n".format(text)

    def filmid_repr(self):
        text = ";".join([
            (str)(self.filmid),
            self.title.replace(";", ".,"),
            self.url
        ])
        return f'{text}\n'

    def lower(self, s):
        return self.mapper.toascii(s).lower()

    def duration_to_minutes(duration):
        return int(duration.total_seconds() / 60)

    def duration_str(self):
        minutes = Film.duration_to_minutes(self.duration)
        return str(minutes) + "′"

    def language(self):
        try:
            language = Film.language_by_title[self.title]
            return language
        except KeyError:
            return 'en'

    def film_info(self, festival_data):
        infos = [i for i in festival_data.filminfos if i.filmid == self.filmid]
        try:
            return infos[0]
        except IndexError:
            return FilmInfo(None, '', '')

    def is_part_of_combination(self, festival_data):
        return len(self.film_info(festival_data).combination_urls) > 0

    def screened_films(self, festival_data):
        return self.film_info(festival_data).screened_films

    def strip_article(self):
        title = self.title
        start_indices = [i for i in [title.find(" "), title.find("'")] if i >= 0]
        try:
            i = min(start_indices)
        except ValueError:
            return title
        else:
            if title[i] == "'":
                i += 1
            first = title[0:i]
            rest = title[i:].lstrip()
        if not self.articles_by_language[self.title_language].isarticle(first):
            return title
        return "{}, {}".format(rest, first)


class ScreenedFilm:

    def __init__(self, filmid, title, description):
        self.filmid = filmid
        if title is None or len(title) == 0:
            raise FilmTitleError(description)
        self.title = title
        self.description = description if description is not None else ''

    def __str__(self):
        return '\n'.join([str(self.filmid), self.title, self.description])


class FilmInfo():

    def __init__(self, filmid, description, article, combination_urls=[], screened_films=[]):
        self.filmid = filmid
        self.description = description
        self.article = article
        self.combination_urls = combination_urls
        self.screened_films = screened_films

    def __str__(self):
        return '\n'.join([str(self.filmid), self.description, self.article, '\n'.join([str(fi) for fi in self.screened_films])]) + '\n'


class Screen():

    screen_types = ['Location', 'OnLine', 'OnDemand']

    def __init__(self, screen_id, city, name, abbr, screentype='Location'):
        self.screen_id = screen_id
        self.city = city
        self.name = name
        self.abbr = abbr
        self.type = screentype

    def __str__(self):
        return self.abbr

    def __repr__(self):
        text = ";".join([str(self.screen_id), self.city, self.name, self.abbr, self.type])
        return "{}\n".format(text)

    def _key(self):
        return (self.city, self.name)


class Screening:

    def __init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience, combination_program=None, subtitles=''):
        self.film = film
        self.screen = screen
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self.extra = extra
        self.films_in_screening = 1 if len(extra) == 0 else 2
        self.subtitles = subtitles
        self.combination_program = combination_program
        self.q_and_a = qa
        self.audience = audience

    def __str__(self):
        starttime = self.start_datetime.isoformat(sep=" ", timespec="minutes")
        endtime = self.end_datetime.time().isoformat()
        return f'{starttime} - {endtime}, {self.screen.abbr}, {self.film.title}'

    def screening_repr_csv_head(self):
        text = ";".join([
            "filmid",
            "screen",
            "starttime",
            "endtime",
            "filmsinscreening",
            "combinationid",
            "extra",
            "qanda"
        ])
        return "{}\n".format(text)

    def __repr__(self):
        text = ";".join([
            (str)(self.film.filmid),
            self.screen.abbr,
            self.start_datetime.isoformat(sep=' '),
            self.end_datetime.isoformat(sep=' '),
            (str)(self.combination_program.filmid if self.combination_program is not None else ''),
            self.subtitles,
            self.q_and_a,
            self.extra
        ])
        return "{}\n".format(text)


class FestivalData:

    curr_screen_id = None

    def __init__(self, plandata_dir):
        self.films = []
        self.filminfos = []
        self.screenings = []
        self.filmid_by_url = {}
        self.filmid_by_key = {}
        self.screen_by_location = {}
        self.films_file = os.path.join(plandata_dir, "films.csv")
        self.filmids_file = os.path.join(plandata_dir, "filmids.txt")
        self.filminfo_file = os.path.join(plandata_dir, "filminfo.xml")
        self.screens_file = os.path.join(plandata_dir, "screens.csv")
        self.screenings_file = os.path.join(plandata_dir, "screenings.csv")
        self.curr_film_id = None
        self.film_seqnr = 0
        self.read_articles()
        self.read_screens()
        self.read_filmids()

    def _filmkey(self, title, url):
        return title

    def create_film(self, title, url):
        filmid = self.new_film_id(self._filmkey(title, url))
        if filmid not in [f.filmid for f in self.films]:
            self.film_seqnr += 1
            return Film(self.film_seqnr, filmid, title, url)
        else:
            return None

    def new_film_id(self, key):
        try:
            filmid = self.filmid_by_key[key]
        except KeyError:
            self.curr_film_id += 1
            filmid = self.curr_film_id
            self.filmid_by_key[key] = filmid
        return filmid

    def get_film_by_key(self, title, url):
        filmid = self.filmid_by_key[self._filmkey(title, url)]
        films = [film for film in self.films if film.filmid == filmid]
        if len(films) > 0:
            return films[0]
        return None

    def get_filmid(self, url):
        return self.get_film_by_key(None, url).filmid

    def get_screen(self, city, name):
        screen_key = (city, name)
        try:
            screen = self.screen_by_location[screen_key]
        except KeyError:
            self.curr_screen_id += 1
            screen_id = self.curr_screen_id
            abbr = name.replace(" ", "").lower()
            print(f"NEW LOCATION:  '{city} {name}' => {abbr}")
            screen = Screen(screen_id, city, name, abbr)
            self.screen_by_location[screen_key] = screen
        return screen

    def splitrec(self, line, sep):
        end = sep + '\r\n'
        return line.rstrip(end).split(sep)

    def read_articles(self):
        with open(articles_file) as f:
            articles = [Article(self.splitrec(line, ":")) for line in f]
        Film.articles_by_language = dict([(a._key(), a) for a in articles])

    def read_filmids(self):
        try:
            with open(self.filmids_file, 'r') as f:
                records = [self.splitrec(line, ';') for line in f]
            for record in records:
                filmid = int(record[0])
                title = record[1]
                url = record[2]
                self.filmid_by_url[url] = filmid
                self.filmid_by_key[self._filmkey(title, url)] = filmid
        except OSError:
            pass
        try:
            self.curr_film_id = max(self.filmid_by_key.values())
        except ValueError:
            self.curr_film_id = 0
        print(f"Done reading {len(self.filmid_by_url)} records from {self.filmids_file}.")

    def read_screens(self):
        def create_screen(fields):
            screen_id = int(fields[0])
            city = fields[1]
            name = fields[2]
            abbr = fields[3]
            screen_type = fields[4]
            if screen_type not in Screen.screen_types:
                raise ScreenTypeError(abbr, screen_type)
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

    def sort_films(self):
        seqnr = 0
        for film in sorted(self.films):
            seqnr += 1
            film.seqnr = seqnr

    def screening_can_go_to_planner(self, screening):
        return screening.audience == "publiek"

    def film_can_go_to_planner(self, filmid):
        return len([s for s in self.screenings if s.film.filmid == filmid and self.screening_can_go_to_planner(s)]) > 0

    def write_films(self):
        public_films = [f for f in self.films if self.film_can_go_to_planner(f.filmid)]
        if len(self.films):
            with open(self.films_file, 'w') as f:
                f.write(self.films[0].film_repr_csv_head())
                for film in public_films:
                    f.write(repr(film))
        print(f'Done writing {len(public_films)} of {len(self.films)} records to {self.films_file}.')
        if len(self.films):
            with open(self.filmids_file, 'w') as f:
                for film in self.films:
                    f.write(film.filmid_repr())
            print(f'Done writing {len(self.films)} records to {self.filmids_file}.')

    def write_filminfo(self):
        info_count = 0
        filminfos = ET.Element('FilmInfos')
        for filminfo in [i for i in self.filminfos if self.film_can_go_to_planner(i.filmid)]:
            info_count += 1
            id = str(filminfo.filmid)
            article = filminfo.article
            descr = filminfo.description
            info = ET.SubElement(filminfos, 'FilmInfo',
                                 FilmId=id,
                                 FilmArticle=article,
                                 FilmDescription=descr,
                                 InfoStatus='Complete')
            combination_programs = ET.SubElement(info, 'CombinationPrograms')
            for combination_url in filminfo.combination_urls:
                _ = ET.SubElement(combination_programs, 'CombinationProgram',
                                  CombinationProgramId=str(self.get_filmid(combination_url)))
            screened_films = ET.SubElement(info, 'ScreenedFilms')
            for screened_film in filminfo.screened_films:
                _ = ET.SubElement(screened_films, 'ScreenedFilm',
                                  ScreenedFilmId=str(screened_film.filmid),
                                  Title=screened_film.title,
                                  Description=screened_film.description)
        tree = ET.ElementTree(filminfos)
        tree.write(self.filminfo_file, encoding='utf-8', xml_declaration=True)
        print(f"Done writing {info_count} records to {self.filminfo_file}.")

    def write_screens(self):
        with open(self.screens_file, 'w') as f:
            for screen in self.screen_by_location.values():
                f.write(repr(screen))
        print(f"Done writing {len(self.screen_by_location)} records to {self.screens_file}.")

    def write_screenings(self):
        public_screenings = []
        if len(self.screenings):
            public_screenings = [s for s in self.screenings if self.screening_can_go_to_planner(s) and not s.film.is_part_of_combination(self)]
            with open(self.screenings_file, 'w') as f:
                f.write(self.screenings[0].screening_repr_csv_head())
                for screening in public_screenings:
                    f.write(repr(screening))
        print(f"Done writing {len(public_screenings)} of {len(self.screenings)} records to {self.screenings_file}.")


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class FilmTitleError(Error):
    """Exception raised when a film title is empty."""

    def __init__(self, film_description):
        self.film_description = film_description

    def __str__(self):
        return f'Film has no title. Description: {self.film_description}'


class ScreenTypeError(Error):
    """Exception raised when an unknown screen type is being processed."""

    def __init__(self, screen_abbr, screen_type):
        self.screen_abbr = screen_abbr
        self.screen_type = screen_type

    def __str__(self):
        return f'Screen with abbreviation \'{self.screen_abbr}\' has unknown type: {self.screen_type}'


if __name__ == "__main__":
    print("This module is not executable.")
