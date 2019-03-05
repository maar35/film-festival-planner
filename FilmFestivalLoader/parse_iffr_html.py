#!/usr/bin/python

import argparse
import os
from operator import attrgetter
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint
from urllib2 import Request, urlopen, URLError

version_number = "0.1"

# Globals.

project_dir = os.path.expanduser("~/Documents/Film/IFFR/IFFR2019")
html_input_dir = os.path.join(project_dir, "_website_data")
data_dir = os.path.join(project_dir, "_planner_data")
screenfile = os.path.join(data_dir, "screens.csv")
filmsfile = os.path.join(data_dir, "films.csv")
ucodefile = os.path.join(data_dir, "unicodemap.txt")
filmurlfile = os.path.join(data_dir, "filmurls.txt")
screeningsfile = os.path.join(data_dir, "screenings.csv")

# Glyphs.

f = open(ucodefile)
umapkeys = f.readline().rstrip("\n").split(";")
umapvalues = f.readline().rstrip("\n").split(";")
f.close()

### my parser ###

# create a subclass and override the handler methods

class MyHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        print "Start tag:", tag
        for attr in attrs:
            print "     attr:", attr

    def handle_endtag(self, tag):
        print "End tag  :", tag

    def handle_data(self, data):
        print "Data     :", data

    def handle_comment(self, data):
        print "Comment  :", data

    def handle_entityref(self, name):
        c = unichr(name2codepoint[name])
        print "Named ent:", c

    def handle_charref(self, name):
        if name.startswith('x'):
            c = unichr(int(name[1:], 16))
        else:
            c = unichr(int(name))
        print "Num ent  :", c

    def handle_decl(self, data):
        print "Decl     :", data


# instantiate the parser and fed it some HTML
my_parser = MyHTMLParser()
#my_parser.feed('<a href="/nl/2019/films/%C3%A0-travers-la-lune">')
#my_parser.feed(text)

### iffr parser ###

# Globals

def attr_str(attr, index):
    return (str)(attr[index])


class Screen():

    def __init__(self, (name, abbr)):
        self.name = name
        self.abbr = abbr

    def __repr__(self):
        return self.abbr

    def _key(self):
        return self.name

    def screen_repr_csv(self):
        text = ";".join([self.name, self.abbr])
        return "{}\n".format(text)

class Film:

    def __init__(self, admin, title, url):
        self.filmId = admin.new_film_id()
        self.sortedTitle = title
        self.sortstring = self.lower(self.sortedTitle)
        self.title = title
        self.titleLanguage = ""
        self.section = ""
        self.rating = "0"
        self.filmInfoStatus = "Absent"
        #info = FilmInfo(self.filmId, url, "no-description")
        self.url = url
        self.medium_catagory = url.split("/")[5]
        self.combination_url = ""

    def __str__(self):
        return "; ".join([self.title, self.medium_catagory, self.combination_url])

    def film_repr_csv_head(self):
        text = ";".join([
            "filmid",
            "sort",
            "title",
            "titlelanguage",
            "section",
            "rating",
            "filminfostatus"
        ])
        return "{}\n".format(text)

    def film_repr_csv(self):
        text = ";".join([
            (str)(self.filmId),
            self.sortstring.replace(";", ".,"),
            self.title.replace(";", ".,"),
            self.titleLanguage,
            self.section,
            self.rating,
            self.filmInfoStatus
        ])
        return "{}\n".format(text)

    def filmurl_repr_txt(self):
        text = ";".join([
            (str)(self.filmId),
            self.url
        ])
        return "{}\n".format(text)

    def toascii(self, s):
        for (u, a) in zip(umapkeys, umapvalues):
            s = s.replace(u, a)
        return s

    def lower(self, s):
        return self.toascii(s).lower()


class FilmInfo:

    def __init__(self, id, url, desc):
        self.filmId = id
        self.url = url
        self.description = desc

    def filminfo_repr_csv(self):
        text = ";".join([
            (str)(self.filmId),
            self.url,
            self.description
        ])
        return "{}\n".format(text)


