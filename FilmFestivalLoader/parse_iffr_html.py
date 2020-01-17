#!/usr/bin/python3

import os
import sys
from html.parser import HTMLParser
from html.entities import name2codepoint
import urllib.request
import urllib.error

version_number = "0.4"
year = 2020

az_page_count = 24
project_dir = os.path.expanduser("~/Documents/Film/IFFR/IFFR{}".format(year))
html_input_dir = os.path.join(project_dir, "_website_data")
film_file_pattern = os.path.join(html_input_dir, "filmpage_{:03d}.html")
az_file_pattern = os.path.join(html_input_dir, "azpage_{:02d}.html")
data_dir = os.path.join(project_dir, "_planner_data")
screensfile = os.path.join(data_dir, "screens.csv")
filmsfile = os.path.join(data_dir, "films.csv")
ucodefile = os.path.join(data_dir, "unicodemap.txt")
screeningsfile = os.path.join(data_dir, "screenings.csv")
debugfile = os.path.join(data_dir, "debug.txt")


class Globals:
    iffr_data = None


def main():
    writefilmlist = False
    writeotherlists = True
    
    try:
        # Instantiate the parser.
        Globals.iffr_data = IffrData()
        az_parser = AzProgrammeHtmlParser()
        print("PARSER INITIATED\n")
        
        # Get the HTML and feed it to the parser.
        az_html_reader = HtmlReader()
        az_html_reader.feed_az_pages(az_page_count, az_parser)
        
    except KeyboardInterrupt:
        print("Interrupted from keyboard... exiting")
        writeotherlists = False
    except SystemExit:
        print("Quitting now.")
    else:
        writefilmlist = True

    az_parser.write_debug()
    az_parser.print_errors()
    print("\n\nDONE FEEDING\n")

    if writefilmlist or writeotherlists:
        print("\n\nWRITING LISTS")
    
    if writeotherlists:
        Globals.iffr_data.write_screens()
        Globals.iffr_data.write_screenings()
    else:
        print("Screens and screenings NOT WRITTEN")
    
    if writefilmlist:
        Globals.iffr_data.write_films()
    else:
        print("Films NOT WRITTEN")
    
    print("\nDONE")


class MyHTMLParser(HTMLParser):
    """Example HTML parser"""
    
    def handle_starttag(self, tag, attrs):
        print("Start tag:", tag)
        for attr in attrs:
            print("     attr:", attr)

    def handle_endtag(self, tag):
        print("End tag  :", tag)

    def handle_data(self, data):
        print("Data     :", data)

    def handle_comment(self, data):
        print("Comment  :", data)

    def handle_entityref(self, name):
        c = chr(name2codepoint[name])
        print("Named ent:", c)

    def handle_charref(self, name):
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))
        print("Num ent  :", c)

    def handle_decl(self, data):
        print("Decl     :", data)


# instantiate the parser and feed it some HTML
#my_parser = MyHTMLParser()
#my_parser.feed('<a href="/nl/2019/films/%C3%A0-travers-la-lune">')
#my_parser.feed(text)


def attr_str(attr, index):
    return (str)(attr[index])


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


class Film:

    filmCategoryByString = {}
    filmCategoryByString["films"] = "Films"
    filmCategoryByString["verzamelprogrammas"] = "CombinedProgrammes"
    filmCategoryByString["events"] = "Events"
    umap_is_read = False

    def __init__(self, seqnr, filmid, title, url):
        if not self.umap_is_read:
            self.read_umap()
            self.umap_is_read = True
        self.seqnr = seqnr
        self.filmid = filmid
        self.sortedTitle = title
        self.sortstring = self.lower(self.sortedTitle)
        self.title = title
        self.titleLanguage = ""
        self.section = ""
        self.duration = ""
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
            self.titleLanguage,
            self.section,
            self.duration,
            self.filmCategoryByString[self.medium_category],
            self.url
        ])
        return "{}\n".format(text)

    def read_umap(self):
        with open(ucodefile) as f:
            self.umapkeys = f.readline().rstrip("\n").split(";")
            self.umapvalues = f.readline().rstrip("\n").split(";")

    def toascii(self, s):
        for (u, a) in zip(self.umapkeys, self.umapvalues):
            s = s.replace(u, a)
        return s

    def lower(self, s):
        return self.toascii(s).lower()


