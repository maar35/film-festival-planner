#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide all interfaces to the Planner Project, including shared tools.

Created on Sat Oct 10 18:13:42 2020

@author: maarten
"""
import csv
import os
import re
import xml.etree.ElementTree as Tree
from enum import Enum, auto
from unicodedata import normalize

import yaml

from Shared.application_tools import config, pr_info

INTERFACE_DIR = os.path.expanduser(f"~/{config()['Paths']['LoaderSharedDirectory']}")
COMMON_DATA_DIR = os.path.expanduser(f"~/{config()['Paths']['CommonDataDirectory']}")
ARTICLES_FILE = os.path.join(INTERFACE_DIR, "articles.txt")
FILMS_FILE_HEADER = config()['Headers']['FilmsFileHeader']


def get_screen_from_parse_name(festival_data, screen_parse_name, split_location):
    city_name, theater_parse_name, screen_abbreviation = split_location(screen_parse_name)
    screen = festival_data.get_screen(
        city_name,
        screen_parse_name,
        theater_parse_name=theater_parse_name,
        screen_abbreviation=screen_abbreviation
    )
    return screen


def link_screened_film(festival_data, sub_film, main_film, main_film_info=None, screened_film_type=None):
    sub_film_info = sub_film.film_info(festival_data)
    sub_film_info.combination_films.append(main_film)
    screened_film = ScreenedFilm(sub_film.film_id, sub_film.title, sub_film_info.description, screened_film_type)
    main_film_info = main_film_info or main_film.film_info(festival_data)
    main_film_info.screened_films.append(screened_film)


def write_lists(festival_data, write_film_list, write_other_lists):

    if write_film_list or write_other_lists:
        pr_info("\n\nWRITING LISTS")

    if write_film_list:
        festival_data.sort_films()
        festival_data.write_films()
    else:
        pr_info("Films NOT WRITTEN")

    if write_other_lists:
        festival_data.write_film_ids()
        festival_data.write_csv_filminfo()
        festival_data.write_xml_filminfo()
        festival_data.write_yaml_filminfo()
        festival_data.write_new_cities()
        festival_data.write_new_theaters()
        festival_data.write_new_screens()
        festival_data.write_screenings()
        festival_data.write_sections()
        festival_data.write_subsections()
    else:
        pr_info("Film info, screens and screenings NOT WRITTEN")


class UnicodeMapper:
    form = 'NFD'
    encoding = 'utf-8'

    @classmethod
    def normalize(cls, string, encoding=None):
        encoding = encoding or cls.encoding
        normalized_str = ''
        for char in string:
            n = normalize(cls.form, char).encode(encoding)
            normalized_str += n.decode(encoding)[0]
        return normalized_str


class Article:

    def __init__(self, language_articles_tuple):
        self.language = language_articles_tuple[0]
        self.articles = language_articles_tuple[1].split()

    def key(self):
        return self.language

    def is_article(self, word):
        return word.lower() in self.articles


class Film:

    category_films = "Films"
    category_combinations = "CombinedProgrammes"
    category_events = "Events"
    category_by_string = {
        'films': category_films,
        'combinations': category_combinations,
        'events': category_events,
    }
    minutes_mark = "′"
    articles_by_language = {}
    language_by_title = {}
    re_alpha = re.compile(r'^[a-zA-Z]')

    def __init__(self, seq_nr, film_id, title, url, duration=None, medium_category=None):
        self.seq_nr = seq_nr
        self.film_id = film_id
        self.title = title
        self.url = url
        self.title_language = self.language()
        self.subsection = None
        self.duration = duration
        self.medium_category = medium_category
        self.reviewer = None
        self.sort_string = self.lower(self.strip_article())

    def __str__(self):
        return ", ".join([str(self.film_id),
                          self.title,
                          self.duration_str() if self.duration else '',
                          self.medium_category])

    def __lt__(self, other):
        return self.sort_string < other.sort_string

    @staticmethod
    def film_repr_csv_head():
        return FILMS_FILE_HEADER

    def row_repr(self):
        row = [
            str(self.seq_nr),
            str(self.film_id),
            self.sort_string,
            self.title,
            self.title_language,
            str(self.subsection.subsection_id) if self.subsection else '',
            self.duration_str() if self.duration else '0' + self.minutes_mark,
            self.category_by_string[self.medium_category],
            self.reviewer if self.reviewer else '',
            self.url
        ]
        return row

    def short_str(self):
        return f'{self.title} ({self.duration_str()})'

    @staticmethod
    def lower(string):
        return UnicodeMapper.normalize(string).lower()

    @staticmethod
    def duration_to_minutes(duration):
        return int(duration.total_seconds() / 60)

    def duration_str(self):
        minutes = Film.duration_to_minutes(self.duration)
        return str(minutes) + self.minutes_mark

    def language(self):
        try:
            language = Film.language_by_title[self.title]
            return language
        except KeyError:
            return 'en'

    def screenings(self, festival_data):
        return [s for s in festival_data.screenings if s.film.film_id == self.film_id]

    def film_info(self, festival_data):
        infos = [i for i in festival_data.filminfos if i.film_id == self.film_id]
        try:
            return infos[0]
        except IndexError:
            return FilmInfo(None, '', '')

    def is_part_of_combination(self, festival_data):
        return len(self.film_info(festival_data).combination_films) > 0

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
            first = title[:i]
            rest = title[i:].lstrip()
        if not self.articles_by_language[self.title_language].is_article(first):
            return title
        return "{}, {}".format(rest, first)


class ScreenedFilmType(Enum):
    PART_OF_COMBINATION_PROGRAM = auto()
    SCREENED_BEFORE = auto()
    SCREENED_AFTER = auto()
    DIRECTLY_COMBINED = auto()


class ScreenedFilm:

    def __init__(self, film_id, title, description, screened_film_type=None):
        """
        Screened Film: representation of a film that
        is displayed as part of combination program.

        @type film_id: int
        @type title: str
        @type description: str
        """
        screened_film_type = screened_film_type or ScreenedFilmType.PART_OF_COMBINATION_PROGRAM
        self.film_id = film_id
        if title is None or len(title) == 0:
            raise FilmTitleError(description)
        self.title = title
        self.description = description.strip() if description is not None else ''
        self.screened_film_type = screened_film_type

    def __str__(self):
        return ' - '.join([str(self.film_id), self.title])


class FilmInfo:

    def __init__(self, film_id, description, article, metadata=None, combination_films=None, screened_films=None):
        self.film_id = film_id
        self.description = description.strip()
        self.metadata = metadata or {}
        self.article = article.strip()
        self.combination_films = combination_films or []
        self.screened_films = screened_films or []

    def __str__(self):
        combinations_str = '\nCombinations:\n' + '\n'.join([str(cf) for cf in self.combination_films])
        screened_str = '\nScreened:\n' + '\n'.join([str(sf) for sf in self.screened_films])
        return '\n'.join([str(self.film_id), self.description, self.article, combinations_str, screened_str]) + '\n'

    def format_metadata(self):
        properties = [f'{key}: {value}' for (key, value) in self.metadata.items()]
        return '\n'.join(properties)


class Section:

    def __init__(self, section_id, name, color=None):
        self.section_id = section_id
        self.name = name
        self.color = color if color is not None else 'grey'

    def __repr__(self):
        text = ';'.join([str(self.section_id), self.name, self.color])
        return f'{text}\n'


class Subsection:

    def __init__(self, subsection_id, section, name, url, description=None):
        self.subsection_id = subsection_id
        self.section = section
        self.name = name
        self.url = url
        self.description = description if description is not None else ''

    def __repr__(self):
        text = ';'.join([
            str(self.subsection_id),
            str(self.section.section_id),
            self.name,
            self.description if self.description is not None else '',
            self.url
        ])
        return f'{text}\n'


class City:
    default_country = 'nl'

    def __init__(self, city_id, name, country=None, new=True):
        self.city_id = city_id
        self.name = name
        self.country = country or self.default_country
        self.new = new

    def __str__(self):
        return self.name

    def __repr__(self):
        text = ';'.join([str(self.city_id), self.name, self.country])
        return f'{text}\n'

    def key(self):
        return self.country, self.name


class Theater:
    default_prio = 1

    def __init__(self, theater_id, city, name, abbr, prio=None, new=True):
        self.theater_id = theater_id
        self.city = city
        self.name = name
        self.abbr = abbr
        self.prio = prio or self.default_prio
        self.new = new

    def __str__(self):
        return self.name

    def __repr__(self):
        text = ';'.join([
            str(self.theater_id),
            str(self.city.city_id),
            self.name,
            self.abbr,
            str(self.prio)])
        return f'{text}\n'

    def key(self):
        return self.city.city_id, self.name


class Screen:
    screen_types = ['OnLine', 'OnDemand', 'Physical']

    def __init__(self, screen_id, theater, name, abbr, screen_type='Physical', new=True):
        self.screen_id = screen_id
        self.theater = theater
        self.name = name
        self.abbr = abbr
        self.type = screen_type if name else 'OnLine'
        self.new = new

    def __str__(self):
        return f'{self.theater.abbr}{self.abbr}'

    def __repr__(self):
        text = ';'.join([
            str(self.screen_id),
            str(self.theater.theater_id),
            self.name,
            self.abbr,
            str(self.screen_type_nr(self.type))
        ])
        return f'{text}\n'

    def key(self):
        return self.theater.theater_id, self.name

    @staticmethod
    def screen_type_nr(screen_type_name):
        return Screen.screen_types.index(screen_type_name) + 1

    @staticmethod
    def screen_type_name(screen_type_nr):
        return Screen.screen_types[screen_type_nr - 1]


class Screening:
    audience_type_public = 'publiek'

    def __init__(self, film, screen, start_datetime, end_datetime, qa, extra, audience,
                 combination_program=None, subtitles='', sold_out=None):
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
        self.sold_out = sold_out

    def __str__(self):
        start_time = self.start_datetime.isoformat(sep=" ", timespec="minutes")
        end_time = self.end_datetime.time().isoformat()
        return f'{start_time} - {end_time}, {self.screen.abbr}, {self.film.title}'

    def __eq__(self, other):
        lhs = (self.film.film_id, self.screen.screen_id, self.start_datetime, self.end_datetime)
        rhs = (other.film.film_id, other.screen.screen_id, other.start_datetime, other.end_datetime)
        return lhs == rhs

    def __hash__(self):
        return hash((
            self.film.film_id, self.screen.screen_id, self.start_datetime, self.end_datetime
        ))

    @staticmethod
    def screening_repr_csv_head():
        text = ";".join([
            "film_id",
            "screen_id",
            "start_time",
            "end_time",
            "combination_id",
            "subtitles",
            "qanda",
            "extra",
            "sold_out",
        ])
        return "{}\n".format(text)

    def __repr__(self):
        text = ";".join([
            str(self.film.film_id),
            str(self.screen.screen_id),
            self.start_datetime.isoformat(sep=' '),
            self.end_datetime.isoformat(sep=' '),
            str(self.combination_program.film_id if self.combination_program is not None else ''),
            self.subtitles,
            self.q_and_a,
            self.extra,
            str(self.sold_out) if self.sold_out else ''
        ])
        return f'{text}\n'

    def is_public(self):
        return self.audience == self.audience_type_public

    def coincides(self, other_screening):
        return ScreeningKey(other_screening) == ScreeningKey(self)

    def is_part_of(self, other_screening):
        ok = self.screen.screen_id == other_screening.screen.screen_id
        if ok:
            ok = other_screening.start_datetime <= self.start_datetime
        if ok:
            ok = other_screening.end_datetime >= self.end_datetime
        return ok


class ScreeningKey:

    def __init__(self, screening):
        self.screen = screening.screen
        self.start_dt = screening.start_datetime
        self.end_dt = screening.end_datetime

    def __str__(self):
        return "{} {}-{} in {}".format(
            self.start_dt.date().isoformat(),
            self.start_dt.time().isoformat(timespec='minutes'),
            self.end_dt.time().isoformat(timespec='minutes'),
            self.screen)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash((self.screen, self.start_dt, self.end_dt))


class FestivalData:
    curr_city_id = None
    curr_theater_id = None
    curr_screen_id = None
    curr_film_id = None
    curr_section_id = None
    curr_subsection_id = None
    common_data_dir = COMMON_DATA_DIR
    dialect = None
    write_verbose = True

    def __init__(self, default_city_name, plandata_dir, common_data_dir=None):
        self.default_city_name = default_city_name
        self.common_data_dir = common_data_dir or self.common_data_dir
        self.films = []
        self.filminfos = []
        self.screenings = []
        self.title_by_film_id = {}
        self.film_id_by_url = {}
        self.film_id_by_key = {}
        self.section_by_name = {}
        self.section_by_id = {}
        self.subsection_by_name = {}
        self.screen_by_location = {}
        self.theater_by_location = {}
        self.city_by_location = {}
        self.city_by_id = {}
        self.set_csv_dialect()
        self.films_file = os.path.join(plandata_dir, 'films.csv')
        self.filmids_file = os.path.join(plandata_dir, 'filmids.txt')
        self.filminfo_csv_file = os.path.join(plandata_dir, 'filminfo.csv')
        self.filminfo_yaml_file = os.path.join(plandata_dir, 'filminfo.yml')
        self.filminfo_xml_file = os.path.join(plandata_dir, 'filminfo.xml')
        self.sections_file = os.path.join(plandata_dir, 'sections.csv')
        self.subsections_file = os.path.join(plandata_dir, 'subsections.csv')
        self.subsections_file = os.path.join(plandata_dir, 'subsections.csv')
        self.cities_file = os.path.join(self.common_data_dir, 'cities.csv')
        self.new_cities_file = os.path.join(self.common_data_dir, 'new_cities.csv')
        self.theaters_file = os.path.join(self.common_data_dir, 'theaters.csv')
        self.new_theaters_file = os.path.join(self.common_data_dir, 'new_theaters.csv')
        self.screens_file = os.path.join(self.common_data_dir, 'screens.csv')
        self.new_screens_file = os.path.join(self.common_data_dir, 'new_screens.csv')
        self.screenings_file = os.path.join(plandata_dir, 'screenings.csv')
        self.film_seqnr = 0
        self.read_articles()
        self.read_sections()
        self.read_subsections()
        self.read_cities()
        self.read_theaters()
        self.read_screens()
        self.read_film_ids()

    def set_csv_dialect(self):
        self.dialect = csv.unix_dialect
        self.dialect.delimiter = ';'
        self.dialect.quotechar = '"'
        self.dialect.doublequote = True
        self.dialect.quoting = csv.QUOTE_MINIMAL

    def film_key(self, title, url):
        return title

    def new_film_id(self, key):
        try:
            film_id = self.film_id_by_key[key]
        except KeyError:
            self.curr_film_id += 1
            film_id = self.curr_film_id
            self.film_id_by_key[key] = film_id
        return film_id

    def create_film(self, title, url, duration=None, medium_category=None):
        film_id = self.new_film_id(self.film_key(title, url))
        if film_id not in [f.film_id for f in self.films]:
            self.film_seqnr += 1
            self.title_by_film_id[film_id] = title
            self.film_id_by_url[url] = film_id
            return Film(self.film_seqnr, film_id, title, url, duration=duration, medium_category=medium_category)
        return None

    def add_film(self, title, url, duration=None, medium_category=None):
        title_exists = title in self.title_by_film_id.values()
        url_exists = url in self.film_id_by_url.keys()
        match [title_exists, url_exists]:
            case [False, False]:
                # Create new film.
                film = self.create_film(title, url, duration=duration, medium_category=medium_category)
                if film:
                    self.films.append(film)
            case [True, True]:
                # Update existing film.
                film = self.get_film_by_key(title, url)
                film.duration = duration or film.duration
                film.medium_category = medium_category or film.medium_category
            case _:
                film = None
        return film

    def get_film_by_key(self, title, url):
        key = self.film_key(title, url)
        try:
            film_id = self.film_id_by_key[key]
        except KeyError:
            raise KeyError(f'Key ({key}) not found in film dictionary')
        else:
            films = [film for film in self.films if film.film_id == film_id]
            if len(films) == 0:
                raise ValueError(f'Key ({key}) found, but no film found with film ID ({film_id})')
        return films[0]

    def get_filmid(self, url):
        return self.get_film_by_key(None, url).film_id

    def get_film_by_id(self, film_id):
        films = [f for f in self.films if f.film_id == film_id]
        if len(films) > 0:
            return films[0]
        return None

    def get_section(self, name, color=None, color_by_id=None):
        if name is None:
            return None
        try:
            section = self.section_by_name[name]
        except KeyError:
            self.curr_section_id += 1
            if color_by_id and not color:
                try:
                    color = color_by_id[self.curr_section_id]
                except KeyError:
                    color = None
            section = Section(self.curr_section_id, name, color=color)
            self.section_by_name[name] = section
            self.section_by_id[section.section_id] = section
        return section

    def get_subsection(self, name, url, section):
        if name is None:
            return None
        try:
            subsection = self.subsection_by_name[name]
        except KeyError:
            self.curr_subsection_id += 1
            subsection = Subsection(self.curr_subsection_id, section, name, url)
            self.subsection_by_name[name] = subsection
        return subsection

    def get_city_by_name(self, city_name, country=None):
        country = country or City.default_country
        city_name = city_name or self.default_city_name
        city_key = (country, city_name)
        try:
            city = self.city_by_location[city_key]
        except KeyError:
            self.curr_city_id += 1
            city_id = self.curr_city_id
            city = City(city_id, city_name, country)
            self.city_by_location[city_key] = city
        return city

    def get_city_by_id(self, city_id):
        try:
            city = self.city_by_id[city_id]
        except KeyError:
            raise KeyError(f'City ID ({city_id}) not found in dictionary')
        return city

    def get_theater(self, city_name, name):
        city = self.get_city_by_name(city_name)
        name = name or f'{city.name}-theater'
        theater_key = (city.city_id, name)
        try:
            theater = self.theater_by_location[theater_key]
        except KeyError:
            self.curr_theater_id += 1
            theater_id = self.curr_theater_id
            abbr = name.replace(' ', '').lower()
            theater = Theater(theater_id, city, name, abbr)
            self.theater_by_location[theater_key] = theater
        return theater

    def get_screen(self, city_name, screen_parse_name,
                   theater_parse_name=None, screen_abbreviation=None, verbose=True):
        theater = self.get_theater(city_name, theater_parse_name)
        screen_key = (theater.theater_id, screen_parse_name)
        try:
            screen = self.screen_by_location[screen_key]
        except KeyError:
            self.curr_screen_id += 1
            screen_id = self.curr_screen_id
            abbr = (screen_abbreviation or screen_parse_name).replace(' ', '').lower()
            screen_type = 'OnDemand' if 'ondemand' in abbr or 'on demand' in screen_parse_name\
                else 'OnLine' if abbr.startswith('online')\
                else 'Physical'
            if verbose:
                pr_info(f"NEW SCREEN:  '{theater.city}' '{theater.name}' '{screen_parse_name}' => {abbr}")
            screen = Screen(screen_id, theater, screen_parse_name, abbr, screen_type)
            self.screen_by_location[screen_key] = screen
        return screen

    def get_screen_by_id(self, screen_id):
        screens = [screen for screen in self.screen_by_location.values() if screen.screen_id == screen_id]
        return screens[0] if screens else None

    @staticmethod
    def split_rec(line, sep):
        end = sep + '\r\n'
        return line.rstrip(end).split(sep)

    def read_articles(self):
        with open(ARTICLES_FILE) as f:
            articles = [Article(self.split_rec(line, ":")) for line in f]
        Film.articles_by_language = dict([(a.key(), a) for a in articles])

    def read_film_ids(self):
        try:
            with open(self.filmids_file, 'r') as f:
                records = [self.split_rec(line, ';') for line in f]
            for record in records:
                film_id = int(record[0])
                title = record[1]
                url = record[2]
                self.film_id_by_url[url] = film_id
                self.film_id_by_key[self.film_key(title, url)] = film_id
                self.title_by_film_id[film_id] = title
        except OSError:
            pass

        try:
            self.curr_film_id = max(self.film_id_by_key.values())
        except ValueError:
            self.curr_film_id = 0
        pr_info(f"Done reading {len(self.film_id_by_url)} records from {self.filmids_file}.")

    def read_sections(self):
        try:
            with open(self.sections_file, 'r') as f:
                records = [self.split_rec(line, ';') for line in f]
            for record in records:
                section_id = int(record[0])
                name = record[1]
                color = record[2]
                section = Section(section_id, name, color)
                self.section_by_name[name] = section
                self.section_by_id[section_id] = section
        except (OSError, IndexError):
            pass

        try:
            self.curr_section_id = max(self.section_by_id.keys())
        except ValueError:
            self.curr_section_id = 0

    def read_subsections(self):
        try:
            with open(self.subsections_file, 'r') as f:
                records = [self.split_rec(line, ';') for line in f]
            for record in records:
                subsection_id = int(record[0])
                section_id = int(record[1])
                name = record[2]
                description = record[3]
                url = record[4]
                section = self.section_by_id[section_id]
                self.subsection_by_name[name] = Subsection(subsection_id, section, name, url, description)
        except (OSError, IndexError):
            pass

        try:
            subsection_ids = [subsection.subsection_id for subsection in self.subsection_by_name.values()]
            self.curr_subsection_id = max(subsection_ids)
        except ValueError:
            self.curr_subsection_id = 0

    def read_cities(self):
        def create_city(fields):
            city_id = int(fields[0])
            name = fields[1]
            country = fields[2]
            return City(city_id, name, country, new=False)

        try:
            with open(self.cities_file, 'r') as f:
                cities = [create_city(self.split_rec(line, ';')) for line in f]
            self.city_by_location = {city.key(): city for city in cities}
            self.city_by_id = {city.city_id: city for city in cities}
        except OSError:
            cities = []

        try:
            self.curr_city_id = max(city.city_id for city in cities)
        except ValueError:
            self.curr_city_id = 0

    def read_theaters(self):
        def create_theater(fields):
            theater_id = int(fields[0])
            city = self.get_city_by_id(int(fields[1]))
            name = fields[2]
            abbr = fields[3]
            prio = fields[4]
            return Theater(theater_id, city, name, abbr, prio, new=False)

        try:
            with open(self.theaters_file, 'r') as f:
                theaters = [create_theater(self.split_rec(line, ';')) for line in f]
        except OSError:
            theaters = []
        else:
            self.theater_by_location = {theater.key(): theater for theater in theaters}

        try:
            self.curr_theater_id = max(theater.theater_id for theater in theaters)
        except ValueError:
            self.curr_theater_id = 0

    def read_screens(self):
        def create_screen(fields):
            screen_id = int(fields[0])
            theater_id = int(fields[1])
            name = fields[2]
            abbr = fields[3]
            screen_type = Screen.screen_type_name(int(fields[4]))
            if screen_type not in Screen.screen_types:
                raise ScreenTypeError(abbr, screen_type)
            theaters = [theater for theater in self.theater_by_location.values() if theater.theater_id == theater_id]
            if len(theaters) == 1:
                theater = theaters[0]
            else:
                raise TheaterIdError(abbr, theater_id)
            return Screen(screen_id, theater, name, abbr, screen_type, new=False)

        try:
            with open(self.screens_file, 'r') as f:
                screens = [create_screen(self.split_rec(line, ';')) for line in f]
            self.screen_by_location = {screen.key(): screen for screen in screens}
        except OSError:
            pass

        try:
            self.curr_screen_id = max([screen.screen_id for screen in self.screen_by_location.values()])
        except ValueError:
            self.curr_screen_id = 0

    def print_combi_screenings(self, combi_program_id):
        def print_screening(f, s):
            print(f'{f.title:36} {s.start_datetime}-{s.end_datetime} {s.screen.name}')

        combi_program = self.get_film_by_id(combi_program_id)
        combi_info = combi_program.film_info(self)
        screened_films = [self.get_film_by_id(sf.film_id) for sf in combi_info.screened_films]
        screenings_by_title = {sf.title: sf.screenings(self) for sf in screened_films}
        print()
        print(f'Print the {len(combi_program.screenings(self))} screenings of {combi_program.title}, '
              f'{len(screened_films)} screened films')
        for cs in sorted(combi_program.screenings(self), key=lambda s: s.start_datetime):
            print()
            print_screening(combi_program, cs)
            for sf in screened_films:
                s_filtered = [s for s in screenings_by_title[sf.title] if s.start_datetime == cs.start_datetime]
                for s in s_filtered:
                    print_screening(sf, s)

    def create_yaml_object(self):
        def can_go(film_info):
            return self.film_can_go_to_planner(film_info.film_id)

        def get_info_dict(list_attr):
            info_dict = {}
            list_by_id = {i.film_id: getattr(i, list_attr) for i in self.filminfos if can_go(i)}
            for film_id, listed_films in list_by_id.items():
                info_dict_list = [{
                    'film_id': listed_film.film_id,
                    'title': listed_film.title,
                } for listed_film in listed_films]
                info_dict[film_id] = info_dict_list
            return info_dict

        # Get metadata per film id.
        metadata_dict = {i.film_id: i.metadata for i in self.filminfos if can_go(i)}

        # Get combination films per film id.
        combi_dict = get_info_dict('combination_films')

        # Get screened films per film id.
        screened_dict = get_info_dict('screened_films')

        # Create the YAML object.
        yaml_object = {
            'metadata': metadata_dict,
            'screened_films': screened_dict,
            'combinations': combi_dict,
        }

        return yaml_object

    def sort_films(self):
        seq_nr = 0
        for film in sorted(self.films):
            seq_nr += 1
            film.seqnr = seq_nr

    def screening_can_go_to_planner(self, screening):
        return screening.is_public() and not screening.film.is_part_of_combination(self)

    def film_can_go_to_planner(self, film_id):
        return len([s for s in self.screenings if s.film.film_id == film_id and self.screening_can_go_to_planner(s)]) > 0

    def write_films(self):
        public_films = [f for f in self.films if self.film_can_go_to_planner(f.film_id)]
        if len(self.films):
            with open(self.films_file, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile, self.dialect)
                csv_writer.writerow(Film.film_repr_csv_head())
                for film in public_films:
                    csv_writer.writerow(film.row_repr())
            pr_info(f'Done writing {len(public_films)} of {len(self.films)} records to {self.films_file}.')
        else:
            pr_info('No films to be written.')

    def write_film_ids(self):
        film_id_count = len(self.film_id_by_url)
        if film_id_count > 0:
            with open(self.filmids_file, 'w') as f:
                for url, film_id in self.film_id_by_url.items():
                    title = self.title_by_film_id[film_id]
                    text = ";".join([str(film_id), title.replace(";", ".,"), url])
                    f.write(f'{text}\n')
            pr_info(f'Done writing {film_id_count} records to {self.filmids_file}.')

    def write_yaml_filminfo(self):
        yaml_object = self.create_yaml_object()
        with open(self.filminfo_yaml_file, 'w') as stream:
            yaml.dump(yaml_object, stream, encoding='utf-8', indent=4)
        pr_info(f'Done writing {len(yaml_object)} objects to {self.filminfo_yaml_file}.')

    def write_csv_filminfo(self):
        data = [i for i in self.filminfos if self.film_can_go_to_planner(i.film_id)]
        rows = sorted([[
            i.film_id,
            i.description,
            i.metadata['Reviewer'] if 'Reviewer' in i.metadata else ''
        ] for i in data], key=lambda row: row[0])
        with open(self.filminfo_csv_file, 'w') as csvfile:
            csv_writer = csv.writer(csvfile, self.dialect)
            csv_writer.writerows(rows)
        pr_info(f'Done writing {len(data)} records to {self.filminfo_csv_file}.')

    def write_xml_filminfo(self):
        info_count = 0
        film_infos = Tree.Element('FilmInfos')
        for filminfo in [i for i in self.filminfos if self.film_can_go_to_planner(i.film_id)]:
            info_count += 1
            id = str(filminfo.film_id)
            article = filminfo.article
            if filminfo.metadata:
                article += f'\n\n{filminfo.format_metadata()}'
            descr = filminfo.description
            info = Tree.SubElement(film_infos, 'FilmInfo',
                                   FilmId=id,
                                   FilmArticle=article,
                                   FilmDescription=descr,
                                   InfoStatus='Complete')
            combination_programs = Tree.SubElement(info, 'CombinationPrograms')
            for combination_film in filminfo.combination_films:
                _ = Tree.SubElement(combination_programs, 'CombinationProgram',
                                    CombinationProgramId=str(combination_film.film_id))
            screened_films = Tree.SubElement(info, 'ScreenedFilms')
            for screened_film in filminfo.screened_films:
                _ = Tree.SubElement(screened_films, 'ScreenedFilm',
                                    ScreenedFilmId=str(screened_film.film_id),
                                    Title=screened_film.title,
                                    Description=screened_film.description,
                                    ScreenedFilmType=screened_film.screened_film_type.name)
        tree = Tree.ElementTree(film_infos)
        tree.write(self.filminfo_xml_file, encoding='utf-8', xml_declaration=True)
        pr_info(f"Done writing {info_count} objects to {self.filminfo_xml_file}.")

    def write_sections(self):
        with open(self.sections_file, 'w') as f:
            for section in self.section_by_id.values():
                f.write((repr(section)))
        if self.write_verbose:
            pr_info(f'Done writing {len(self.section_by_id)} records to {self.sections_file}.')

    def write_subsections(self):
        with open(self.subsections_file, 'w') as f:
            for subsection in self.subsection_by_name.values():
                f.write(repr(subsection))
        pr_info(f'Done writing {len(self.subsection_by_name)} records to {self.subsections_file}.')

    def write_new_cities(self):
        new_cities = [city for city in self.city_by_location.values() if city.new]
        with open(self.new_cities_file, 'w') as f:
            for city in new_cities:
                f.write(repr(city))
        pr_info(f'Done writing {len(new_cities)} records to {self.new_cities_file}.')

    def write_new_theaters(self):
        new_theaters = [theater for theater in self.theater_by_location.values() if theater.new]
        with open(self.new_theaters_file, 'w') as f:
            for theater in new_theaters:
                f.write(repr(theater))
        pr_info(f'Done writing {len(new_theaters)} records to {self.new_theaters_file}.')

    def write_new_screens(self):
        new_screens = [screen for screen in self.screen_by_location.values() if screen.new]
        with open(self.new_screens_file, 'w') as f:
            for screen in new_screens:
                f.write(repr(screen))
        pr_info(f'Done writing {len(new_screens)} records to {self.new_screens_file}.')

    def write_screenings(self):
        public_screenings = []
        if len(self.screenings):
            public_screenings = [s for s in self.screenings if self.screening_can_go_to_planner(s)]
            with open(self.screenings_file, 'w') as f:
                f.write(self.screenings[0].screening_repr_csv_head())
                for screening in public_screenings:
                    f.write(repr(screening))
        pr_info(f"Done writing {len(public_screenings)} of {len(self.screenings)} records to {self.screenings_file}.")


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


class TheaterIdError(Error):
    """Exception raised when an unknown theater ID is being processed."""

    def __init__(self, screen_abbr, theater_id):
        self.screen_abbr = screen_abbr
        self.theater_id = theater_id

    def __str__(self):
        return f'Screen with abbreviation \'{self.screen_abbr}\' has unknown theater id: {self.theater_id}'


if __name__ == "__main__":
    print("This module is not executable.")
