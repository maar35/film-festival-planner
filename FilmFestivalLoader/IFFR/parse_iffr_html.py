#!/Users/maarten/opt/anaconda3/bin/python3

import os
import sys
from html.parser import HTMLParser
import urllib.request
import urllib.error
import re
import datetime

shared_dir = os.path.expanduser("~/Projects/FilmFestivalPlanner/FilmFestivalLoader/Shared")
sys.path.insert(0, shared_dir)
import planner_interface as planner
import application_tools as app_tools
import web_tools

# Parameters.
festival = 'IFFR'
year = 2021
city = "Rotterdam"
az_page_count = 1
include_events = True

# Directories:
documents_dir = os.path.expanduser("~/Documents/Film/{0}/{0}{1}".format(festival, year))
webdata_dir = os.path.join(documents_dir, "_website_data")
plandata_dir = os.path.join(documents_dir, "_planner_data")

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
az_url_format = "/nl/programma/" + str(year) + "/a-z{}"


def main():
    # Initialize globals.
    Globals.error_collector = app_tools.ErrorCollector()
    Globals.debug_recorder = app_tools.DebugRecorder(debug_file)

    # Initialize a festival data object.
    iffr_data = IffrData(plandata_dir)

    # Try parsing the web sites.
    write_film_list = False
    write_other_lists = True
    try:
        comment("Parsing AZ pages.")
        films_loader = FilmsLoader(az_page_count)
        films_loader.get_films(iffr_data)

        comment("Parsing film pages.")
        film_detals_loader = FilmDetailsLoader()
        film_detals_loader.get_film_details(iffr_data)
    except KeyboardInterrupt:
        comment("Interrupted from keyboard... exiting")
        write_other_lists = False
    except Exception as e:
        Globals.debug_recorder.write_debug()
        comment('Debug info printed.')
        raise e
    else:
        write_film_list = True

    # Display error when found.
    if Globals.error_collector.error_count() > 0:
        comment("Encountered some errors:")
        print(Globals.error_collector)

    # Write parsed information.
    comment("Done laoding IFFR data.")
    write_lists(iffr_data, write_film_list, write_other_lists)
    Globals.debug_recorder.write_debug()


def comment(text):
    print(f"\n{datetime.datetime.now()}  - {text}")


def write_lists(iffr_data, write_film_list, write_other_lists):

    if write_film_list or write_other_lists:
        print("\n\nWRITING LISTS")

    if write_film_list:
        iffr_data.sort_films()
        iffr_data.write_films()
    else:
        print("Films NOT WRITTEN")

    if write_other_lists:
        iffr_data.write_filminfo()
        iffr_data.write_screens()
        iffr_data.write_screenings()
    else:
        print("Screens and screenings NOT WRITTEN")


class Globals:
    error_collector = None
    debug_recorder = None


class FilmsLoader:

    def __init__(self, az_page_count):
        self.page_count = az_page_count

    def get_films(self, iffr_data):
        for page_number in range(1, self.page_count + 1):
            az_html = None
            az_file = az_file_format.format(page_number)
            if os.path.isfile(az_file):
                charset = web_tools.get_charset(az_file)
                print(f'Reading {az_file} with encoding {charset}.')
                with open(az_file, 'r', encoding=charset) as f:
                    az_html = f.read()
            else:
                az_url_leave = ''
                if page_number > 1:
                    az_url_leave = r'#page={}'.format(page_number)
                az_page = iffr_hostname + az_url_format.format(az_url_leave)
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
            if film.filmid not in [1, 18, 123, 124, 175, 438, 572, 659, 688, 692]:
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

    def attr_str(self, attr, index):
        return (str)(attr[index])