class Screening:

    def __init__(self, film, screen, startDate, startTime, endTime, audience, qa, extra):
        self.status = "ONWAAR"
        self.iAttend = "ONWAAR"
        self.attendingFriends = "ONWAAR,ONWAAR,ONWAAR"
        self.startDate = startDate
        self.screen = screen
        self.startTime = startTime
        self.endTime = endTime
        self.extra = extra
        self.filmsInScreening = 1 if len(extra) == 0 else 2
        self.qAndA = qa
        self.ticketsBought = "ONWAAR"
        self.soldOut = "ONWAAR"
        self.filmid = film.filmid
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
        text = ";".join([
            (str)(self.filmid),
            self.startDate,
            self.screen.abbr,
            self.startTime,
            self.endTime,
            (str)(self.filmsInScreening),
            self.extra,
            self.qAndA
        ])
        return "{}\n".format(text)


class IffrData:

    curr_film_id = 0

    def __init__(self):
        self.films = []
        self.filmUrls = []
        self.screenings = []
        self.filmid_by_url = {}
        self.read_screens()
        self.read_filmids()

    def new_film_id(self, url):
        try:
            filmid = self.filmid_by_url[url]
        except KeyError:
            self.curr_film_id = self.curr_film_id + 1
            filmid = self.curr_film_id
            self.filmid_by_url[url] = filmid
        return filmid

    def read_url(self, url):
        pass

    def splitrec(self, line, sep):
        end = sep + '\r\n'
        return line.rstrip(end).split(sep)

    def read_screens(self):
        with open(screensfile, 'r') as f:
            screens = [Screen(self.splitrec(line, ';')) for line in f]
        self.screenbylocation = {screen._key(): screen for screen in screens}

    def read_filmids(self):
        try:
            with open(filmsfile, 'r') as f:
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
        with open(screensfile, 'w')as f:
            for screen in self.screenbylocation.values():
                f.write(repr(screen))
        print("Done writing {} records to {}.".format(len(self.screenbylocation), screensfile))

    def write_films(self):
        with open(filmsfile, 'w') as f:
            f.write(self.films[0].film_repr_csv_head())
            for film in self.films:
                f.write(repr(film))
        print("Done writing {} records to {}.".format(len(self.films), filmsfile))

    def write_screenings(self):
        if len(self.screenings):
            with open(screeningsfile, 'w') as f:
                f.write(self.screenings[0].screening_repr_csv_head())
                for screening in [s for s in self.screenings if s.audience == "publiek"]:
                    f.write(repr(screening))
        print("Done writing {} records to {}.".format(len(self.screenings), screeningsfile))


class UrlReader:

    def read_url(self, url):
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
        headers = {'User-Agent': user_agent}
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req) as response:
                html = response.read().decode()
        except urllib.error.URLError as e:
            if hasattr(e, 'reason'):
                print('We failed to reach a server.')
                print('Reason: ', e.reason)
            elif hasattr(e, 'code'):
                print('The server couldn\'t fulfill the request.')
                print('Error code: ', e.code)
            html = ""

        return html


