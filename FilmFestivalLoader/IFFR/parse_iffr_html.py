#!/Users/maarten/opt/anaconda3/bin/python3

import os
import sys
from html.parser import HTMLParser
import urllib.request
import urllib.error
import datetime

shared_dir = os.path.expanduser("~/Projects/FilmFestivalPlanner/FilmFestivalLoader/Shared")
sys.path.insert(0, shared_dir)
import planner_interface as planner
import application_tools as app_tools
import web_tools

# Parameters.
year = 2021
data_year = 2020
city = "Rotterdam"
az_page_count = 24
include_events = True

# Directories:
project_dir = os.path.expanduser("~/Documents/Film/IFFR/IFFR{}".format(year))
webdata_dir = os.path.join(project_dir, "_website_data")
plandata_dir = os.path.join(project_dir, "_planner_data")

# Filename formats.
az_file_format = os.path.join(webdata_dir, "azpage_{:02d}.html")
film_file_format = os.path.join(webdata_dir, "filmpage_{:03d}.html")

# Files.
films_file = os.path.join(plandata_dir, "films.csv")
screens_file = os.path.join(plandata_dir, "screens.csv")
screenings_file = os.path.join(plandata_dir, "screenings.csv")
debug_file = os.path.join(plandata_dir, "debug.txt")

# URL information.
iffr_hostname = "https://iffr.com"
az_url_format = iffr_hostname + "/nl/programma/" + str(data_year) + "/a-z{}"


def main():
    # Initialize globals.
    Globals.error_collector = app_tools.ErrorCollector()
    Globals.debug_recorder = app_tools.DebugRecorder(debug_file)
    
    # initialize a festival data object.
    iffr_data = IffrData(plandata_dir)
    
    comment("Parsing AZ pages.")
    films_loader = FilmsLoader(az_page_count)
    films_loader.get_films(iffr_data)
    
    comment("Parsing film pages.")
    film_detals_loader = FilmDetailsLoader()
    film_detals_loader.get_film_details(iffr_data)
    
    if(Globals.error_collector.error_count() > 0):
        comment("Encountered some errors:")
        print(Globals.error_collector)
        
    comment("Done laoding IFFR data.")
    iffr_data.write_films()
    iffr_data.write_filminfo()
    iffr_data.write_screens()
    iffr_data.write_screenings()
    Globals.debug_recorder.write_debug()

def comment(text):
    print(f"\n{datetime.datetime.now()}  - {text}")


class Globals:
#    iffr_data = None
    error_collector = None
    debug_recorder = None


#def old_main():
#    writefilmlist = False
#    writeotherlists = True
#    
#    try:
#        # Instantiate the parser.
#        Globals.iffr_data = IffrData()
#        az_parser = AzProgrammeHtmlParser()
#        print("PARSER INITIATED\n")
#        
#        # Get the HTML and feed it to the parser.
#        az_html_reader = HtmlReader()
#        az_html_reader.feed_az_pages(az_page_count, az_parser)
#        
#    except KeyboardInterrupt:
#        print("Interrupted from keyboard... exiting")
#        writeotherlists = False
#    except SystemExit:
#        print("Quitting now.")
#    else:
#        writefilmlist = True
#
#    az_parser.write_debug()
#    az_parser.print_errors()
#    print("\n\nDONE FEEDING\n")
#
#    if writefilmlist or writeotherlists:
#        print("\n\nWRITING LISTS")
#    
#    if writeotherlists:
#        Globals.iffr_data.write_screens()
#        Globals.iffr_data.write_screenings()
#    else:
#        print("Screens and screenings NOT WRITTEN")
#    
#    if writefilmlist:
#        Globals.iffr_data.write_films()
#    else:
#        print("Films NOT WRITTEN")
#    
#    print("\nDONE")


class FilmsLoader:

    def __init__(self, az_page_count):
        self.page_count = az_page_count

    def get_films(self, iffr_data):
        for page_number in range(self.page_count):
            az_html = None
            az_file = az_file_format.format(page_number)
            if os.path.isfile(az_file):
                charset = web_tools.get_charset(az_file, 2600)
                with open(az_file, 'r', encoding=charset) as f:
                    az_html = f.read()
            else:
                az_url_leave = ""
                if page_number > 0:
                    az_url_leave = f"?page={page_number}"
                az_page = az_url_format.format(az_url_leave)