class AzPageParser(HtmlPageParser):

    props_re = re.compile(
        r"""
            "bookings":\[\],"title":"(?P<title>[^"]+)                 # Title
            .*?"url\(\{\\"language\\":\\"nl\\"\}\)":"(?P<url>[^"]+)"  # URL
            ,"description\(\{.*?\}\)":"(?P<grid_desc>[^"]+)"          # Grid description
            ,"description\(\{.*?\}\)":"(?P<list_desc>[^"]+)"          # List description
            .*?"sortedTitle":"(?P<sorted_title>[^"]+)"                # Sorted Title
            (?:.*?"duration":(?P<duration>\d+)\})?                    # Duration
        """, re.VERBOSE)

    def __init__(self, iffr_data):
        HtmlPageParser.__init__(self, iffr_data, 'AZ')
        self.matching_attr_value = ""
        self.debugging = True
        self.init_film_data()

    def parse_props(self, data):
        for g in self.props_re.findall(data):
            self.title = g[0]
            self.url = iffr_hostname + g[1]
            self.description = g[2]
            self.article = g[3]
            self.sorted_title = g[4].lower()
            minutes = 0
            if len(g) > 5 and len(g[5]) > 0:
                minutes = int(g[5])
            self.duration = datetime.timedelta(minutes=minutes)
            self.add_film()
            if self.film is not None:
                self.add_filminfo()

    def init_film_data(self):
        self.film = None
        self.title = None
        self.url = None
        self.duration = None
        self.description = None
        self.article = None
        self.sorted_title = None
        # self.await_title = False
        # self.in_title = False
        # self.in_description = False
        # self.await_duration = False
        # self.in_duration = False

    def add_film(self):
        self.film = self.iffr_data.create_film(self.title, self.url)
        if self.film is None:
            Globals.error_collector.add(f'Could\'t create film from {self.title}', self.url)
        else:
            self.film.medium_category = self.url.split('/')[5]
            self.film.duration = self.duration
            self.film.sortstring = self.sorted_title
            print(f'Adding FILM: {self.title} ({self.film.duration_str()}) {self.film.medium_category}')
            self.iffr_data.films.append(self.film)

    def add_filminfo(self):
        filminfo = planner.FilmInfo(self.film.filmid, self.description, self.article)
        self.iffr_data.filminfos.append(filminfo)

    # def match_attr(self, curr_tag, test_tag, curr_attr, test_attr):
    #     self.matching_attr_value = ""
    #     if self.in_film_part:
    #         if curr_tag == test_tag:
    #             if self.attr_str(curr_attr, 0) == test_attr:
    #                 self.matching_attr_value = self.attr_str(curr_attr, 1)
    #                 return True
    #     return False

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
        # if tag == 'a' and len(attrs) > 0:
        #     attr = attrs[0]
        #     if attr[0] == 'href' and attr[1].startswith('/nl/2021/'):
        #         self.url = f'{iffr_hostname}{attr[1]}'
        #         self.await_title = True
        #         self.print_debug('--', f'Found URL: {self.url}')
        # elif self.await_title and tag == 'h4':
        #     self.await_title = False
        #     self.in_title = True
        # elif self.await_duration and tag == 'p':
        #     self.await_duration = False
        #     self.in_duration = True

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)
        if data.startswith('{"props":'):
            self.parse_props(data)
        # if self.in_title:
        #     self.in_title = False
        #     self.title = data
        #     self.print_debug('--', f'Found TITLE: {self.title}')
        #     self.in_description = True
        # elif self.in_description:
        #     self.in_description = False
        #     self.description = data
        #     self.print_debug('--', f'Found DESCRIPTION: {self.description}')
        #     self.await_duration = True
        # elif self.in_duration:
        #     self.in_duration = False
        #     if data == f'{festival} {year}':
        #         minutes = 0
        #     else:
        #         minutes = int(data.rstrip("'"))
        #     self.duration = datetime.timedelta(minutes=minutes)
        #     self.print_debug('--', f'Found DURATION: {self.duration}')
        #     self.add_film()