class FilmPageParser(HTMLParser):

    def __init__(self, film):
        HTMLParser.__init__(self)
        self.film = film
        self.screen = None
        self.start_date = ""
        self.times = ""
        self.audience = ""
        self.qa = ""
        self.extra = ""
        self.before_screenings = True
        self.in_screenings = False
        self.in_location = False
        self.in_time = False
        self.in_extra_or_qa = False
        self.matching_attr_value = ""
        self.debug_text = ""

    def add_screening(self):
        print("--  {}".format(self.film.title))
        print("--  start date: {}".format(self.start_date))
        print("--  screen:     {}".format(self.screen))
        print("--  times:      {}".format(self.times))
        print("--  audience:   {}".format(self.audience))
        print("--  category:   {}".format(self.film.medium_category))
        print("--  q and a     {}".format(self.qa))
        print("--  extra:      {}".format(self.extra))
        startDate = self.start_date.split()[0]
        startTime = self.times.split()[0]
        endTime = self.times.split()[2]
        screening = Screening(self.film, self.screen, startDate, startTime, endTime, self.audience, self.qa, self.extra)
        Globals.iffr_data.screenings.append(screening)
        print("---SCREENING ADDED")
        self.in_extra_or_qa = False
        self.qa = ""
        self.extra = ""
        self.start_date = None
        self.screen = None
        self.times = ""
        self.audience = ""

    def print_debug(self, str1, str2):
        if self.film.filmid in [100, 115, 174]:
            self.debug_text += 'F ' + str(str1) + ' ' + str(str2) + '\n'

    def match_attr(self, curr_tag, test_tag, curr_attr, test_attr):
        self.matching_attr_value = ""
        if curr_tag == test_tag:
            if attr_str(curr_attr, 0) == test_attr:
                self.matching_attr_value = attr_str(curr_attr, 1)
                return True
        return False

    def handle_starttag(self, tag, attrs):
        self.print_debug("Encountered a start tag:", tag)
        #for attr in attrs:
        #    self.print_debug("         attr:      ", attr)
        for attr in attrs:
            self.print_debug("Handling attr:      ", attr)
            if tag == "section" and attr == ("class", "film-screenings-wrapper"):
                self.in_screenings = True
                self.before_screenings = False
                self.print_debug("--  ", "ENTERING SCREENINGS SECTION")
            if self.before_screenings:
                collect_attr = "/nl/{}/verzamelprogrammas/".format(year)
                if tag == "a" and attr[0] == "href" and attr[1].startswith(collect_attr):
                    if self.film.medium_category != "verzamelprogrammas":
                        self.film.combination_url = attr[1]
                        print("--  PART OF COMBINATION: {}".format(self.film))
            if self.in_screenings:
                if tag == "span" and attr == ("class", "location"):
                    self.in_location = True
                    self.print_debug("-- ", "ENTERING LOCATION")
                if tag =="a" and attr[0] == "data-audience":
                    self.audience = attr[1]
                if tag == "small" and attr[1] == "film-label voorfilm-qa":
                    self.in_extra_or_qa = True
                if tag =="a" and attr[0] == "data-date":
                    self.start_date = attr[1]
                    #if len(self.audience) > 0 and len(self.film.combination_url) == 0 and self.film.medium_category != "events":
                    if len(self.audience) > 0 and len(self.film.combination_url) == 0:
                        print("-- adding it")
                        self.add_screening()
                        self.print_debug("-- ", "ADDING SCREENING")
        
        if self.in_screenings:
            if tag == "time":
                self.in_time = True

    def handle_endtag(self, tag):
        self.print_debug("Encountered an end tag :", tag)
        self.in_location = False
        if self.in_screenings:
            if tag == "section":
                self.in_screenings = False
                self.print_debug("--  ", "LEAVING SCREENINGS SECTION")
            if tag == "small":
                    self.in_extra_or_qa = False
            if tag == "time":
                self.in_time = False

    def handle_data(self, data):
        self.print_debug("Encountered some data  :", data)
        if self.in_location:
            location = data.strip()
            print("--  LOCATION:   {}   CATEGORY: {}".format(location, self.film.medium_category))
            self.print_debug("LOCATION", location)
            try:
                self.screen = Globals.iffr_data.screenbylocation[location]
            except KeyError:
                abbr = location.replace(" ", "").lower()
                print("NEW LOCATION:  '{}' => {}".format(location, abbr))
                Globals.iffr_data.screenbylocation[location] =  Screen((location, abbr))
                self.screen = Globals.iffr_data.screenbylocation[location]
            self.in_location = False
            self.print_debug("-- ", "LEAVING LOCATION")
        if self.in_extra_or_qa:
            if data == "Met Q&A":
                self.qa = "QA"
                self.print_debug("-- ", "FOUND QA")
            else:
                self.extra = data
                self.print_debug("-- FOUND EXTRA:", self.extra)
        if self.in_time:
            self.times = data.strip()

    def handle_comment(self, data):
        self.print_debug("Comment  :", data)

    #def handle_entityref(self, name):
    #    c = chr(name2codepoint[name])
    #    self.print_debug("Named ent:", c)

    #def handle_charref(self, name):
    #    if name.startswith('x'):
    #        c = chr(int(name[1:], 16))
    #    else:
    #        c = chr(int(name))
    #    self.print_debug("Num ent  :", c)

    def handle_decl(self, data):
        self.print_debug("Decl     :", data)


# create a subclass and override the handler methods

class AzProgrammeHtmlParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.film = None
        self.filmseqnr = 0
        self.in_film_part = False
        self.in_edition_part = False
        self.datablock_count = 0
        self.debug_text = ""
        self.url = ""
        self.matching_attr_value = ""
        self.errors = []

    def print_debug(self, str1, str2):
        if self.in_film_part:
            self.debug_text += 'AZ ' + str(str1) + ' ' + str(str2) + '\n'

    def write_debug(self):
        if len(self.debug_text) > 0:
            with open(debugfile, 'w') as f:
                f.write(self.debug_text)

    def match_attr(self, curr_tag, test_tag, curr_attr, test_attr):
        self.matching_attr_value = ""
        if self.in_film_part:
            if curr_tag == test_tag:
                if attr_str(curr_attr, 0) == test_attr:
                    self.matching_attr_value = attr_str(curr_attr, 1)
                    return True
        return False

    def add_error(self, error):
        self.errors.append(error)
    
    def print_errors(self):
        if len(self.errors) > 0:
            print("\n\nFILM ERRORS:")
            print("\n".join(self.errors))

    def handle_starttag(self, tag, attrs):
        self.print_debug("Encountered a start tag:", tag)
        for attr in attrs:
            self.print_debug("     attr:              ", attr)
            if attr_str(attr, 1).startswith("block-type-film"):
                self.in_film_part = True
            if self.match_attr(tag, "img", attr, "alt"):
                title = self.matching_attr_value
                self.film = self.create_film(title, self.url)
                if self.film is not None:
                    if self.populate_film_fields():
                        Globals.iffr_data.films.append(self.film)
            if self.match_attr(tag, "a", attr, "href"):
                self.url = "https://iffr.com{}".format(self.matching_attr_value)
            if attr_str(attr, 1).startswith("edition-year-label"):
                self.in_edition_part = True

    def handle_endtag(self, tag):
        self.print_debug("Encountered an end tag :", tag)
        if tag == "li":
            self.in_film_part = False
        if self.in_edition_part and tag == 'small':
            if self.film is not None:
                self.film.duration = '0′'
            self.in_edition_part = False
            self.datablock_count = 0

    def handle_data(self, data):
        self.print_debug("Encountered some data  :", data)
        if self.in_edition_part:
            self.datablock_count += 1
            if self.datablock_count == 3:
                if self.film is not None:
                    self.film.duration = data
                self.in_edition_part = False
                self.datablock_count = 0

    def create_film(self, title, url):
        filmid = Globals.iffr_data.new_film_id(url)
        if not filmid in [f.filmid for f in Globals.iffr_data.films]:
            self.filmseqnr += 1
            return Film(self.filmseqnr, filmid, title, url)
        else:
            self.add_error("Film #{} ({}) already in list".format(filmid, url))
            return None

    def populate_film_fields(self):
        title = self.film.title
        film_html_file = film_file_pattern.format(self.film.filmid)
        if not os.path.isfile(film_html_file):
            print("---------------------- START READING FILM URL ---")
            print("--  TITLE: {}".format(title))
            print("--  URL:   {}".format(self.url))
            url_reader = UrlReader()
            html = url_reader.read_url(self.url)
            if len(html)> 0:
                with open(film_html_file, 'w') as f:
                    f.write(html)
                print("--  Done writing URL to {}.".format(film_html_file))
            else:
                filmid = self.film.filmid
                print("--  ERROR: Failed at film #{} '{}'.\n\n\n".format(filmid, title))
                #sys.exit(0)
                self.add_error("{2} could not be read (#{0} '{1}')".format(filmid, title, self.url))
                return False
        if os.path.isfile(film_html_file):
            self.print_debug("--  Analysing film page of title:", title)
            film_html_parser = FilmPageParser(self.film)
            film_html_reader = HtmlReader()
            film_html_reader.feed_film_page(film_html_file, film_html_parser)
            self.debug_text += film_html_parser.debug_text
            return True
        return False


class HtmlReader:

    def feed_film_page(self, html_input_file, parser):
        with open(html_input_file, 'r') as f:
            text = '\n' + '\n'.join([line for line in f])
        try:
            parser.feed(text)
        except UnicodeDecodeError as e:
            print("DECODE ERROR: {}".format(e))
            if hasattr(e, 'encoding'):
                print("encoding: {}".format(e.encoding))
            if hasattr(e, 'reason'):
                print("reason: {}".format(e.reason))
            if hasattr(e, 'object'):
                print("object: {}".format(e.object))
            print("messed up by '{}'".format(e.object[e.start:e.end]))

    def feed_az_pages(self, page_count, parser):
        text = ""

        for page_number in range(0, page_count):
            html_input_file = az_file_pattern.format(page_number)
            az_url_root = "https://iffr.com/nl/programma/{}/".format(year)
            az_url_leave = "a-z"
            if not os.path.isfile(html_input_file):
                if page_number > 0:
                    az_url_leave = "a-z?page={}".format(page_number)
                url = az_url_root + az_url_leave
                print("--  AZ PAGE: {}".format(page_number))
                print("--  URL:     {}".format(url))
                print("---------------------- START READING AZ URL ---")
                url_reader = UrlReader()
                html = url_reader.read_url(url)
                if len(html)> 0:
                    with open(html_input_file, 'w') as f:
                        f.write(html)
                    print("--  Done writing URL to {}.".format(html_input_file))
                else:
                    print("--  ERROR: Failed at page #{}.\n".format(page_number))
                    sys.exit(0)
            if os.path.isfile(html_input_file):            
                with open(html_input_file, 'r') as f:
                    text = text + '\n' + '\n'.join([line for line in f])
        parser.feed(text)


main()