#                az_page = az_url_format.format(page_number)
                print(f"Downloading {az_page}.")
                url_reader = web_tools.UrlReader(Globals.error_collector)
                az_html = url_reader.load_url(az_page, az_file)
            if az_html is not None:
                az_page_parser = AzPageParser(iffr_data)
                az_page_parser.feed(az_html)


class FilmDetailsLoader:

    def __init__(self):
        pass

    def get_film_details(self, iffr_data):
        for film in iffr_data.films:
            if not film.filmid in [1, 18, 438, 175, 572, 124, 688, 692]:
#            if film.filmid > 8:
                continue
            html_data = None
            film_file = film_file_format.format(film.filmid)
            if os.path.isfile(film_file):
                charset = web_tools.get_charset(film_file, 2600)
                with open(film_file, 'r', encoding=charset) as f:
                    html_data = f.read()
            else:
                print(f"Downloading site of {film.title}: {film.url}")
                url_reader = web_tools.UrlReader(Globals.error_collector)
                html_data = url_reader.load_url(film.url, film_file)
            if html_data is not None:
                print(f"Analysing html file {film.filmid} of {film.title}")
                FilmPageParser(iffr_data, film).feed(html_data)


class HtmlPageParser(web_tools.HtmlPageParser):
    
    def __init__(self, iffr_data, debug_prefix):
        web_tools.HtmlPageParser.__init__(self, Globals.debug_recorder, debug_prefix)
        self.iffr_data = iffr_data
        self.debugging = False


class AzPageParser(HtmlPageParser):

    def __init__(self, iffr_data):
        HtmlPageParser.__init__(self, iffr_data, 'AZ')
        self.in_film_part = False
        self.in_edition_part = False
        self.datablock_count = 0
        self.matching_attr_value = ""
        self.debugging = False
        self.init_film_data()

    def init_film_data(self):
        self.film = None
        self.title = None
        self.url = None
        self.duration = None
#        self.description = None
#        self.in_link = False
#        self.in_title = False
#        self.await_duration = False
#        self.in_duration = False
#        self.in_description = False

    def add_film(self):
        self.film = self.iffr_data.create_film(self.title, self.url)
        if self.film is None:
            Globals.error_collector.add(f'Could\'t create film from {self.title}', self.url)
        else:
            self.film.medium_category = self.url.split("/")[5]
            print(f"Adding FILM: {self.title}")
            self.iffr_data.films.append(self.film)

    def match_attr(self, curr_tag, test_tag, curr_attr, test_attr):
        self.matching_attr_value = ""
        if self.in_film_part:
            if curr_tag == test_tag:
                if attr_str(curr_attr, 0) == test_attr:
                    self.matching_attr_value = attr_str(curr_attr, 1)
                    return True
        return False

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
        for attr in attrs:
            if attr_str(attr, 1).startswith("block-type-film"):
                self.in_film_part = True
            if self.match_attr(tag, "img", attr, "alt"):
                self.title = self.matching_attr_value
                self.add_film()

            if self.match_attr(tag, "a", attr, "href"):
                self.url = f"{iffr_hostname}{self.matching_attr_value}"
            if attr_str(attr, 1).startswith("edition-year-label"):
                self.in_edition_part = True

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)
        if tag == "li":
            self.in_film_part = False
        if self.in_edition_part and tag == 'small':
            if self.film is not None:
                self.film.duration = datetime.timedelta(minutes=0)
            self.in_edition_part = False
            self.datablock_count = 0

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
        if self.in_edition_part:
            self.datablock_count += 1
            if self.datablock_count == 3:
                if self.film is not None:
                    minutes = int(data.rstrip('′'))
                    self.film.duration = datetime.timedelta(minutes=minutes)
                self.in_edition_part = False
                self.datablock_count = 0