class Screening:

    def __init__(self, film, screen, startDate, startTime, endTime, audience):
        self.status = "ONWAAR"
        self.iAttend = "ONWAAR"
        self.attendingFriends = "ONWAAR,ONWAAR,ONWAAR"
        self.startDate = startDate
        self.screen = screen
        self.startTime = startTime
        self.endTime = endTime
        self.screeningTitle = film.title
        self.filmsInScreening = 1
        self.extra = ""
        self.qAndA = ""
        self.ticketsBought = "ONWAAR"
        self.soldOut = "ONWAAR"
        self.startDate = startDate
        self.filmId = film.filmId
        self.audience = audience

    def screening_repr_csv_head(self):
        text = ";".join([
            "blocked",
            "maarten",
            "Adrienne,Manfred,Piggel",
            "startdm",
            "theatre",
            "starttime",
            "endtime",
            "title",
            "filmsinshow",
            "extra",
            "qanda",
            "ticketsbought",
            "soldout",
            "date",
            "filmid"
        ])
        return "{}\n".format(text)

    def screening_repr_csv(self):
        text = ";".join([
            self.status,
            self.iAttend,
            self.attendingFriends,
            self.startDate,
            self.screen.abbr,
            self.startTime,
            self.endTime,
            self.screeningTitle,
            (str)(self.filmsInScreening),
            self.extra,
            self.qAndA,
            self.ticketsBought,
            self.soldOut,
            self.startDate,
            (str)(self.filmId)
        ])
        return "{}\n".format(text)


class IffrData:

    curr_film_id = 0

    def __init__(self):
        self.films = []
        self.filmUrls = []
        self.filmInfos = []
        self.screenings = []
        self.read_screens()

    def new_film_id(self):
        self.curr_film_id = self.curr_film_id + 1
        return self.curr_film_id

    def read_url(self, url):
        pass

    def splitrec(self, line, sep):
        end = sep + "\r\n"
        return line.rstrip(end).split(sep)

    def read_screens(self):
        f = open(screenfile, "r")
        screens = [Screen(self.splitrec(line, ";")) for line in f]
        f.close()
        self.screens = dict([(screen._key(), screen) for screen in screens])

    def write_screens(self):
        f = open(screenfile, "w")
        for screen in self.screens.values():
            f.write(screen.screen_repr_csv())
        f.close()
        print "Done writing {} records to {}.".format(len(self.screens), screenfile)

    def write_films(self):
        f = open(filmsfile, "w")
        f.write(self.films[0].film_repr_csv_head())
        for film in self.films:
            f.write(film.film_repr_csv())
        f.close()
        print "Done writing {} records to {}.".format(len(self.films), filmsfile)

    def write_filmurls(self):
        f = open(filmurlfile, "w")
        for film in self.films:
            f.write(film.filmurl_repr_txt())
        f.close()
        print "Done writing {} records to {}.".format(len(self.films), filmurlfile)

    def write_screenings(self):
        f = open(screeningsfile, "w")
        f.write(self.screenings[0].screening_repr_csv_head())
        for screening in [s for s in self.screenings if s.audience == "publiek"]:
            f.write(screening.screening_repr_csv())
        f.close()
        print "Done writing {} records to {}.".format(len(self.screenings), screeningsfile)


class UrlReader:

    def read_url(self, url, film):
        req = Request(url)
        try:
            response = urlopen(req)
        except URLError as e:
            if hasattr(e, 'reason'):
                print 'We failed to reach a server.'
                print 'Reason: ', e.reason
            elif hasattr(e, 'code'):
                print 'The server couldn\'t fulfill the request.'
                print 'Error code: ', e.code
        else:
            html = response.read()
            #film_parser = FilmPageParser()
            #film_parser.feed(html)


