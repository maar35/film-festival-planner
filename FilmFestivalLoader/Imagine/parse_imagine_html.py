#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 18 20:56:44 2021

@author: maartenroos
"""

import os
import re
import sys
import datetime
from enum import Enum, auto

shared_dir = os.path.expanduser("~/Projects/FilmFestivalPlanner/FilmFestivalLoader/Shared")
sys.path.insert(0, shared_dir)
import planner_interface as planner
import application_tools as app_tools
import web_tools

# Parameters.
festival = 'Imagine'
year = 2021
city = 'Amsterdam'
ondemand_available_hours = 48

# Directories:
documents_dir = os.path.expanduser("~/Documents/Film/{0}/{0}{1}".format(festival, year))
webdata_dir = os.path.join(documents_dir, "_website_data")
plandata_dir = os.path.join(documents_dir, "_planner_data")

# Filename formats.
film_file_format = os.path.join(webdata_dir, "filmpage_{:03d}.html")

# Files.
az_file = os.path.join(webdata_dir, "azpage_01.html")
debug_file = os.path.join(plandata_dir, "debug.txt")

# URL information.
imagine_hostname = "https://www.imaginefilmfestival.nl"
az_url_path = "/festival-" + str(year) + "/films/"


def main():
    # Initialize globals.
    Globals.error_collector = app_tools.ErrorCollector()
    Globals.debug_recorder = app_tools.DebugRecorder(debug_file)

    # Initialize a festival data object.
    imagine_data = ImagineData(plandata_dir)

    # Try parsing the web sites.
    write_film_list = False
    write_other_lists = True
    try:
        parse_imagine_sites(imagine_data)
    except KeyboardInterrupt:
        comment('Interrupted from keyboard... exiting')
        write_other_lists = False
    except Exception as e:
        Globals.debug_recorder.write_debug()
        comment('Debug info printed.')
        raise e
    else:
        write_film_list = True

    # Display errors when found.
    if Globals.error_collector.error_count() > 0:
        comment('Encountered some errors:')
        print(Globals.error_collector)

    # Write parsed information.
    comment('Done laoding Imagine data.')
    write_lists(imagine_data, write_film_list, write_other_lists)
    Globals.debug_recorder.write_debug()


def parse_imagine_sites(imagine_data):
    comment('Parsing AZ pages.')
    films_loader = FilmsLoader()
    films_loader.get_films(imagine_data)

    comment('Parsing film pages.')
    film_detals_loader = FilmDetailsLoader()
    film_detals_loader.get_film_details(imagine_data)


def comment(text):
    print(f"\n{datetime.datetime.now()}  - {text}")


def write_lists(imagine_data, write_film_list, write_other_lists):

    if write_film_list or write_other_lists:
        print("\n\nWRITING LISTS")

    if write_film_list:
        imagine_data.sort_films()
        imagine_data.write_films()
    else:
        print("Films NOT WRITTEN")

    if write_other_lists:
        imagine_data.write_filminfo()
        imagine_data.write_screens()
        imagine_data.write_screenings()
    else:
        print("Film info, screens and screenings NOT WRITTEN")


class Globals:
    error_collector = None
    debug_recorder = None


class FilmsLoader:

    def get_films(self, imagine_data):
        if os.path.isfile(az_file):
            charset = web_tools.get_charset(az_file)
            with open(az_file, 'r', encoding=charset) as f:
                az_html = f.read()
        else:
            az_url = imagine_hostname + az_url_path
            az_html = web_tools.UrlReader(Globals.error_collector).load_url(az_url, az_file)
        if az_html is not None:
            AzPageParser(imagine_data).feed(az_html)


class FilmDetailsLoader:

    def __init__(self):
        pass

    def get_film_details(self, imagine_data):
        for film in imagine_data.films:
            html_data = None
            film_file = film_file_format.format(film.filmid)
            if os.path.isfile(film_file):
                charset = web_tools.get_charset(film_file)
                with open(film_file, 'r', encoding=charset) as f:
                    html_data = f.read()
            else:
                print(f"Downloading site of {film.title}: {film.url}")
                html_data = web_tools.UrlReader(Globals.error_collector).load_url(film.url, film_file)
            if html_data is not None:
                print(f"Analysing html file {film.filmid} of {film.title} {film.url}")
                FilmPageParser(imagine_data, film).feed(html_data)


class HtmlPageParser(web_tools.HtmlPageParser):

    def __init__(self, imagine_data, debug_prefix):
        web_tools.HtmlPageParser.__init__(self, Globals.debug_recorder, debug_prefix)
        self.imagine_data = imagine_data
        self.debugging = False


class AzPageParser(HtmlPageParser):

    def __init__(self, imagine_data):
        HtmlPageParser.__init__(self, imagine_data, 'AZ')
        self.matching_attr_value = ""
        self.debugging = False
        self.init_catagories()
        self.init_film_data()

    def init_catagories(self):
        planner.Film.filmcategory_by_string['feature'] = planner.Film.category_films
        planner.Film.filmcategory_by_string['special'] = planner.Film.category_events
        planner.Film.filmcategory_by_string['talk'] = planner.Film.category_events
        planner.Film.filmcategory_by_string['workshop'] = planner.Film.category_events

    def init_film_data(self):
        self.film = None
        self.title = None
        self.url = None
        self.medium_category = None
        self.description = None
        self.duration = None
        self.sorted_title = None
        self.in_film = False
        self.await_description = False
        self.in_description = False

    def add_film(self):
        self.film = self.imagine_data.create_film(self.title, self.url)
        if self.film is None:
            Globals.error_collector.add(f'Could\'t create film from {self.title}', self.url)
        else:
            self.film.medium_category = self.medium_category
            self.film.sortstring = self.title
            self.film.duration = datetime.timedelta(seconds=0)
            self.imagine_data.films.append(self.film)

    def add_filminfo(self):
        print(f'Found description of {self.title}: {self.description}')
        filminfo = planner.FilmInfo(self.film.filmid, self.description, '')
        self.imagine_data.filminfos.append(filminfo)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
        if tag == 'li' and len(attrs) > 4 and attrs[1][0] == 'data-url':
            self.in_film = True
            self.url = attrs[1][1]
            self.title = attrs[3][1]
            self.medium_category = attrs[4][1]
            self.add_film()
        elif self.await_description and tag == 'p':
            self.await_description = False
            self.in_description = True

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)
        if self.in_film and tag == 'li':
            self.in_film = False
        elif self.in_film and tag == 'h3':
            self.await_description = True

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
        if self.in_description:
            self.description = data
            self.add_filminfo()
            self.init_film_data()


class FilmPageParser(HtmlPageParser):

    class ScreeningsParseState(Enum):
        IDLE = auto()
        IN_META_DATA = auto()
        IN_DURATION = auto()
        IN_NAMED_META = auto()
        IN_META_KEY = auto()
        AWAITING_ARTICLE = auto()
        IN_ARTICLE = auto()
        SKIP_DESCRIPTION = auto()
        IN_SCREENINGS = auto()
        IN_DATE = auto()
        IN_TIME = auto()
        IN_LOCATION = auto()
        IN_EXTRA = auto()
        DONE = auto()

    nl_month_by_name = {}
    nl_month_by_name['mar'] = 3
    nl_month_by_name['apr'] = 4

    def __init__(self, imagine_data, film):
        HtmlPageParser.__init__(self, imagine_data, "F")
        self.film = film
        self.filminfo = self.get_filminfo(self.film.filmid)
        self.debugging = False
        self.article = None
        self.combination_urls = []
        self.print_debug(f"{40 * '-'} ", f"Analysing FILM {film}, {film.url}")
        self.screened_films = []
        self.metadata = None

        self.init_screening_data()
        self.stateStack = self.StateStack(self.print_debug, self.ScreeningsParseState.IDLE)

    def init_screening_data(self):
        self.audience = 'publiek'
        self.qa = ''
        self.subtitles = ''
        self.extra = ''
        self.screen = None
        self.start_dt = None
        self.end_dt = None
        self.start_date = None
        self.times = None

    def get_filminfo(self, filmid):
        filminfos = [filminfo for filminfo in self.imagine_data.filminfos if filminfo.filmid == self.film.filmid]
        if len(filminfos) == 1:
            return filminfos[0]
        Globals.error_collector.add(f'No unique FILMINFO found for {self.film}', f'{len(filminfos)} linked filminfo records')
        return None

    def update_filminfo(self):
        if self.filminfo is not None:
            self.article = re.sub('\n\n+', '\n', self.metadata).rstrip() + '\n\n' + self.article.lstrip()
            if self.article is not None and len(self.article) > 0:
                self.filminfo.article = self.article
            elif self.article is None:
                Globals().error_collector.add('Article is None', f'{self.film} {self.film.duration_str()}')
                self.filminfo.article = ''
            else:
                Globals().error_collector.add('Article is empty string', f'{self.film} {self.film.duration_str()}')
                self.filminfo.article = ''
            self.filminfo.combination_urls = self.combination_urls
            self.filminfo.screened_films = self.screened_films
            self.print_debug(f'FILMINFO of {self.film.title} updated', f'ARTICLE: {self.filminfo.article}')
        else:
            filminfo = planner.FilmInfo(self.film.filmid, '', self.article, self.screened_films)
            self.imagine_data.filminfos.append(filminfo)

    def set_screen(self, location):
        self.screen = self.imagine_data.get_screen(city, location)

    def set_screening_info(self, data):
        self.print_debug('Found SCREENING info', data)
        parts = data.split(self.film.title)
        if len(parts) > 1:
            searchtext = parts[1]
        else:
            searchtext = data
        if 'Q&A' in searchtext:
            self.qa = 'Q&A'
        if '+' in searchtext:
            self.extra = searchtext.split('+')[1].strip()
        if searchtext.endswith('(besloten)'):
            self.audience = 'besloten'

    def add_screening(self):
        # Calculate the screening's (virtual) end time.
        duration = self.film.duration if self.screen.type != 'OnDemand' else datetime.timedelta(hours=ondemand_available_hours)
        self.end_dt = self.start_dt + duration

        # Print the screening propoerties.
        if self.audience == 'publiek':
            print()
            print(f"---SCREENING OF {self.film.title}")
            print(f"--  screen:     {self.screen}")
            print(f"--  start time: {self.start_dt}")
            print(f"--  end time:   {self.end_dt}")
            print(f"--  duration:   film: {self.film.duration_str()}  screening: {self.end_dt - self.start_dt}")
            print(f"--  audience:   {self.audience}")
            print(f"--  category:   {self.film.medium_category}")
            print(f"--  q and a:    {self.qa}")

        # Create a new screening object.
        program = None
        screening = planner.Screening(self.film, self.screen, self.start_dt,
                                      self.end_dt, self.qa, self.extra,
                                      self.audience, program, self.subtitles)

        # Add the screening to the list.
        self.imagine_data.screenings.append(screening)
        print("---SCREENING ADDED")

        # Initialize the next round of parsing.
        self.init_screening_data()

    def parse_imagine_category(self, data):
        items = data.split(',')  # Feature, 88min
        return items[0].strip()

    def parse_duration(self, data):
        items = data.split(',')  # Feature, 88min
        return datetime.timedelta(minutes=int(items[1].strip().rstrip('min')))

    def parse_date(self, data):
        items = data.split()  # 10 apr
        day = int(items[0])
        month = self.nl_month_by_name[items[1]]
        return datetime.date(year, month, day)

    def parse_time(self, data):
        items = data.split()  # 17:00 (online)
        return datetime.time.fromisoformat(items[0])

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        # Get data for film info.
        if tag == 'div' and len(attrs) > 0 and attrs[0] == ('class', 'meta'):
            self.stateStack.push(self.ScreeningsParseState.IN_META_DATA)
            self.metadata = ''
            self.stateStack.push(self.ScreeningsParseState.IN_DURATION)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_META_DATA) and tag == 'strong':
            self.stateStack.change(self.ScreeningsParseState.IN_NAMED_META)
            self.stateStack.push(self.ScreeningsParseState.IN_META_KEY)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_NAMED_META) and tag == 'strong':
            self.stateStack.push(self.ScreeningsParseState.IN_META_KEY)
        elif tag == 'div' and len(attrs) > 0 and attrs[0] == ('class', 'w6'):
            self.stateStack.push(self.ScreeningsParseState.AWAITING_ARTICLE)
        elif self.stateStack.state_is(self.ScreeningsParseState.AWAITING_ARTICLE) and tag == 'p':
            self.stateStack.change(self.ScreeningsParseState.IN_ARTICLE)
            self.article = ''
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_ARTICLE) and tag == 'strong':
            self.stateStack.push(self.ScreeningsParseState.SKIP_DESCRIPTION)

        # Get data for screenings.
        if tag == 'ul' and len(attrs) > 0 and attrs[0] == ('class', 'shows'):
            self.stateStack.push(self.ScreeningsParseState.IN_SCREENINGS)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'div' and attrs[0] == ('class', 'date'):
            self.stateStack.push(self.ScreeningsParseState.IN_DATE)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'div' and attrs[0] == ('class', 'time'):
            self.stateStack.push(self.ScreeningsParseState.IN_TIME)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'div' and attrs[0] == ('class', 'theatre'):
            self.stateStack.push(self.ScreeningsParseState.IN_LOCATION)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'div' and attrs[0] == ('class', 'extra'):
            self.stateStack.push(self.ScreeningsParseState.IN_EXTRA)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        # Get data for film info.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_META_DATA) and tag == 'div':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_NAMED_META) and tag == 'div':
            self.stateStack.pop()
            self.metadata += '\n'
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_META_KEY) and tag == 'strong':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_ARTICLE) and tag == 'div':
            self.stateStack.pop()
        elif self.stateStack.state_is(self.ScreeningsParseState.SKIP_DESCRIPTION) and tag == 'strong':
            self.stateStack.pop()

        # Get data for screenings.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_SCREENINGS) and tag == 'ul':
            self.stateStack.pop()
            self.update_filminfo()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        # Get data for film info.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_DURATION):
            self.stateStack.pop()
            self.metadata += data.strip()
            self.film.duration = self.parse_duration(data)
            self.filminfo.description = self.parse_imagine_category(data) + ' - ' + self.filminfo.description
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_META_DATA):
            self.metadata += '\n' + data.strip()
            if 'ondertiteld' in data:
                self.subtitles = data.strip()
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_NAMED_META):
            self.metadata += data
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_META_KEY):
            self.metadata += '\n' + data
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_ARTICLE):
            self.article += data

        # Get data for screenings.
        if self.stateStack.state_is(self.ScreeningsParseState.IN_DATE):
            self.stateStack.pop()
            self.start_date = self.parse_date(data)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_TIME):
            self.stateStack.pop()
            self.start_dt = datetime.datetime.combine(self.start_date, self.parse_time(data))
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_LOCATION):
            self.stateStack.pop()
            self.set_screen(data)
        elif self.stateStack.state_is(self.ScreeningsParseState.IN_EXTRA):
            self.stateStack.pop()
            self.set_screening_info(data)
            self.add_screening()


class ImagineData(planner.FestivalData):

    def _init__(self, plandata_dir):
        planner.FestivalData.__init__(self, plandata_dir)

    def _filmkey(self, film, url):
        return url

    def has_public_screenings(self, filmid):
        return True


if __name__ == "__main__":
    main()
