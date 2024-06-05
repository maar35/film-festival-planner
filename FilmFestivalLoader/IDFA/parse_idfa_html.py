#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load films, film information, screens and screenings from the IDFA 2020
website.

Created on Wed Nov  4 20:36:18 2020

@author: maarten
"""

import datetime
import os
import re
from enum import Enum, auto
from typing import Dict
from urllib.parse import urlparse

from Shared.application_tools import ErrorCollector, DebugRecorder, comment, Counter
from Shared.parse_tools import FileKeeper, HtmlPageParser, ScreeningKey, try_parse_festival_sites
from Shared.planner_interface import FestivalData, Screening, Film, FilmInfo, ScreenedFilm, get_screen_from_parse_name
from Shared.web_tools import UrlFile, iri_slug_to_url

# Parameters.
festival = 'IDFA'
festival_city = 'Amsterdam'
festival_year = 2023

# Files.
fileKeeper = FileKeeper(festival, festival_year)
debug_file = fileKeeper.debug_file

# URL information.
festival_hostname = 'https://festival.idfa.nl'
section_path = '/programma/?page=1&tabIndex=2'

# Application tools.
error_collector = ErrorCollector()
debug_recorder = DebugRecorder(debug_file)
counter = Counter()

DEBUGGING = False
ALWAYS_DOWNLOAD = False
AUDIENCE_PUBLIC = 'publiek'


def main():
    # Initialize a festival data object.
    comment('Creating festival data object.')
    festival_data = IdfaData(fileKeeper.plandata_dir)

    # Set-up counters.
    counter.start('sections')
    counter.start('pathways')
    counter.start('film URLs')
    counter.start('film title')
    counter.start('sections with css data')
    counter.start('no description')
    counter.start('meta dicts')
    counter.start('corrected urls')
    counter.start('articles')
    counter.start('improper dates')
    counter.start('improper times')
    counter.start('filminfo update')
    counter.start('filminfo extended')
    counter.start('combination screenings')

    # Try parsing the websites.
    try_parse_festival_sites(parse_idfa_sites, festival_data, error_collector, debug_recorder, festival, counter)


def parse_idfa_sites(festival_data):
    comment('Parsing section pages.')
    get_films(festival_data)

    comment('Parsing film pages')
    FilmDetailsReader(festival_data).get_film_details()


def get_films(festival_data):
    section_url = festival_hostname + section_path
    section_file = os.path.join(fileKeeper.webdata_dir, 'sections.html')
    url_file = UrlFile(section_url, section_file, error_collector, debug_recorder, byte_count=200)
    section_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=f'Downloading {section_url}')
    if section_html:
        comment(f'Analysing sections page, encoding={url_file.encoding}')
        SectionsPageParser(festival_data).feed(section_html)


def get_films_by_section(festival_data, section_urls):
    for i, section_url in enumerate(section_urls):
        section_file = fileKeeper.numbered_webdata_file('section', i)
        url_file = UrlFile(section_url, section_file, error_collector, debug_recorder, byte_count=200)
        section_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD,
                                         comment_at_download=f'Downloading {section_url}')
        if section_html:
            comment(f'Analysing section page, encoding={url_file.encoding}')
            FilmsFromSectionPageParser(festival_data, section_url).feed(section_html)


class FilmDetailsReader:
    def __init__(self, festival_data):
        self.festival_data = festival_data

    def get_film_details(self):
        always_download = ALWAYS_DOWNLOAD
        for film, sections in FilmsFromSectionPageParser.sections_by_film.items():
            comment(f'Parsing film details of {film.title}')
            film_file = fileKeeper.film_webdata_file(film.film_id)
            url = film.url
            url_file = UrlFile(url, film_file, error_collector, debug_recorder, byte_count=200)
            film_html = url_file.get_text(always_download=always_download,
                                          comment_at_download=f'Downloading {film.url}')
            if film_html:
                print(f'Analysing film page, encoding={url_file.encoding}')
                corrected_url = None if url == film.url else url
                FilmPageParser(self.festival_data, film, sections, corrected_url=corrected_url).feed(film_html)


class SectionsPageParser(HtmlPageParser):
    class SectionParseState(Enum):
        AWAITING_URL = auto()
        DONE = auto()

    def __init__(self, festival_date):
        super().__init__(festival_date, debug_recorder, 'S', debugging=DEBUGGING)
        self.section_urls = []
        self.pathway_urls = []
        self.stateStack = self.StateStack(self.print_debug, self.SectionParseState.AWAITING_URL)

    def add_section(self, url):
        self.section_urls.append(url)
        counter.increase('sections')

    def add_pathway(self, url):
        self.pathway_urls.append(url)
        counter.increase('pathways')

    def add_theme(self, slug):
        url = iri_slug_to_url(festival_hostname, slug)
        theme = slug.split('/')[1]
        if theme == 'section':
            self.add_section(url)
        elif theme == 'pathways':
            self.add_pathway(url)
        else:
            error_collector.add('Unexpected theme', f'{theme}')

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.stateStack.state_is(self.SectionParseState.AWAITING_URL):
            if tag == 'a':
                if len(attrs) == 2 and attrs[0][0] == 'class' and attrs[0][1] == 'css-avil9w' and attrs[1][0] == 'href':
                    self.add_theme(attrs[1][1])
            elif tag == 'footer':
                self.stateStack.change(self.SectionParseState.DONE)
                get_films_by_section(self.festival_data, self.section_urls)


class FilmsFromSectionPageParser(HtmlPageParser):
    class FilmsParseState(Enum):
        AWAITING_TITLE = auto()
        IN_TITLE = auto()
        AWAITING_DESCR = auto()
        IN_DESCR = auto()
        AWAITING_FILM_URL = auto()
        IN_FILM_URL = auto()
        AWAITING_FILM_TITLE = auto()
        IN_FILM_TITLE = auto()
        IN_FILM_PROPERTIES = auto()
        IN_FILM_PROPERTY = auto()
        DONE = auto()

    color_by_section_id = {
        1: 'DodgerBlue',
        2: 'PeachPuff',
        3: 'PeachPuff',
        4: 'DodgerBlue',
        5: 'PaleVioletRed',
        6: 'LightSalmon',
        7: 'HotPink',
        8: 'Khaki',
        9: 'SpringGreen',
        10: 'DarkSeaGreen',
        11: 'OliveDrab',
        12: 'Olive',
        13: 'SpringGreen',
        14: 'PeachPuff',
        15: 'DodgerBlue',
        16: 'PeachPuff',
        17: 'DarkMagenta',
        18: 'IndianRed',
        19: 'PaleVioletRed',
        20: 'SpringGreen',
        21: 'CadetBlue',
        22: 'PapayaWhip',
        23: 'Orchid',
        24: 'DarkSeaGreen',
        25: 'PaleVioletRed',
        26: 'PeachPuff',
        27: 'PapayaWhip',
    }
    sections_by_film = {}

    def __init__(self, festival_data, section_url):
        super().__init__(festival_data, debug_recorder, 'FS', debugging=DEBUGGING)
        self.section_url = section_url
        self.section_name = None
        self.subsection = None

        # Initialize film data.
        self.film_url = None
        self.film_title = None
        self.film = None
        self.film_duration = None
        self.film_property_by_label = None
        self.metadata_key = None
        self.init_film_data()

        # Draw a bar with section info.
        self.draw_headed_bar(section_url)

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.FilmsParseState.AWAITING_TITLE)

    def init_film_data(self):
        self.film_url = None
        self.film_title = None
        self.film = None
        self.film_duration = None
        self.film_property_by_label = {}
        self.metadata_key = None

    def reset_film_parsing(self):
        self.state_stack.pop()
        self.set_duration()
        self.add_film()
        self.init_film_data()

    def draw_headed_bar(self, section_url):
        url_obj = urlparse(section_url)
        url_parts = url_obj.path.split('/')
        theme_type = url_parts[1]
        slug = url_parts[3]
        print(f'{theme_type} {self.headed_bar(header=slug)}')
        self.print_debug(self.headed_bar(header=slug))

    def get_subsection(self, section_description=None):
        if self.section_name:
            section = self.festival_data.get_section(self.section_name)
            try:
                section.color = self.color_by_section_id[section.section_id]
            except KeyError as e:
                error_collector.add(e, f'No color for section {section.name}')
            subsection = self.festival_data.get_subsection(section.name, self.section_url, section)
            subsection.description = section_description or section.name
            return subsection
        return None

    def add_film(self):
        # Create a new film.
        self.film = self.festival_data.create_film(self.film_title, self.film_url)
        if self.film is None:
            try:
                self.film = self.festival_data.get_film_by_key(self.film_title, self.film_url)
            except KeyError:
                error_collector.add(f'Could not create film:', f'{self.film_title} ({self.film_url})')
            else:
                self.sections_by_film[self.film].append(self.subsection)
        else:
            # Fill details.
            self.film.duration = self.film_duration
            self.film.subsection = self.subsection
            self.film.medium_category = Film.category_by_string['films']
            self.sections_by_film[self.film] = [self.subsection]

            # Add the film to the list.
            self.festival_data.films.append(self.film)

    def set_duration(self):
        try:
            film_length = self.film_property_by_label['length']
        except KeyError:
            minutes = 0
        else:
            minutes = int(film_length.split(' ')[0])  # '84 min'
        self.film_duration = datetime.timedelta(minutes=minutes)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.FilmsParseState.AWAITING_TITLE) and tag == 'meta' and len(attrs) == 2:
            if attrs[0] == ('property', 'og:description') and attrs[1][0] == 'content':
                self.state_stack.change(self.FilmsParseState.IN_TITLE)
        elif self.state_stack.state_is(self.FilmsParseState.IN_TITLE) and tag == 'span' and len(attrs):
            if attrs[0][0] == 'title':
                self.section_name = attrs[0][1].strip()
                self.state_stack.change(self.FilmsParseState.AWAITING_DESCR)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_DESCR) and tag == 'div' and len(attrs) == 1:
            if attrs[0] == ('class', 'ey43j5h0 css-uu0j5i-Body-Body'):
                self.state_stack.change(self.FilmsParseState.IN_DESCR)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_FILM_URL) and tag == 'article' and len(attrs):
            if attrs[0] == ('class', 'eqiw4yk1 css-scrfvs-Container-Container'):
                self.state_stack.push(self.FilmsParseState.IN_FILM_URL)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_DESCR) and tag == 'article' and len(attrs):
            if attrs[0] == ('class', 'eqiw4yk1 css-scrfvs-Container-Container'):
                self.subsection = self.get_subsection()
                counter.increase('no description')
                self.state_stack.push(self.FilmsParseState.IN_FILM_URL)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_URL) and tag == 'a' and len(attrs):
            if attrs[0][0] == 'href':
                slug = attrs[0][1]
                self.film_url = festival_hostname + slug    # Use literal slug, iri codes are not well understood.
                counter.increase('film URLs')
                self.state_stack.change(self.FilmsParseState.AWAITING_FILM_TITLE)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_FILM_TITLE) and tag == 'h2' and len(attrs) == 3:
            if attrs[0] == ('variant', '4') and attrs[1] == ('clamp', '2'):
                self.state_stack.change(self.FilmsParseState.IN_FILM_TITLE)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTIES):
            if tag == 'div' and len(attrs) and attrs[0][0] == 'data-meta':
                self.metadata_key = attrs[0][1]
                self.state_stack.change(self.FilmsParseState.IN_FILM_PROPERTY)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_FILM_URL) and tag == 'footer':
            self.state_stack.change(self.FilmsParseState.DONE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTY) and tag == 'div':
            self.state_stack.change(self.FilmsParseState.IN_FILM_PROPERTIES)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTIES) and tag == 'div':
            self.reset_film_parsing()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.FilmsParseState.IN_DESCR):
            if not data.startswith('.css'):
                section_description = data
                self.subsection = self.get_subsection(section_description)
                self.state_stack.change(self.FilmsParseState.AWAITING_FILM_URL)
            else:
                counter.increase('sections with css data')
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_TITLE):
            self.film_title = data
            counter.increase('film title')
            self.state_stack.change(self.FilmsParseState.IN_FILM_PROPERTIES)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTY):
            self.film_property_by_label[self.metadata_key] = data


class FilmPageParser(HtmlPageParser):
    class FilmParseState(Enum):
        IDLE = auto()
        AWAITING_TITLE = auto()
        IN_TITLE = auto()
        AWAITING_META_DICT = auto()
        IN_META_DICT = auto()
        IN_META_PROPERTY = auto()
        AWAITING_PAGE_SECTION = auto()
        IN_PAGE_SECTION = auto()
        AWAITING_ARTICLE = auto()
        IN_ARTICLE = auto()
        AWAITING_SCREENINGS = auto()
        IN_SCREENINGS = auto()
        IN_SCREENING_DATE = auto()
        AWAITING_SCREENING_INFO = auto()
        IN_SCREENING_INFO = auto()
        AWAITING_TIMES = auto()
        IN_TIMES = auto()
        AWAITING_LOCATION = auto()
        IN_LOCATION = auto()
        AWAITING_CREDITS = auto()
        IN_DICT = auto()
        IN_PROPERTY = auto()
        DONE = auto()

    # Instead of developing a new SpecialsPageParser, link special titles
    # and urls by hand.
    url_by_combi_title = {
        '16 Worlds on 16: American Experimental': 'https://festival.idfa.nl/section/2d577533-3b56-4ab9-8032-f85a8ccb332e/focus:-16-worlds-on-16/',
        'And How Miserable Is the Home of Evil & Talking with Rivers': 'https://festival.idfa.nl/composition/4472f00e-f123-4056-840f-0fed9d2503d2/and-how-miserable-is-the-home-of-evil-and-talking-with-rivers/',
        'Before Sandstorm & Mud': 'https://festival.idfa.nl/composition/72273ed4-8eef-4b76-aaf5-690e41dc6574/before-sandstorm-and-mud/',
        'Before Sandstorm & Mud, Georganiseerd door Soapbox': 'https://festival.idfa.nl/composition/72273ed4-8eef-4b76-aaf5-690e41dc6574/before-sandstorm-and-mud/',
        'Before Sandstorm & Mud, Sensory friendly screening': 'https://festival.idfa.nl/composition/72273ed4-8eef-4b76-aaf5-690e41dc6574/before-sandstorm-and-mud/',
        'Corresponding Cinemas: Basma al-Sharif & Jumana Manna': 'https://festival.idfa.nl/composition/ba8adeb9-2825-484f-9fd4-213508cd2756/corresponding-cinemas:-basma-al-sharif-and-jumana-manna/',
        'Corresponding Cinemas: Basma al-Sharif': 'https://festival.idfa.nl/composition/143d0dc2-b950-4da6-a587-5ff0ef3c1440/corresponding-cinemas:-basma-al-sharif/',
        'Corresponding Cinemas: Ibrahim Shaddad': 'https://festival.idfa.nl/composition/e5421cef-9f7b-488b-b107-0f409b9a7819/corresponding-cinemas:-ibrahim-shaddad/',
        'De Groene Amsterdammer-dag, De must-sees van IDFA 2023 volgens de redacteuren van De Groene Amsterdammer.': 'https://festival.idfa.nl/composition/28f44ee2-358d-4961-90c8-1c6c858956db/de-groene-amsterdammer-dag/',
        'DocLab Exhibition: Phenomenal Friction': 'https://festival.idfa.nl/section/502a3ed8-572f-498d-b41a-940494f47c7a/idfa-doclab:-phenomenal-friction/',
        'DocLab Live: Koyaanisqatsi Special': 'https://festival.idfa.nl/composition/515ac5a7-8a7b-4b47-becf-9d60254a572e/doclab-live:-koyaanisqatsi-special/',
        'DocLab: VR Booth in Main Exhibition': 'https://festival.idfa.nl/composition/4f653351-6b52-4317-a650-de5b73434a13/doclab:-vr-booth-in-main-exhibition/',
        'DocLab: VR Gallery': 'https://festival.idfa.nl/composition/3c3d05ae-4307-4c24-b87a-de5c335dfd2a/doclab:-vr-gallery/',
        'Fogo île de feu & On the Other Island': 'https://festival.idfa.nl/composition/3ff6602f-90a1-4965-825b-4934666f6371/fogo-ile-de-feu-and-on-the-other-island/',
        'How to Please & Nightwatchers': 'https://festival.idfa.nl/composition/b2f5b1d2-a2e9-481b-929a-2f57719127b0/how-to-please-and-nightwatchers/',
        'IDFA Junior': 'https://festival.idfa.nl/composition/25252b1c-1782-42a4-8917-cbd4d7705b7a/idfa-junior/',
        'IDFA Meets x Subbacultcha, Avant-pop band Sergeant laat zich inspireren door twee shorts uit het Paradocs programma.': 'https://festival.idfa.nl/composition/df281ce5-154a-430f-a47e-48b83e922961/idfa-meets-x-subbacultcha/',
        'IDFA Shorts 1': 'https://festival.idfa.nl/composition/d2c54e11-34eb-446f-b6d5-a248e2239f17/idfa-shorts-1/',
        'IDFA Shorts 2': 'https://festival.idfa.nl/composition/f7aa259a-7962-478f-8b88-9558b0e1c76a/idfa-shorts-2/',
        'IDFA Shorts 2, The Story of Ne Kuko, met een Talk verzorgd door Oneworld.': 'https://festival.idfa.nl/composition/f7aa259a-7962-478f-8b88-9558b0e1c76a/idfa-shorts-2/',
        "IDFA Shorts 2, Meervaart Studio bespreekt 'reclaiming space' met de filmmaker van Hotel Mokum.": 'https://festival.idfa.nl/composition/f7aa259a-7962-478f-8b88-9558b0e1c76a/idfa-shorts-2/',
        'IDFA Shorts 3': 'https://festival.idfa.nl/composition/8da51942-d67d-45a2-b89d-2e864ef34db5/idfa-shorts-3/',
        'IDFA Shorts 4': 'https://festival.idfa.nl/composition/e1442ffb-4062-4c49-b6e1-7d47caa80793/idfa-shorts-4/',
        'IDFA Shorts 4, Gratis toegankelijk voor Cineville pashouders.': 'https://festival.idfa.nl/composition/e1442ffb-4062-4c49-b6e1-7d47caa80793/idfa-shorts-4/',
        'IDFA Shorts 5': 'https://festival.idfa.nl/composition/f71393b8-5989-4f5e-8817-7e08ad77ef23/idfa-shorts-5/',
        'IDFA Shorts 6': 'https://festival.idfa.nl/composition/c093cec5-0c9a-40b3-80ff-cb6203c47be3/idfa-shorts-6/',
        'IDFA Shorts 7': 'https://festival.idfa.nl/composition/34a02290-6862-424c-9b66-e150117aad81/idfa-shorts-7/',
        'Incident & Landslide': 'https://festival.idfa.nl/composition/9a175161-71f5-4543-86f6-8be60beb3222/incident-and-landslide/',
        'Jeugdvoorstelling': 'https://festival.idfa.nl/composition/8ee6e4f5-72cc-4575-aeb1-15928c1afa63/jeugdvoorstelling/',
        'Paradocs Shorts': 'https://festival.idfa.nl/composition/e8a63491-759d-4e5e-ae2d-dadd3874785b/paradocs-shorts/',
        'People from the Heart of the Earth & Marungka Tjalatjunu': 'https://festival.idfa.nl/composition/108f4942-1b03-4356-bfd2-1929beb54243/people-from-the-heart-of-the-earth-and-marungka-tjalatjunu/',
        'Red Flag & Postcards from the Verge': 'https://festival.idfa.nl/composition/7ef93f13-f1a2-4ef6-b91d-9c4f3110d595/red-flag-and-postcards-from-the-verge/',
        'Step by Step & First Case, Second Case': 'https://festival.idfa.nl/composition/1879bf5a-128b-4d78-8b2a-efd5d02d3dfb/step-by-step-and-first-case-second-case/',
        "Tomorrow's Classics": "https://festival.idfa.nl/composition/72d8a429-a1d1-4f31-80a3-6276a8e61a3b/tomorrow's-classics/",
        'VPRO Preview': 'https://festival.idfa.nl/composition/1ea96e78-2d83-4239-9831-5b0f54c8e9e1/vpro-preview/',
        'VPRO Review': 'https://festival.idfa.nl/composition/d90434c6-035c-4d1f-9a84-c2b2fbd76a17/vpro-review/',
        'Vriendenvoorstelling: Glass, My Unfulfilled Life, Vrienden worden uitgenodigd voor de Vriendenvoorstelling. Kijk op idfa.nl/vriend.': 'https://festival.idfa.nl/composition/ad9a1be6-809f-4e65-9604-afbddf50ffcd/vriendenvoorstelling:-glass-my-unfulfilled-life/',
        'WePresent Night, Talk met Amanda Kim + borrel in Eye van 19:00 - 20:30, aangeboden door WePresent.': 'https://festival.idfa.nl/composition/fc3878cc-4d24-4bc2-95e1-a309192ee24c/wepresent-night/',
        'Who Tells the Story? & Citizen Sleuth': 'https://festival.idfa.nl/composition/a24cb2b4-3395-4afa-98f2-25f0f3cf1a37/who-tells-the-story-and-citizen-sleuth/',
        'Youth 13+: Love, Your Neighbour & Another Body': 'https://festival.idfa.nl/composition/087c205c-9141-4388-9aac-a41e2db17b4b/youth-13+:-love-your-neighbour-and-another-body/',
        'Youth 13+: Unfiltered Reality': 'https://festival.idfa.nl/composition/d4b56229-5115-4f4e-ab85-5caf4a4980d9/youth-13+:-unfiltered-reality/',
        'Youth 13+: Where Am I From? & Boyz': 'https://festival.idfa.nl/composition/0bb709ec-9f4c-4a6c-849f-e4da98f0fdf2/youth-13+:-where-am-i-from-and-boyz/',
        'Youth 9-12: Extraordinary Life': 'https://festival.idfa.nl/composition/ccf51b8c-8bf3-4cb4-bde4-76a7d9c9d97c/youth-9-12:-extraordinary-life/',
        'Youth 9-12: Figure & JessZilla': 'https://festival.idfa.nl/composition/e7d5ce72-41e0-447f-b8b3-0bd88a4810c4/youth-9-12:-figure-and-jesszilla/',
        "Youth 9-12: Girls' Stories & And a Happy New Year": "https://festival.idfa.nl/composition/49c06e0f-7a05-445c-bcd3-f9cb2d48fe0f/youth-9-12:-girls'-stories-and-and-a-happy-new-year/",
        'de Volkskrantdag': 'https://festival.idfa.nl/composition/f12b7b9c-29e1-4596-a6a0-d8e231a6af47/de-volkskrantdag/',
    }
    re_desc = re.compile(r'(?P<title>.*), (?P<desc>[A-Z].*\.)$')
    re_num_screen = re.compile(r'^(?P<theater>.*?)\s+(?P<number>\d+)$')
    re_colon_screen = re.compile(r'^(?P<theater>.*?):\s+(?P<room>.+)$')
    nl_month_by_name: Dict[str, int] = {'november': 11}

    def __init__(self, festival_data, film, sections, debug_prefix='F', corrected_url=None):
        super().__init__(festival_data, debug_recorder, debug_prefix, debugging=DEBUGGING)
        self.film = film
        self.sections = sections
        self.corrected_url = corrected_url
        self.title = film.title
        self.film_property_by_label = {}
        self.film_info = None
        self.duration = None

        # Initialize screening data.
        self.metadata_key = None
        self.start_date = None
        self.start_dt = None
        self.end_dt = None
        self.screen = None
        self.qa = None
        self.audience = None
        self.extra = None
        self.combi_title = None
        self.init_screening_data()

        # Draw a bar with section info.
        self.print_debug(self.headed_bar(header=str(self.film)))
        if corrected_url:
            counter.increase('corrected urls')

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.FilmParseState.IDLE)

    def init_screening_data(self):
        self.metadata_key = None
        self.start_date = None
        self.start_dt = None
        self.end_dt = None
        self.screen = None
        self.qa = ''
        self.audience = AUDIENCE_PUBLIC
        self.extra = ''
        self.combi_title = None

    def add_paragraph(self):
        paragraph = self.article_paragraph
        if len(paragraph) > 0:
            self.article_paragraphs.append(paragraph.strip())
        self.article_paragraph = ''

    def set_article(self):
        self.article = '\n\n'.join(self.article_paragraphs)
        self.set_description_from_article(self.film.title)
        counter.increase('articles')

    def add_film_info(self):
        self.film_info = FilmInfo(self.film.film_id, self.description, self.article)
        self.festival_data.filminfos.append(self.film_info)

    def update_film_info(self):
        counter.increase('filminfo update')
        if self.film_property_by_label:
            counter.increase('meta dicts')
            properties = [f'{key}: {value}' for (key, value) in self.film_property_by_label.items()]
            metadata = '\n'.join(properties)
            self.film_info.article += f'\n\n{metadata}'
            counter.increase('filminfo extended')

    def set_screening_date(self, data):
        parts = data.split()  # '10 november'
        try:
            day = int(parts[0])
            month = int(FilmPageParser.nl_month_by_name[parts[1]])
        except ValueError as e:
            counter.increase('improper dates')
            self.print_debug(f'{e} in {self.film}', 'Proceeding to next page section')
            return False
        else:
            self.start_date = datetime.date(day=day, month=month, year=festival_year)
        return True

    def set_screening_times(self, data):
        try:
            start_time = datetime.time(int(data[:2]), int(data[3:5]))   # '14.00–15.28'
            end_time = datetime.time(int(data[6:8]), int(data[9:]))
        except ValueError as e:
            counter.increase('improper times')
            self.print_debug(f'{e} in times of {self.film} screening', 'Proceeding to next page section')
            return False
        else:
            start_date = self.start_date
            end_date = start_date if end_time > start_time else start_date + datetime.timedelta(days=1)
            self.start_dt = datetime.datetime.combine(start_date, start_time)
            self.end_dt = datetime.datetime.combine(end_date, end_time)
        return True

    def get_idfa_screen(self, data):
        screen_parse_name = data.strip()
        return get_screen_from_parse_name(self.festival_data, screen_parse_name, self.split_location)

    def split_location(self, location):
        city_name = festival_city
        theater_parse_name = location
        screen_abbreviation = 'zaal'
        colon_match = self.re_colon_screen.match(location)
        if colon_match:
            theater_parse_name = colon_match.group(1)
            screen_abbreviation = colon_match.group(2)
        else:
            num_match = self.re_num_screen.match(location)
            if num_match:
                theater_parse_name = num_match.group(1)
                screen_abbreviation = num_match.group(2)
        return city_name, theater_parse_name, screen_abbreviation

    def process_screening_info(self, data):
        qa_words = ['gesprek', 'Q&amp;A', 'Talk', 'nagesprek']
        private_words = ['Exclusief', 'Pashouders']
        part_of_prefix = 'Onderdeel van'
        self.qa = 'QA' if len([w for w in qa_words if w in data]) else ''
        self.audience = 'private' if len([w for w in private_words if w in data]) else AUDIENCE_PUBLIC
        if data.startswith(part_of_prefix):
            self.combi_title = data[len(part_of_prefix):].strip()
            self.print_debug('FOUND COMBINATION TITLE', f'{self.combi_title}')

    def add_idfa_screening(self, display=False):
        # Create an IDFA screening from the gathered data.
        self.screening = IdfaScreening(self.film, self.screen, self.start_dt, self.end_dt,
                                       qa=self.qa, audience=self.audience, extra=self.extra,
                                       combi_title=self.combi_title)
        self.add_screening(self.screening, display=display)

        # Prepare combination film data if applicable.
        if self.combi_title in self.url_by_combi_title.keys():
            self.screening.combi_url = self.url_by_combi_title[self.combi_title]
            m = re.match(self.re_desc, self.combi_title)
            if m:
                g = m.groupdict()
                self.combi_title = g['title']
                print(f"{g['title']:-<80}{g['desc']}")
            self.set_combination(self.screening)

        # Reset data as to find the next screening.
        self.init_screening_data()

    def set_combination(self, screening):
        combi_url = screening.combi_url

        # Get the combination film or create it.
        combi_film = self.festival_data.create_film(self.combi_title, combi_url)
        if combi_film is None:
            try:
                combi_film = self.festival_data.get_film_by_key(self.combi_title, combi_url)
            except KeyError:
                error_collector.add(f'Could not create combination film:', f'{self.combi_title} ({combi_url})')
                return
        else:
            combi_film.duration = screening.end_datetime - screening.start_datetime
            combi_film.medium_category = Film.category_by_string['combinations']
            self.festival_data.films.append(combi_film)
        combi_screening = IdfaScreening(
            combi_film, screening.screen, screening.start_datetime, screening.end_datetime, audience=AUDIENCE_PUBLIC
        )
        if combi_screening not in combi_film.screenings(self.festival_data):
            self.festival_data.screenings.append(combi_screening)
            counter.increase('combination screenings')

        # Update the combination film info.
        combi_film_info = combi_film.film_info(self.festival_data)
        screened_film_info = self.film.film_info(self.festival_data)
        if not combi_film_info.film_id:
            combi_film_info.film_id = combi_film.film_id
            combi_film_info.description = self.combi_title
            self.festival_data.filminfos.append(combi_film_info)
        if self.film.film_id not in [sf.film_id for sf in combi_film_info.screened_films]:
            screened_film = ScreenedFilm(self.film.film_id, self.film.title, screened_film_info.description)
            combi_film_info.screened_films.append(screened_film)

        # Update the screened film info.
        if combi_film.film_id not in [cf.film_id for cf in screened_film_info.combination_films]:
            screened_film_info.combination_films.append(combi_film)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.FilmParseState.IDLE) and tag == 'script':
            self.state_stack.push(self.FilmParseState.AWAITING_TITLE)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_TITLE) and tag == 'h1':
            self.state_stack.change(self.FilmParseState.IN_TITLE)
        elif self.state_stack.state_in([
                self.FilmParseState.AWAITING_META_DICT,
                self.FilmParseState.IN_META_DICT,
                self.FilmParseState.AWAITING_CREDITS]):
            if tag == 'div' and len(attrs) and attrs[0][0] == 'data-meta':
                self.metadata_key = attrs[0][1]
                self.state_stack.change(self.FilmParseState.IN_META_PROPERTY)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_PAGE_SECTION) and tag in ['div', 'h2']:
            if len(attrs) == 2 and attrs[0] == ('variant', '3'):
                if attrs[1] == ('class', 'e10q2t3u0 css-1bg59lt-Heading-Heading-Heading'):
                    self.state_stack.push(self.FilmParseState.IN_PAGE_SECTION)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_ARTICLE) and tag == 'p':
            self.state_stack.change(self.FilmParseState.IN_ARTICLE)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_SCREENINGS) and tag == 'div':
            if len(attrs) == 2 and attrs[0] == ('variant', '4'):
                self.state_stack.change(self.FilmParseState.IN_SCREENINGS)
                self.state_stack.push(self.FilmParseState.IN_SCREENING_DATE)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_SCREENING_INFO) and tag == 'div':
            if len(attrs) and attrs[0] == ('class', 'ey43j5h0 css-1cky3te-Body-Body'):
                self.state_stack.change(self.FilmParseState.IN_SCREENING_INFO)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_TIMES) and tag == 'span':
            self.state_stack.change(self.FilmParseState.IN_TIMES)
        elif self.state_stack.state_is(self.FilmParseState.IN_SCREENINGS) and tag == 'div' and len(attrs) == 2:
            if attrs[0] == ('variant', '4'):
                self.state_stack.push(self.FilmParseState.IN_SCREENING_DATE)
            elif attrs[0] == ('variant', '3'):
                self.state_stack.change(self.FilmParseState.IN_PAGE_SECTION)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_is(self.FilmParseState.IN_META_PROPERTY) and tag == 'div':
            self.state_stack.change(self.FilmParseState.IN_META_DICT)
        elif self.state_stack.state_is(self.FilmParseState.IN_META_DICT) and tag == 'div':
            print(f'{self.film_property_by_label=}')
            self.print_debug('FOUND DICT', f'{self.film_property_by_label=}')
            self.state_stack.change(self.FilmParseState.AWAITING_PAGE_SECTION)
        elif self.state_stack.state_is(self.FilmParseState.IN_DICT):
            self.state_stack.change(self.FilmParseState.AWAITING_TITLE)
        elif self.state_stack.state_is(self.FilmParseState.IN_ARTICLE):
            if tag == 'p':
                self.add_paragraph()
            elif tag == 'div':
                self.set_article()
                self.add_film_info()
                self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmParseState.IN_SCREENING_INFO) and tag == 'div':
            self.state_stack.change(self.FilmParseState.AWAITING_TIMES)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_LOCATION) and tag == 'svg':
            self.state_stack.change(self.FilmParseState.IN_LOCATION)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.FilmParseState.IN_TITLE):
            self.title = data
            if self.film.title != self.title:
                error_desc = f'"{self.title}" while parsing "{self.film}"'
                debug_text = '\n'.join([
                    error_desc,
                    f'{"registered url":-<20}{self.film.url}',
                    f'{"corrected url":-<20}{self.corrected_url}',
                ])
                error_collector.add('DIFFERENT TITLE', error_desc)
                self.print_debug(f'DIFFERENT TITLE: {debug_text}')
            self.state_stack.change(self.FilmParseState.AWAITING_META_DICT)
        elif self.state_stack.state_is(self.FilmParseState.IN_META_PROPERTY):
            self.film_property_by_label[self.metadata_key] = data
        elif self.state_stack.state_is(self.FilmParseState.IN_PAGE_SECTION):
            if data == 'Synopsis':
                self.state_stack.change(self.FilmParseState.AWAITING_ARTICLE)
            elif data.startswith('Tickets'):
                self.state_stack.change(self.FilmParseState.AWAITING_SCREENINGS)
            elif data == 'Credits':
                self.state_stack.change(self.FilmParseState.AWAITING_CREDITS)
            elif data == 'Stills':
                self.update_film_info()
                self.state_stack.change(self.FilmParseState.DONE)
        elif self.state_stack.state_is(self.FilmParseState.IN_SCREENING_INFO):
            self.process_screening_info(data)
        elif self.state_stack.state_is(self.FilmParseState.IN_ARTICLE):
            if not data.startswith('.css'):
                self.article_paragraph += data
        elif self.state_stack.state_is(self.FilmParseState.IN_SCREENING_DATE):
            if self.set_screening_date(data):
                self.state_stack.change(self.FilmParseState.AWAITING_SCREENING_INFO)
            else:
                self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmParseState.IN_TIMES):
            if self.set_screening_times(data):
                self.state_stack.change(self.FilmParseState.AWAITING_LOCATION)
            else:
                self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmParseState.IN_LOCATION):
            self.screen = self.get_idfa_screen(data)
            self.add_idfa_screening(True)
            self.state_stack.pop()


class IdfaScreening(Screening):
    def __init__(self, film, screen, start_datetime, end_datetime,
                 qa='', extra='', audience=None, combi_title=None, combi_url=None):
        super().__init__(film, screen, start_datetime, end_datetime, qa, extra, audience)
        self.combi_title = combi_title
        self.combi_url = combi_url


class IdfaData(FestivalData):
    duplicates_by_screening = {}

    def __init__(self, directory):
        super().__init__(festival_city, directory)
        self.compilation_by_url = {}

    def film_key(self, title, url):
        return url

    def screening_can_go_to_planner(self, screening):
        can_go = screening.is_public()
        if can_go:
            try:
                self.duplicates_by_screening[screening] += 1
                can_go = False
            except KeyError:
                self.duplicates_by_screening[screening] = 0
        if can_go:
            can_go = screening.combi_url is None
        if can_go:
            can_go = screening.screen.screen_id != 126      # de Brakke Grond
        if can_go:
            can_go = not self.is_coinciding(screening)
        return can_go

    def film_can_go_to_planner(self, film_id):
        return True

    def is_coinciding(self, screening):
        # Get the film info.
        film_info = screening.film.film_info(self)

        # Check if the film is a combination program.
        screened_films = film_info.screened_films
        if len(screened_films):
            return False

        # Check if the film is screened as part of a combination
        # program.
        combination_films = film_info.combination_films
        if len(combination_films):
            key = ScreeningKey(screening)
            for combination_film in combination_films:
                for combination_screening in combination_film.screenings(self):
                    if key == ScreeningKey(combination_screening):
                        return True

        # This screening doesn't coincide with a combination program.
        return False


if __name__ == "__main__":
    main()