class FilmPageParser(HTMLParser):

    def __init__(self, film):
        HTMLParser.__init__(self)
        self.film = film
        self.screen = ""
        self.start_date = ""
        self.times = ""
        self.audience = ""
        self.before_screenings = True
        self.in_screenings = False
        self.in_location = False
        #self.in_date = False
        self.some_times = ""
        self.matching_attr_value = ""

    def add_screening(self):
        #-print "--  {}".format(self.film.title)
        #-print "--  SCREEN:     {}".format(self.screen)
        #-print "--  STARTDATE:  {}".format(self.start_date)
        #-print "--  TIMES:      {}".format(self.times)
        #-print "--  AUDIENCE:   {}".format(self.audience)
        startDate = self.start_date.split()[0]
        startTime = self.times.split()[0]
        endTime = self.times.split()[2]
        screening = Screening(self.film, self.screen, startDate, startTime, endTime, self.audience)
        iffr_data.screenings.append(screening)
        self.screen = ""
        self.times = ""
        self.audience = ""

    def match_attr(self, curr_tag, test_tag, curr_attr, test_attr):
        self.matching_attr_value = ""
        if curr_tag == test_tag:
            if attr_str(curr_attr, 0) == test_attr:
                self.matching_attr_value = attr_str(curr_attr, 1)
                return True
        return False

    def print_dbg(self, str1, str2):
        pass
        #print str1, unicode(str2, "ascii")
        #try:
        #    print str1, str2
        #    #print str1, (str)(str2)
        #    #print str1, str2.encode("ascii", "xmlcharrefreplace")
        #except UnicodeEncodeError as e:
        #    if hasattr(e, 'object'):
        #        print "{}XXX{}".format(e.object[0:e.start], e.object[e.end:])
        #    else:
        #        print "ENCODE ERROR: {}".format(e)

    def handle_starttag(self, tag, attrs):
        #self.print_dbg("Start tag:", tag)
        #-print "Start tag:", tag
        for attr in attrs:
            #self.print_dbg("     attr:", attr)
            #-print "     attr:", attr
            if tag == "section" and attr == ("class", "film-screenings-wrapper"):
                self.in_screenings = True
                self.before_screenings = False
                #-print "--  IN SCREENINGS SECTION"
            if self.before_screenings:
                if tag == "a" and attr[0] == "href" and attr[1].startswith("/nl/2019/verzamelprogrammas/"):
                    if self.film.medium_catagory != "verzamelprogrammas":
                        self.film.combination_url = attr[1]
                        #-print "--  PART OF COMBINATION {}".format(self.film)
            if self.in_screenings:
                if tag == "span" and attr == ("class", "location"):
                    self.in_location = True
                #if tag == "span" and attr == ("class", "date"):
                #    self.in_date = True
                if tag =="a" and attr[0] == "data-audience":
                    self.audience = attr[1]
                    #-print "--  AUDIENCE:   {}".format(self.audience)
                if tag =="a" and attr[0] == "data-date":
                    self.start_date = attr[1]
                    #-print "--  STARTDATE:  {}".format(self.start_date)
                    if len(self.audience) > 0 and len(self.film.combination_url) == 0 and self.film.medium_catagory != "events":
                        self.add_screening()

    def handle_endtag(self, tag):
        #self.print_dbg("End tag  :", tag)
        #-print "End tag  :", tag
        self.in_location = False
        #self.in_date = False
        if self.in_screenings:
            if tag == "section":
                self.in_screenings = False
                #-print "--  LEAVING SCREENINGS SECTION"
            if tag == "time":
                self.times = self.some_times
                #-print "--  TIMES     : {}".format(self.times)

    def handle_data(self, data):
        #self.print_dbg("Data     :", data)
        #-print "Data     :", data
        if self.in_location:
            location = data.strip()
            #-print "--  LOCATION:   {}   CATAGORY: {}".format(location, self.film.medium_catagory)
            try:
                self.screen = iffr_data.screens[location]
            except KeyError:
                abbr = location.replace(" ", "").lower()
                #-print "NEW LOCATION:  '{}' => {}".format(location, abbr)
                iffr_data.screens[location] =  Screen((location, abbr))
        #if self.in_date:
        #    self.start_date = data.strip()
        #    print "    START DATE: {}".format(self.start_date)
        if self.in_screenings:
            self.some_times = data.strip()

    #def handle_comment(self, data):
    #    self.print_dbg("Comment  :", data)

    #def handle_entityref(self, name):
    #    c = unichr(name2codepoint[name])
    #    self.print_dbg("Named ent:", c)

    #def handle_charref(self, name):
    #    if name.startswith('x'):
    #        c = unichr(int(name[1:], 16))
    #    else:
    #        c = unichr(int(name))
    #    self.print_dbg("Num ent  :", c)

    #def handle_decl(self, data):
    #    self.print_dbg("Decl     :", data)


