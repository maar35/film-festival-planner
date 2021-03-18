#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 18 20:56:44 2021

@author: maartenroos
"""

import os
import sys
import re
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

    # Display error when found.
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

    # comment('Parsing film pages.')
    # film_detals_loader = FilmDetailsLoader()
    # film_detals_loader.get_film_details(imagine_data)


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
        print("Screens and screenings NOT WRITTEN")


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


class HtmlPageParser(web_tools.HtmlPageParser):

    def __init__(self, imagine_data, debug_prefix):
        web_tools.HtmlPageParser.__init__(self, Globals.debug_recorder, debug_prefix)
        self.imagine_data = imagine_data
        self.debugging = False

    def attr_str(self, attr, index):
        return (str)(attr[index])


class AzPageParser(HtmlPageParser):

    def __init__(self, imagine_data):
        HtmlPageParser.__init__(self, imagine_data, 'AZ')
        self.matching_attr_value = ""
        self.debugging = True
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
            print(f'Adding FILM: {self.title} - {self.film.medium_category}')
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


class ImagineData(planner.FestivalData):

    def _init__(self, plandata_dir):
        planner.FestivalData.__init__(self, plandata_dir)

    def _filmkey(self, film, url):
        return url

    def has_public_screenings(self, filmid):
        return True


if __name__ == "__main__":
    main()