class FilmPageParser(HtmlPageParser):

    def __init__(self, iffr_data, film):
        HtmlPageParser.__init__(self, iffr_data, "F")
        self.film = film
        self.description = None
        self.article = None
        self.debugging = True
        self.in_article = False
        self.await_article = False
        self.in_description = False
        self.await_content = False
        self.await_paragraph = False
        self.print_debug(f"{40 * '-'} ", f"Analysing FILM {film}")

        self.init_screening_data()
        self.before_screenings = True
        self.in_screenings = False
        self.in_location = False
        self.in_time = False
        self.in_extra_or_qa = False
        self.matching_attr_value = ""
#        self.debug_text = ""

    def init_screening_data(self):
        self.screen = None
        self.start_date = None
#        self.times = None
        self.start_time = None
        self.end_time = None
        self.audience = None
        self.qa = ""
        self.extra = ""

    def add_screening(self):
#        print("--  {}".format(self.film.title))
#        print("--  start date: {}".format(self.start_date))
#        print("--  screen:     {}".format(self.screen))
#        print("--  times:      {}".format(self.times))
#        print("--  audience:   {}".format(self.audience))
#        print("--  category:   {}".format(self.film.medium_category))
#        print("--  q and a     {}".format(self.qa))
#        print("--  extra:      {}".format(self.extra))

        start_datetime = datetime.datetime.combine(self.start_date, self.start_time)        
        end_date = self.start_date if self.end_time > self.start_time else self.start_date + datetime.timedelta(days=1) 
        end_datetime = datetime.datetime.combine(end_date, self.end_time)
        self.print_debug("--- ", f"START TIME = {start_datetime}, END TIME = {end_datetime}")
        
        print()
        print(f"---SCREENING OF {self.film.title}")
        print(f"--  screen:     {self.screen}")
        print(f"--  start time: {start_datetime}")
        print(f"--  end time:   {end_datetime}")
        print(f"--  duration:   film: {self.film.duration_str()}  screening: {end_datetime - start_datetime}")
        print(f"--  audience:   {self.audience}")
        print(f"--  category:   {self.film.medium_category}")
        print(f"--  q and a:    {self.qa}")
        print(f"--  extra:      {self.extra}")
        
        screening = planner.Screening(self.film, self.screen, start_datetime, end_datetime, self.qa, self.extra, self.audience)
        
        self.iffr_data.screenings.append(screening)
        print("---SCREENING ADDED")
        self.in_extra_or_qa = False
        self.init_screening_data()

    def ok_to_add_screening(self):
        if self.audience is None:
            return False
        if len(self.film.combination_url) > 0:
            return False
        if self.extra == "Voorfilm: " + self.film.title:
            return False
        if not include_events and self.film.medium_category == "events":
            return False
        return True

    def add_article(self, description, article):
        description = description if description is not None else ''
        article = article if article is not None else ''
        filminfo = planner.FilmInfo(self.film.filmid, description, article)
        self.iffr_data.filminfos.append(filminfo)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        # Get data for fim info.
        if tag == 'meta':
            for attr in attrs:
                if attr == ('name', 'description'):
                    self.await_content = True
                elif self.await_content and attr[0] == 'content':
                    self.await_content = False
                    self.in_description = False
                    self.description = attr[1]
                    self.print_debug(f"Found DESCRIPTION of {self.film.title}:", self.description)
        elif tag == 'article':
            self.await_article = True
        elif self.await_paragraph and tag == 'p':
            self.await_paragraph = False
            self.article += '\n\n'
        elif self.await_article and tag == 'div':
            self.await_article = False
            self.in_article = True
            self.article = ''

        # Get data for screenings.
        for attr in attrs:
            self.print_debug("Handling attr:      ", attr)
            if tag == "section" and attr == ("class", "film-screenings-wrapper"):
                self.in_screenings = True
                self.before_screenings = False
                self.print_debug("--  ", "ENTERING SCREENINGS SECTION")
            if self.before_screenings:
                collect_attr = "/nl/{}/verzamelprogrammas/".format(data_year)
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
                    start_datetime = datetime.datetime.fromisoformat(attr[1])
                    self.start_date = start_datetime.date()
                    if self.ok_to_add_screening():
                        self.add_screening()
                        self.print_debug("-- ", "ADDING SCREENING")
        
        if self.in_screenings:
            if tag == "time":
                self.in_time = True

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        # Get data for fim info.
        if tag == 'title':
            self.in_description = True
        elif self.in_article and tag == 'p':
            self.await_paragraph = True
        elif self.in_article and tag == 'div':
            self.in_article = False
            self.print_debug(f"Found ARTICLE of {self.film.title}:", self.article)
            self.add_article(self.description, self.article)

        # Get data for screenings.
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
        HtmlPageParser.handle_data(self, data)

        # Get data for fim info.
        if self.in_article and len(data.strip()) > 0:
            self.article += data.replace('\n', ' ')

        # Get data for screenings.
        if self.in_location:
            location = data.strip()
            print(f"--  LOCATION:   {location}   CATEGORY: {self.film.medium_category}")
            self.print_debug("LOCATION", location)
            self.screen = self.iffr_data.get_screen(city, location)