# create a subclass and override the handler methods

class AzProgrammeHtmlParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.in_film_part = False
        #self.in_title_tag = False
        self.url = ""
        self.matching_attr_value = ""

    def print_dbg(self, str1, str2):
        pass
        #print str1, str2

    def match_attr(self, curr_tag, test_tag, curr_attr, test_attr):
        self.matching_attr_value = ""
        if self.in_film_part:
            if curr_tag == test_tag:
                if attr_str(curr_attr, 0) == test_attr:
                    self.matching_attr_value = attr_str(curr_attr, 1)
                    return True
        return False

    def handle_starttag(self, tag, attrs):
        self.print_dbg("Encountered a start tag:", tag)
        for attr in attrs:
            self.print_dbg("     attr:              ", attr)
            self.print_dbg("        0:              ", attr[0])
            self.print_dbg("        1:              ", attr[1])
            if attr_str(attr, 1).startswith("block-type-film"):
                self.in_film_part = True
                #=print "--  FOUND ONE"
            if self.match_attr(tag, "img", attr, "alt"):
                title = self.matching_attr_value
                film = Film(iffr_data, title, self.url)
                #=print "--  TITLE: {}".format(title)
                #=print "--  URL:   {}".format(self.url)
                #-print "---------------------- START READING FILM URL {} ---".format(self.url)
                #url_reader = UrlReader()
                #url_reader.read_url(self.url, film)
                film_html_parser = FilmPageParser(film)
                film_html_reader = HtmlReader()
                film_html_reader.feed_page("filmpage_{:03d}.html".format(film.filmId), film_html_parser)
                #-print "---------------------- DONE  READING FILM URL {} ---".format(film)
                iffr_data.films.append(film)
            if self.match_attr(tag, "a", attr, "href"):
                self.url = "https://iffr.com{}".format(self.matching_attr_value)
        #if self.in_film_part and tag == "h2":
        #    self.in_title_tag = True

    def handle_endtag(self, tag):
        self.print_dbg("Encountered an end tag :", tag)
        #self.in_title_tag = False
        if tag == "li":
            self.in_film_part = False

    def handle_data(self, data):
        self.print_dbg("Encountered some data  :", data)
        #if self.in_title_tag:
        #    iffr_data.films.append(Film(iffr_data, data))
        #    print "    OLD TITLE: {}".format(data)


class HtmlReader:

    def feed_page(self, file_name, parser):
        html_input_file = os.path.join(html_input_dir, file_name)
        f = open(html_input_file, "r")
        text = "\n" + "\n".join([line for line in f])
        f.close()
        try:
            parser.feed(text)
            #parser.feed(unicode(text, "utf-8"))
        except UnicodeDecodeError as e:
            print "DECODE ERROR: {}".format(e)
            if hasattr(e, 'encoding'):
                print "encoding: {}".format(e.encoding)
            if hasattr(e, 'reason'):
                print "reason: {}".format(e.reason)
            if hasattr(e, 'object'):
                print "object: {}".format(e.object)
            print "messed up by '{}'".format(e.object[e.start:e.end])

    def feed_pages(self, file_format, page_count, parser):
        text = ""
        for page_number in range(0, page_count):
            html_input_file = os.path.join(html_input_dir, file_format.format(page_number))
            f = open(html_input_file, "r")
            text = text + "\n" + "\n".join([line for line in f])
            f.close()
        parser.feed(text)


# instantiate the parser.

iffr_data = IffrData()
iffr_parser = AzProgrammeHtmlParser()

# Get the HTML and feed it to the parser.

az_html_reader = HtmlReader()
az_html_reader.feed_pages("page{}.html", 22, iffr_parser)

print "\n\nDONE FEEDING\n"

#for film in iffr_data.films:
#    print film

print "\n\nWRITING NOW"
iffr_data.write_screens()
iffr_data.write_films()
iffr_data.write_filmurls()
iffr_data.write_screenings()

print "\nDONE"
