#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct  2 21:35:14 2020

@author: maarten
"""

import re
import os
import parse_nff_html

project_dir = os.path.expanduser("~/Documents/Film/NFF/NFF2020")
webdata_dir = os.path.join(project_dir, "_website_data")
plandata_dir = os.path.join(project_dir, "_planner_data")
filmdata_file = os.path.join(plandata_dir, "filmdata.csv")
films_file = os.path.join(plandata_dir, "films.csv")
films_webroot = "https://www.filmfestival.nl/en/films/"
az_copy_paste_file_pattern = os.path.join(webdata_dir, "copy_paste_az_{:02d}.txt")
az_page_count = 6

filmparts_re = re.compile(r"^.*Films from A to Z(?P<filmparts>.*)\n1\n \n.*$", re.DOTALL)
film_re = re.compile(
r"""
     \n\ \n(?P<title>[^\n]*)\n\n           # Title preceeded by a line consisting of one space
     Duration:\ (?P<duration>[0-9]+)min\n  # Duration in minutes
     (?P<description>[^\n]*)\n             # Description is one line of text following Duration
     Director\(s\):\ (?P<directors>[^\n]*) # Directors, optionally followed by competitions
""", re.DOTALL|re.VERBOSE)
competitions_re = re.compile(r"(?P<directors>[^\n]*) Competitions: (?P<competitions>[^\n]*)")

url_by_title = {}
url_by_title['Flodder'] = 'https://www.filmfestival.nl/en/films/flodder-5'
url_by_title['De Futurotheek'] = 'https://www.filmfestival.nl/en/films/futurotheek'
url_by_title['Gooische vrouwen'] = 'https://www.filmfestival.nl/en/archive/gooische-vrouwen-2'
url_by_title['More Moiré²'] = 'https://www.filmfestival.nl/en/films/more-moire²'
url_by_title['Teledoc Campus - When You Hear the Divine Call'] = 'https://www.filmfestival.nl/en/films/teledoc-campus-a-divine-call'
url_by_title['The Undercurrent'] = 'https://www.filmfestival.nl/en/films/-1'

def main():
    festival_data = FestivalData()
    for page_number in range(az_page_count):
        az_file = az_copy_paste_file_pattern.format(page_number)
        print("Searching {}...".format(az_file), end="")
        with open(az_file, 'r') as f:
            az_text = f.read()
        film_count = parse_az(az_text, festival_data.films)
        print(" {} films found".format(film_count))
    with open(filmdata_file, 'w') as f:
        text = repr(festival_data) + "\n"
        f.write(text)
    print("\n{} films written.\n".format(len(festival_data.films)))
    
    external_data = parse_nff_html.FestivalData()
    fill_external_data(external_data, festival_data.films)
    external_data.write_films()
    get_screenings(external_data)

def get_url(title):
    if title in url_by_title.keys():
        return url_by_title[title]
    lower = title.lower()
    disquoted = re.sub("['\"]+", "", lower)
    connected = re.sub("\W+", "-", disquoted)
    frontstripped = re.sub("^\W+", "", connected)
    stripped = re.sub("\W+$", "", frontstripped)
    url = films_webroot + stripped
    return url

def fill_external_data(data, films):
    filmid = 0
    for film in films:
        filmid += 1
        seqnr = filmid
        title = film.title
        url = get_url(film.title)
        external_film = parse_nff_html.Film(seqnr, filmid, title, url)
        external_film.url = get_url(external_film.toascii(title))
        print(external_film.url)
        external_film.medium_category = "films"
        data.films.append(external_film)
    
def get_screenings(data):
    az_parser = parse_nff_html.AzProgrammeHtmlParser()
    for film in data.films:
        az_parser.film = film
        az_parser.url = film.url
        az_parser.populate_film_fields()


class Film:
    
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
    

class FestivalData:
    
    def __init__(self):
        self.films = []
        
    def __repr__(self):
        return "\n".join([str(film) for film in self.films])
    
    def write_films(self):
        pass
      
        
def parse_az(az_text, films):
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
            films.append(Film(film_match.group('title'),
                                   film_match.group('duration'),
                                   description,
                                   directors,
                                   competitions))
        return film_count


main()