class FilmPageParser(HtmlPageParser):

    def __init__(self, iffr_data, film):
        HtmlPageParser.__init__(self, iffr_data, "F")
        self.film = film
        self.description = None
        self.article_paragraphs = []
        self.paragraph = None
        self.article = None
        self.debugging = True
        self.in_article = False
        self.await_article = False
        self.in_description = False
        self.await_content = False
        self.await_paragraph = False
        self.in_paragraph = False
        self.print_debug(f"{40 * '-'} ", f"Analysing FILM {film}")

        self.init_screened_film_data()
        self.screened_films = []
        self.in_screened_films = False

        self.init_screening_data()
        self.await_screenings = True
        self.in_screenings = False
        self.in_location = False
        self.in_time = False
        self.in_extra_or_qa = False
        self.matching_attr_value = ""

    def init_screened_film_data(self):
        self.screened_url = None
        self.screened_title = None
        self.screened_description = None
        self.in_screened_url = False
        self.await_screened_title = False
        self.in_screened_title = False
        self.await_screened_description = False
        self.in_screened_description = False

    def init_screening_data(self):
        self.screen = None
        self.start_date = None
        self.start_time = None
        self.end_time = None
        self.audience = None
        self.qa = ""
        self.extra = ""

    def create_article(self):
        self.article = '\n\n'.join(self.article_paragraphs)
        self.print_debug(f"Found ARTICLE of {self.film.title}:", self.article)

    def add_filminfo(self):
        description = self.description if self.description is not None else ''
        article = self.article if self.article is not None else ''
        filminfo = planner.FilmInfo(self.film.filmid, description, article, self.screened_films)
        self.iffr_data.filminfos.append(filminfo)

    def add_screened_film(self):
        print(f'Found screened film: {self.screened_title}')
        try:
            film = self.iffr_data.get_film_by_key(self.screened_title, self.screened_url)
        except KeyError:
            Globals.error_collector.add('No screened URL found', f'{self.screened_title}')
        else:
            screened_film = planner.ScreenedFilm(film.filmid, self.screened_title, self.screened_description)
            self.screened_films.append(screened_film)
        finally:
            self.init_screened_film_data()

    def add_screening(self):
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

        program = None
        if self.film.combination_url is not None:
            program = self.iffr_data.get_film_by_key(None, self.film.combination_url)
        screening = planner.Screening(self.film, self.screen, start_datetime, end_datetime, self.qa, self.extra, self.audience, program)

        self.iffr_data.screenings.append(screening)
        print("---SCREENING ADDED")
        self.in_extra_or_qa = False
        self.init_screening_data()

    def ok_to_add_screening(self):
        if self.audience is None:
            return False
        if self.extra == "Voorfilm: " + self.film.title:
            return False
        if not include_events and self.film.medium_category == "events":
            return False
        return True

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
                    self.print_debug(f'Found DESCRIPTION of {self.film.title}:', self.description)
        elif tag == 'article':
            self.await_article = True
        elif self.await_article and tag == 'div':
            self.await_article = False
            self.in_article = True
            self.await_paragraph = True
        elif self.await_paragraph and tag == 'p':
            self.await_paragraph = False
            self.in_paragraph = True
            self.paragraph = ''
        elif tag == 'main':
            self.in_screened_films = True
        elif self.in_screened_films and tag == 'li' and len(attrs) > 0:
            if attrs[0] == ('class', 'block-type-film az-block has-director'):
                self.in_screened_url = True
        elif self.in_screened_url and tag == 'a':
            self.in_screened_url = False
            if len(attrs) > 0:
                attr = attrs[0]
                self.screened_url = f'{iffr_hostname}{attr[1]}'
        elif self.in_screened_films and tag == 'section' and len(attrs) > 0:
            if attrs[0] == ('class', 'rectangle-column'):
                self.await_screened_title = True
                self.await_screened_description = True
        elif self.await_screened_title and tag == 'h2':
            self.await_screened_title = False
            self.in_screened_title = True
        elif self.await_screened_description and tag == 'p':
            self.await_screened_description = False
            self.in_screened_description = True

        # Get data for screenings.
        for attr in attrs:
            self.print_debug("Handling attr:      ", attr)
            if tag == "section" and attr == ("class", "film-screenings-wrapper"):
                self.in_screenings = True
                self.await_screenings = False
                self.print_debug("--  ", "ENTERING SCREENINGS SECTION")
            if self.await_screenings:
                collect_attr = "/nl/{}/verzamelprogrammas/".format(year)
                if tag == "a" and attr[0] == "href" and attr[1].startswith(collect_attr):
                    if self.film.medium_category != "verzamelprogrammas":
                        self.film.combination_url = f'{iffr_hostname}{attr[1]}'
                        program = self.iffr_data.get_film_by_key(None, self.film.combination_url)
                        print(f'--  PART OF COMBINATION: {program}')
            if self.in_screenings:
                if tag == "span" and attr == ("class", "location"):
                    self.in_location = True
                    self.print_debug("-- ", "ENTERING LOCATION")
                if tag == "a" and attr[0] == "data-audience":
                    self.audience = attr[1]
                if tag == "small" and attr[1] == "film-label voorfilm-qa":
                    self.in_extra_or_qa = True
                if tag == "a" and attr[0] == "data-date":
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
        if tag == 'main':
            self.await_screened_title = False
            self.await_screened_description = False
            self.in_screened_films = False
            self.add_filminfo()
        elif tag == 'title':
            self.in_description = True
        elif self.in_paragraph and tag == 'p':
            self.in_paragraph = False
            self.await_paragraph = True
            self.article_paragraphs.append(self.paragraph)
            self.paragraph = ''
        elif self.in_article and tag == 'div':
            self.in_article = False
            self.await_paragraph = False
            self.create_article()

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
        if self.in_paragraph:
            self.paragraph += data.replace('\n', ' ')
        elif self.in_screened_title:
            self.in_screened_title = False
            self.screened_title = data
        elif self.in_screened_description:
            self.in_screened_description = False
            self.screened_description = data
            self.add_screened_film()

        # Get data for screenings.
        if self.in_location:
            self.in_location = False
            location = data.strip()
            print(f"--  LOCATION:   {location}   CATEGORY: {self.film.medium_category}")
            self.print_debug("LOCATION", location)
            self.screen = self.iffr_data.get_screen(city, location)
            self.print_debug("-- ", "LEAVING LOCATION")
        if self.in_extra_or_qa:
            if data == "Met Q&A":
                self.qa = "QA"
                self.print_debug("-- ", "FOUND QA")
            else:
                self.extra = data
                self.print_debug("-- FOUND EXTRA:", self.extra)
        if self.in_time:
            times = data.strip()
            self.start_time = datetime.time.fromisoformat(times.split()[0])
            self.end_time = datetime.time.fromisoformat(times.split()[2])


class IffrData(planner.FestivalData):

    def _init__(self, plandata_dir):
        planner.FestivalData.__init__(self, plandata_dir)

    def _filmkey(self, film, url):
        return url


if __name__ == "__main__":
    main()