#            try:
#                self.screen = Globals.iffr_data.screenbylocation[location]
#            except KeyError:
#                abbr = location.replace(" ", "").lower()
#                print("NEW LOCATION:  '{}' => {}".format(location, abbr))
#                Globals.iffr_data.screenbylocation[location] =  Screen((location, abbr))
#                self.screen = Globals.iffr_data.screenbylocation[location]
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
#            self.times = data.strip()
            times = data.strip()
            self.start_time = datetime.time.fromisoformat(times.split()[0])
            self.end_time = datetime.time.fromisoformat(times.split()[2])

def attr_str(attr, index):
    return (str)(attr[index])


#class Screen():
#
#    def __init__(self, name_abbr_tuple):
#        self.name = name_abbr_tuple[0]
#        self.abbr = name_abbr_tuple[1]
#
#    def __str__(self):
#        return self.abbr
#
#    def __repr__(self):
#        text = ";".join([self.name, self.abbr])
#        return "{}\n".format(text)
#
#    def _key(self):
#        return self.name
#
#
#class Screening:
#
#    def __init__(self, film, screen, startDate, startTime, endTime, audience, qa, extra):
#        self.status = "ONWAAR"
#        self.iAttend = "ONWAAR"
#        self.attendingFriends = "ONWAAR,ONWAAR,ONWAAR"
#        self.startDate = startDate
#        self.screen = screen
#        self.startTime = startTime
#        self.endTime = endTime
#        self.extra = extra
#        self.filmsInScreening = 1 if len(extra) == 0 else 2
#        self.qAndA = qa
#        self.ticketsBought = "ONWAAR"
#        self.soldOut = "ONWAAR"
#        self.filmid = film.filmid
#        self.audience = audience
#
#    def screening_repr_csv_head(self):
#        text = ";".join([
#            "filmid",
#            "date",
#            "screen",
#            "starttime",
#            "endtime",
#            "filmsinscreening",
#            "extra",
#            "qanda"
#        ])
#        return "{}\n".format(text)
#
#    def __repr__(self):
#        text = ";".join([
#            (str)(self.filmid),
#            self.startDate,
#            self.screen.abbr,
#            self.startTime,
#            self.endTime,
#            (str)(self.filmsInScreening),
#            self.extra,
#            self.qAndA
#        ])
#        return "{}\n".format(text)


class IffrData(planner.FestivalData):

    def _init__(self, plandata_dir):
        planner.FestivalData.__init__(self, plandata_dir)

    def _filmkey(self, film, url):
        return url


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


