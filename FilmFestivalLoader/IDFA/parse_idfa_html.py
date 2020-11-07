#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 20:36:18 2020

@author: maarten
"""

import os
import sys
import re
import datetime
from html.parser import HTMLParser

sys.path.insert(0, "/Users/maarten/Projects/FilmFestivalPlanner/FilmFestivalLoader/Shared")
import planner_interface as planner
import application_tools as app_tools
import web_tools

# Parameters.
festival = 'IDFA'
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
    screenings_loader = ScreeningsLoader()
    screenings_loader.get_screenings(idfa_data)
    
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


class ScreeningsLoader:

    def __init__(self):
        pass

    def get_screenings(self, idfa_data):
        for film in idfa_data.films:
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
                parser = FilmPageParser(idfa_data, film)
                parser.feed(film_data)

class HtmlPageParser(HTMLParser):
    
    def __init__(self, idfa_data, debug_prefix):
        HTMLParser.__init__(self)
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
            self.film = self.idfa_data.create_film(self.title, self.url)
            if self.duration == None:
                try:
                    minutes = self.last_data[3]
                    self.print_debug("--", f"Unrecognized DURATION, {minutes} used")
                    print(f"-- Unrecognized DURATION, {minutes} used")
                    self.duration = datetime.timedelta(minutes=int(minutes))
                except IndexError as ie:
                    Globals.error_collector.add(str(ie), f"Not enough data cashed to reconstruct a duration for {self.title}")
                    self.duration = datetime.timedelta(minutes=0)
            try:
                self.film.medium_category = 'films'
                self.film.duration = self.duration
                print(f"Adding FILM: {self.title}")
                self.idfa_data.films.append(self.film)
                if self.description is not None:
                    filminfo = planner.FilmInfo(self.film.filmid, self.description, '')
                    self.idfa_data.filminfos.append(filminfo)
            except AttributeError as e:
                print(f"Error: {e}")
                Globals.error_collector.add(str(e), f"{self.title}")
 
    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
        if self.in_title:
            self.title = data
            self.in_title = False
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


class FilmPageParser(HtmlPageParser):

    def __init__(self, idfa_data, film):
        HtmlPageParser.__init__(self, idfa_data, "F")
        self.film = film
        self.debugging = True
        self.in_article = False
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

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
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

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)
        if tag == 'title':
            self.in_article = True
 
    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)


class IdfaData(planner.FestivalData):

    def _init__(self, plandata_dir):
        planner.FestivalData.__init__(self, plandata_dir)


if __name__ == "__main__":
    main()