class OLdFilmPageParser(HTMLParser):

    def __init__(self, film):
        HTMLParser.__init__(self)
        self.film = film
        self.init_screening_data()
        self.before_screenings = True
        self.in_screenings = False
        self.in_location = False
        self.in_time = False
        self.in_extra_or_qa = False
        self.matching_attr_value = ""
        self.debug_text = ""

    def init_screening_data(self):
        self.screen = None
        self.start_date = None
        self.times = None
        self.audience = None
        self.qa = ""
        self.extra = ""

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
        screening = planner.Screening(self.film, self.screen, startDate, startTime, endTime, self.audience, self.qa, self.extra)
        Globals.iffr_data.screenings.append(screening)
        print("---SCREENING ADDED")
        self.in_extra_or_qa = False
        self.init_screening_data()

    def print_debug(self, str1, str2):
        if self.film.filmid in [100]:
            self.debug_text += 'F ' + str(str1) + ' ' + str(str2) + '\n'

    def match_attr(self, curr_tag, test_tag, curr_attr, test_attr):
        self.matching_attr_value = ""
        if curr_tag == test_tag:
            if attr_str(curr_attr, 0) == test_attr:
                self.matching_attr_value = attr_str(curr_attr, 1)
                return True
        return False

    def ok_to_add_screening(self):
        if self.audience is None:
            return False
        if len(self.film.combination_url) > 0:
            return False
        if self.extra == "Voorfilm: " + self.film.title:
            return False
        if not include_events and self.film.medium_category == "events":
            return False
        return True

    def handle_starttag(self, tag, attrs):
        self.print_debug("Encountered a start tag:", tag)
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
                    if self.ok_to_add_screening():
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

#    def handle_data(self, data):
#        self.print_debug("Encountered some data  :", data)
#        if self.in_location:
#            location = data.strip()
#            print("--  LOCATION:   {}   CATEGORY: {}".format(location, self.film.medium_category))
#            self.print_debug("LOCATION", location)
#            try:
#                self.screen = Globals.iffr_data.screenbylocation[location]
#            except KeyError:
#                abbr = location.replace(" ", "").lower()
#                print("NEW LOCATION:  '{}' => {}".format(location, abbr))
#                Globals.iffr_data.screenbylocation[location] =  Screen((location, abbr))
#                self.screen = Globals.iffr_data.screenbylocation[location]
#            self.in_location = False
#            self.print_debug("-- ", "LEAVING LOCATION")
#        if self.in_extra_or_qa:
#            if data == "Met Q&A":
#                self.qa = "QA"
#                self.print_debug("-- ", "FOUND QA")
#            else:
#                self.extra = data
#                self.print_debug("-- FOUND EXTRA:", self.extra)
#        if self.in_time:
#            self.times = data.strip()

    def handle_comment(self, data):
        self.print_debug("Comment  :", data)

    def handle_decl(self, data):
        self.print_debug("Decl     :", data)


# create a subclass and override the handler methods

#class AzProgrammeHtmlParser(HTMLParser):
#
#    def __init__(self):
#        HTMLParser.__init__(self)
#        self.film = None
#        self.filmseqnr = 0
#        self.in_film_part = False
#        self.in_edition_part = False
#        self.datablock_count = 0
#        self.debug_text = ""
#        self.url = ""
#        self.matching_attr_value = ""
#        self.errors = []
#
#    def print_debug(self, str1, str2):
#        if self.in_film_part:
#            self.debug_text += 'AZ ' + str(str1) + ' ' + str(str2) + '\n'
#
#    def write_debug(self):
#        if len(self.debug_text) > 0:
#            with open(debug_file, 'w') as f:
#                f.write(self.debug_text)
#
#    def match_attr(self, curr_tag, test_tag, curr_attr, test_attr):
#        self.matching_attr_value = ""
#        if self.in_film_part:
#            if curr_tag == test_tag:
#                if attr_str(curr_attr, 0) == test_attr:
#                    self.matching_attr_value = attr_str(curr_attr, 1)
#                    return True
#        return False
#
#    def add_error(self, error):
#        self.errors.append(error)
#    
#    def print_errors(self):
#        if len(self.errors) > 0:
#            print("\n\nFILM ERRORS:")
#            print("\n".join(self.errors))
#
#    def handle_starttag(self, tag, attrs):
#        self.print_debug("Encountered a start tag:", tag)
#        for attr in attrs:
#            self.print_debug("     attr:              ", attr)
#            if attr_str(attr, 1).startswith("block-type-film"):
#                self.in_film_part = True
#            if self.match_attr(tag, "img", attr, "alt"):
#                title = self.matching_attr_value
#                self.film = self.create_film(title, self.url)
#                if self.film is not None:
#                    if self.populate_film_fields():
#                        Globals.iffr_data.films.append(self.film)
#            if self.match_attr(tag, "a", attr, "href"):
##                self.url = "https://iffr.com{}".format(self.matching_attr_value)
#                self.url = f"{iffr_hostname}{self.matching_attr_value}"
#            if attr_str(attr, 1).startswith("edition-year-label"):
#                self.in_edition_part = True

#    def handle_endtag(self, tag):
#        self.print_debug("Encountered an end tag :", tag)
#        if tag == "li":
#            self.in_film_part = False
#        if self.in_edition_part and tag == 'small':
#            if self.film is not None:
#                self.film.duration = '0′'
#            self.in_edition_part = False
#            self.datablock_count = 0

#    def handle_data(self, data):
#        self.print_debug("Encountered some data  :", data)
#        if self.in_edition_part:
#            self.datablock_count += 1
#            if self.datablock_count == 3:
#                if self.film is not None:
#                    self.film.duration = data
#                self.in_edition_part = False
#                self.datablock_count = 0

#    def create_film(self, title, url):
#        filmid = Globals.iffr_data.new_film_id(url)
#        if not filmid in [f.filmid for f in Globals.iffr_data.films]:
#            self.filmseqnr += 1
#            return planner.Film(self.filmseqnr, filmid, title, url)
#        else:
#            self.add_error("Film #{} ({}) already in list".format(filmid, url))
#            return None
#
#    def populate_film_fields(self):
#        title = self.film.title
#        film_html_file = film_file_format.format(self.film.filmid)
#        if not os.path.isfile(film_html_file):
#            print("---------------------- START READING FILM URL ---")
#            print("--  TITLE: {}".format(title))
#            print("--  URL:   {}".format(self.url))
#            url_reader = UrlReader()
#            html = url_reader.read_url(self.url)
#            if len(html)> 0:
#                with open(film_html_file, 'w') as f:
#                    f.write(html)
#                print("--  Done writing URL to {}.".format(film_html_file))
#            else:
#                filmid = self.film.filmid
#                print("--  ERROR: Failed at film #{} '{}'.\n\n\n".format(filmid, title))
#                self.add_error("{2} could not be read (#{0} '{1}')".format(filmid, title, self.url))
#                return False
#        if os.path.isfile(film_html_file):
#            self.print_debug("--  Analysing film page of title:", title)
#            film_html_parser = FilmPageParser(self.film)
#            film_html_reader = HtmlReader()
#            film_html_reader.feed_film_page(film_html_file, film_html_parser)
#            self.debug_text += film_html_parser.debug_text
#            return True
#        return False


#class HtmlReader:
#
#    def feed_film_page(self, html_input_file, parser):
#        with open(html_input_file, 'r') as f:
#            text = '\n' + '\n'.join([line for line in f])
#        try:
#            parser.feed(text)
#        except UnicodeDecodeError as e:
#            print("DECODE ERROR: {}".format(e))
#            if hasattr(e, 'encoding'):
#                print("encoding: {}".format(e.encoding))
#            if hasattr(e, 'reason'):
#                print("reason: {}".format(e.reason))
#            if hasattr(e, 'object'):
#                print("object: {}".format(e.object))
#            print("messed up by '{}'".format(e.object[e.start:e.end]))

#    def feed_az_pages(self, page_count, parser):
#        text = ""
#
#        for page_number in range(0, page_count):
#            html_input_file = az_file_format.format(page_number)
#            az_url_leave = ""
#            if not os.path.isfile(html_input_file):
#                if page_number > 0:
#                    az_url_leave = f"?page={page_number}"
#                url = az_url_format.format(az_url_leave)
#                print("--  AZ PAGE: {}".format(page_number))
#                print("--  URL:     {}".format(url))
#                print("---------------------- START READING AZ URL ---")
#                url_reader = UrlReader()
#                html = url_reader.read_url(url)
#                if len(html)> 0:
#                    with open(html_input_file, 'w') as f:
#                        f.write(html)
#                    print("--  Done writing URL to {}.".format(html_input_file))
#                else:
#                    print("--  ERROR: Failed at page #{}.\n".format(page_number))
#                    sys.exit(0)
#            if os.path.isfile(html_input_file):            
#                with open(html_input_file, 'r') as f:
#                    text = text + '\n' + '\n'.join([line for line in f])
#        parser.feed(text)


if __name__ == "__main__":
    main()
