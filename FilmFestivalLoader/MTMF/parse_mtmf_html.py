#!/usr/bin/env python3
import csv
import datetime
import os
import re
from enum import Enum, auto
from html import unescape
from typing import Dict

from Shared.application_tools import ErrorCollector, DebugRecorder, Counter, comment
from Shared.parse_tools import HtmlPageParser, FileKeeper, try_parse_festival_sites
from Shared.planner_interface import FilmInfo, FestivalData, link_screened_film, Screening
from Shared.web_tools import UrlFile, UrlReader, iri_slug_to_url, get_netloc

ALWAYS_DOWNLOAD = False
DEBUGGING = True
DISPLAY_ADDED_SCREENING = True
ONLY_PARSE_SCREENED_FILMS = True

FESTIVAL = 'MTMF'
FESTIVAL_YEAR = 2026
FESTIVAL_CITY = 'Den Haag'

# Files.
FILE_KEEPER = FileKeeper(FESTIVAL, FESTIVAL_YEAR)

# URL information.
MTMF_HOSTNAME = 'https://moviesthatmatter.nl'
MTMF_TICKETS_HOSTNAME = 'https://tickets.moviesthatmatter.nl'

# Application tools.
ERROR_COLLECTOR = ErrorCollector()
DEBUG_RECORDER = DebugRecorder(FILE_KEEPER.debug_file, active=DEBUGGING)
COUNTER = Counter()

# Experiment.
TRY_EXPERIMENT = False
EXPERIMENT_TROUW_PATH = 'https://moviesthatmatter.nl/festival/specials/trouw/'


def main():
    # Initialize a festival data object.
    festival_data = MtmfData(FILE_KEEPER.plandata_dir)

    # Set up counters.
    setup_counters()

    # Try parsing the websites.
    try_parse_festival_sites(parse_mtmf_sites, festival_data, ERROR_COLLECTOR, DEBUG_RECORDER, FESTIVAL, COUNTER)


def setup_counters():
    COUNTER.start('themes')
    COUNTER.start('competitions')
    COUNTER.start('specials')
    COUNTER.start('films')
    COUNTER.start('duplicates')
    COUNTER.start('metadata')
    COUNTER.start('screenings')
    COUNTER.start('not in dh')
    COUNTER.start('in past')
    COUNTER.start('sold out')
    COUNTER.start('no end time')
    COUNTER.start('end time not reconstructed')
    COUNTER.start('combi screening props fixed')
    COUNTER.start('screen reconstructed')
    COUNTER.start('screen not recovered')
    COUNTER.start('no theater')
    COUNTER.start('screened films')
    COUNTER.start('combi url linked to film')
    COUNTER.start('combination films')
    COUNTER.start('no screened film')
    COUNTER.start('url fixed')
    COUNTER.start('EN url fixed')
    COUNTER.start('end time not reconstructed')


def parse_mtmf_sites(festival_data):
    """
    Callback method to pass to try_parse_festival_sites().
    :param festival_data: planner_interface.festival_data object
    :return: None
    """
    if TRY_EXPERIMENT:
        # Facilitate experiments.
        experiment_get_trouw_films()
    else:
        # Set up a film url finder.
        url_finder = FilmUrlFinder(festival_data)

        # Read film urls from the section sites.
        comment(f"Find film URL's from the festival section sites")
        url_finder.read_sections()

        # Get the films.
        comment('Get films by URL')
        get_films_by_url(festival_data, url_finder.charset_by_film_url)

        # Link combination programs and screened films.
        comment('Apply combination data')
        FilmPageParser.apply_combinations(festival_data)

        # Recover screens of sold-out screenings.
        comment('Recover sold-out screenings')
        ScreeningsPageParser.recover_sold_out_screens(festival_data)


def experiment_get_trouw_films():
    """Experiment with the Trouw page."""
    for id_, url in enumerate([EXPERIMENT_TROUW_PATH]):
        prefix = 'trouw'
        day_file = FILE_KEEPER.numbered_webdata_file(prefix, id_)
        url_file = UrlFile(url, day_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
        comment_at_download = f'Downloading {prefix} page: {url}, encoding: {url_file.encoding}'
        day_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
        if day_html:
            comment(f'Analysing experiment page #{id_}, encoding={url_file.encoding}')


def get_films_by_url(festival_data, charset_by_film_url):
    for film_url, charset in charset_by_film_url.items():
        get_film_by_url(festival_data, film_url, charset)


def get_film_by_url(festival_data, url, charset):
    # Try if the film to be read already has a number.
    try:
        film_id = festival_data.film_id_by_url[url]
    except KeyError:
        get_film_from_url(festival_data, url, charset)
    else:
        film = festival_data.get_film_by_id(film_id)
        if film is None:
            film_file = FILE_KEEPER.film_webdata_file(film_id)
            url_file = UrlFile(url, film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=500)
            comment_at_download = f'Downloading film site: {url}, encoding: {url_file.encoding}'
            film_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=f'{comment_at_download}')
            if film_html is not None:
                print(f'Analysing html file {film_id} of {url}')
                film_parser = FilmPageParser(festival_data, url)
                film_parser.feed(film_html)
                ScreeningsPageParser(festival_data, film_parser.film, film_parser.subtitles).feed(film_html)


def get_film_from_url(festival_data, url, encoding):
    # Get the html data form the url.
    print(f'Requesting film page {url}, encoding={encoding}')
    reader = UrlReader(ERROR_COLLECTOR)
    film_parser = FilmPageParser(festival_data, url)
    film_html = reader.load_url(url, target_file=None, encoding=encoding)
    if film_html:
        print(f'Analysing film program data from {url}')
        film_parser.feed(film_html)

    # Write the gotten html to file.
    try:
        film_id = festival_data.film_id_by_url[url]
    except KeyError as e:
        ERROR_COLLECTOR.add(e, 'No film id found with this URL')
    else:
        film_file = FILE_KEEPER.film_webdata_file(film_id)
        print(f'Writing film html {festival_data.get_film_by_id(film_id).title} to {film_file}')
        html_bytes = film_html.encode(encoding=encoding)
        with open(film_file, 'wb') as f:
            f.write(html_bytes)


def set_subsection_description(festival_data, subsection):
    prefix = subsection.url.split('/')[-2]
    file_name = FILE_KEEPER.numbered_webdata_file('subsection', subsection.subsection_id)
    url_file = UrlFile(subsection.url, file_name, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
    comment_at_download = f'Downloading subsection page: {subsection.url}, encoding: {url_file.encoding}'
    html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
    if html:
        print(f'\nAnalysing subsection page #{subsection.subsection_id}, encoding={url_file.encoding}')
        subsection_desc_parser = SubsectionDescriptionParser(festival_data, prefix)
        subsection_desc_parser.feed(html)
        subsection.description = subsection_desc_parser.subsection_description


def append_to_dict_value(dict_, key, new_element):
    try:
        dict_[key].append(new_element)
    except KeyError:
        dict_[key] = [new_element]


class FilmUrlFinder:
    re_segment_str = r'/[^/#"]*/'
    re_films = re.compile('href="(https://moviesthatmatter.nl/festival/film/[^/]*/)"')
    main_sections = {
        'themas': {'singular': 'theme', 'plural': 'themes'},
        'competities': {'singular': 'competition', 'plural': 'competitions'},
        'specials': {'singular': 'special', 'plural': 'specials'},
    }
    color_by_section_name = {
        'themas': 'DodgerBlue',
        'competities': 'Red',
        'specials': 'LimeGreen',
    }
    correct_path_by_notfound_path = {
    }
    charset_by_film_url = {}
    subsection_by_film_url = {}

    def __init__(self, festival_data):
        self.festival_data = festival_data
        self.section_urls = None
        self.re_by_section = {section: self.re_section(section) for section in self.main_sections.keys()}
        for section_dict in self.main_sections.values():
            COUNTER.start(section_dict['plural'])

    def __str__(self):
        return '\n'.join(self.charset_by_film_url)

    @staticmethod
    def section_base(section):
        return iri_slug_to_url(MTMF_HOSTNAME, f'festival/{section}')

    def re_section(self, section):
        return re.compile(self.section_base(section) + self.re_segment_str)

    def read_sections(self):
        for section_name in self.main_sections.keys():
            self.read_main_section(section_name)

    def read_main_section(self, section_name):
        section_url = self.section_base(section_name)
        section_file = os.path.join(FILE_KEEPER.webdata_dir, f'{section_name}.html')
        section = self.festival_data.get_section(section_name, self.color_by_section_name[section_name])
        url_file = UrlFile(section_url, section_file, ERROR_COLLECTOR, DEBUG_RECORDER)
        section_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD)
        if section_html is not None:
            subsection_urls = self.re_by_section[section_name].findall(section_html)
            comment(f'{len(subsection_urls)} "{section_name}" subsection urls found.')
            print(f'{'\n'.join(subsection_urls)}')
            for i, subsection_url in enumerate(subsection_urls):
                COUNTER.increase(self.main_sections[section_name]['plural'])
                subsection = self.get_subsection(section, subsection_url)
                set_subsection_description(self.festival_data, subsection)
                self.get_film_urls(subsection, self.main_sections[section_name]['singular'], i)

    def get_film_urls(self, subsection, prefix, subsection_index):
        subsection_file = FILE_KEEPER.numbered_webdata_file(f'section_{prefix}', subsection_index)
        subsection_url = subsection.url
        url_file = UrlFile(subsection_url, subsection_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=500)
        subsection_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD)
        if subsection_html is not None:
            print(f'Getting film urls from {subsection_file}, encoding={url_file.encoding}')
            film_count = 0
            for m in self.re_films.finditer(subsection_html):
                film_url = m.group(1)
                film_url = self.fix_misspelled_url(film_url)
                if film_url in self.charset_by_film_url:
                    COUNTER.increase('duplicates')
                else:
                    film_count += 1
                    COUNTER.increase('films')
                    self.charset_by_film_url[film_url] = url_file.encoding
                    self.subsection_by_film_url[film_url] = subsection
            print(f'{film_count} films in {subsection.section.name}: {subsection.name}')

    def get_subsection(self, section, url):
        lower_name = url.split('/')[-2].replace('-', ' ')
        try:
            subsection_name = lower_name[0].upper() + lower_name[1:]
        except IndexError as e:
            ERROR_COLLECTOR.add(e, f'{url=}')
            subsection = None
        else:
            subsection = self.festival_data.get_subsection(subsection_name, url, section)
        return subsection

    @classmethod
    def fix_misspelled_url(cls, url):
        url = unescape(url)
        url = cls.set_nl_url(url)
        parts = url.split('/')
        path = parts[-2]  # https://moviesthatmatter.nl/festival/film/there-will-be-no-end/
        try:
            correct_path = cls.correct_path_by_notfound_path[path]
        except KeyError:
            pass
        else:
            COUNTER.increase('url fixed')
            parts[-2] = correct_path
            url = '/'.join(parts)
        return url

    @classmethod
    def set_nl_url(cls, url):
        language_iso = 'en'
        if url.split('/')[3] == language_iso:
            parts = url.split('/')
            parts.remove(language_iso)
            url = '/'.join(parts)
            COUNTER.increase('EN url fixed')
        return url


class FilmPageParser(HtmlPageParser):
    class FilmsParseState(Enum):
        IDLE = auto()
        IN_TITLE = auto()
        IN_ARTICLE = auto()
        IN_PARAGRAPH = auto()
        IN_EMPHASIS = auto()
        AWAITING_COMBINATION = auto()
        NEAR_COMBINATION = auto()
        IN_COMBINATION = auto()
        IN_PROPERTIES = auto()
        IN_LABEL = auto()
        AWAITING_VALUE = auto()
        IN_VALUE = auto()
        DONE = auto()

    category_by_branch = dict(film='films')
    combination_urls_by_film_id = {}
    applying_combination = False

    def __init__(self, festival_data, url):
        super().__init__(festival_data, DEBUG_RECORDER, 'F')
        self.url = url
        self.festival_data = festival_data
        self.print_debug(self.bar, f'Analysing film URL {url}')
        self.film = None
        self.title = None
        self.subtitles = None
        self.combination_urls = []
        self.film_info = None
        self.label = None
        self.state_stack = self.StateStack(self.print_debug, self.FilmsParseState.IDLE)
        self.film_property_by_label = {}

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.FilmsParseState
        match [stack.state(), tag, attrs]:
            case [_, 'title', _]:
                stack.change(state.IN_TITLE)
            case [state.IDLE, 'div', a] if a and a[0][1] == 'film-detail__the-content the-content':
                stack.push(state.IN_ARTICLE)
            case [state.IDLE, 'section', a] if a[0][1] == 'film-detail__verzamel-parent':
                stack.push(state.AWAITING_COMBINATION)
            case [state.IDLE, 'dl', a] if a and a[0][1] == 'data-list data-list--details':
                stack.change(state.IN_PROPERTIES)
            case [state.IDLE, 'footer', _]:
                stack.change(state.DONE)
                self.finish_parsing()
            case [state.IN_ARTICLE, 'p', _]:
                stack.push(state.IN_PARAGRAPH)
            case [state.IN_PARAGRAPH, 'em', _]:
                stack.push(state.IN_EMPHASIS)
            case [state.IN_PARAGRAPH, 'br', _]:
                self.add_paragraph()
            case [state.AWAITING_COMBINATION, 'h3', _]:
                stack.change(state.NEAR_COMBINATION)
            case [state.IN_COMBINATION, 'a', a] if a and a[1][0] == 'href':
                self.add_combination_url(a[1][1])
                stack.pop()
            case [state.IN_PROPERTIES, 'dt', _]:
                stack.push(state.IN_LABEL)
            case [state.AWAITING_VALUE, 'dd', _]:
                stack.change(state.IN_VALUE)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        stack = self.state_stack
        state = self.FilmsParseState
        match [stack.state(), tag]:
            case [state.IN_PARAGRAPH, 'p']:
                stack.pop()
                self.add_paragraph()
            case [state.IN_EMPHASIS, 'em']:
                stack.pop()
            case [state.IN_COMBINATION, 'em']:
                stack.pop(depth=2)
                stack.push(state.IN_COMBINATION)
            case [state.IN_ARTICLE, 'div']:
                stack.pop()
                self.set_article()
            case [state.IN_PROPERTIES, 'dl']:
                stack.change(state.DONE)
                self.finish_parsing()

    def handle_data(self, data):
        super().handle_data(data)

        stack = self.state_stack
        state = self.FilmsParseState
        match stack.state():
            case state.IN_TITLE:
                self.title = self.set_title(data)
                stack.change(state.IDLE)
            case state.IN_PARAGRAPH | state.IN_EMPHASIS:
                self.article_paragraph += data.replace('\n', ' ')
            case state.NEAR_COMBINATION if data.strip() == 'Onderdeel van dit programma':
                stack.change(state.IN_COMBINATION)
            case state.IN_LABEL:
                self.label = data
                stack.change(state.AWAITING_VALUE)
            case state.IN_VALUE:
                self.film_property_by_label[self.label] = data
                stack.pop()

    def add_combination_url(self, url):
        self.combination_urls.append(url)

    def add_properties_to_article(self):
        properties_text = '\n'.join([f'{k}: {v}' for k, v in self.film_property_by_label.items()])
        self.article += '\n\nFilm properties\n' + properties_text

    def get_duration(self):
        try:
            minutes = int(self.film_property_by_label['Duur'].split()[0])
        except KeyError:
            minutes = 0
        return datetime.timedelta(minutes=minutes)

    def get_subsection(self):
        return None if self.applying_combination else FilmUrlFinder.subsection_by_film_url[self.url]

    def get_medium_category(self):
        url_part_index = 4
        category = self.category_by_branch[self.url.split('/')[url_part_index]]
        return category

    @staticmethod
    def set_title(data):
        title = data.strip()
        unwanted_end = ' – Movies that Matter'
        if title.endswith(unwanted_end):
            title = title[:-len(unwanted_end)]
        return title

    def add_film(self):
        if self.title is None:
            ERROR_COLLECTOR.add('Cannot create a film without a title', self.url)
            return
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            ERROR_COLLECTOR.add(f"Couldn't create film from {self.title}", self.url)
        else:
            self.film.medium_category = self.get_medium_category()
            self.film.duration = self.get_duration()
            self.film.subsection = self.get_subsection()
            print(f'Adding FILM: {self.title} ({self.film.duration_str()}) {self.film.medium_category}')
            self.festival_data.films.append(self.film)
            self.add_film_info()
            self.set_global_film_properties()

    def add_film_info(self):
        self.set_description_from_article(self.film.title)
        print(f'Description:\n{self.description}')
        metadata = self.film_property_by_label
        if metadata:
            COUNTER.increase('metadata')

        self.film_info = FilmInfo(self.film.film_id, self.description, self.article,
                                  metadata=self.film_property_by_label)
        self.festival_data.filminfos.append(self.film_info)

    def set_global_film_properties(self):
        # Store the combinations urls for the current film.
        combinations_count = len(self.combination_urls)
        if combinations_count and ONLY_PARSE_SCREENED_FILMS:
            self.combination_urls_by_film_id[self.film.film_id] = self.combination_urls

        # Set the subtitles for use in the Screenings parser.
        try:
            self.subtitles = self.film_property_by_label['Ondertiteling']
        except KeyError:
            self.subtitles = ''
        if self.subtitles == 'Geen':
            self.subtitles = ''

    def finish_parsing(self):
        self.add_properties_to_article()
        self.add_film()

    @classmethod
    def apply_combinations(cls, festival_data):
        cls.applying_combination = True
        screened_films_by_combination = {}

        # Link the screened films to their combination programs.
        for (film_id, combination_urls) in cls.combination_urls_by_film_id.items():
            # Find the combination programs of the current film.
            film = festival_data.get_film_by_id(film_id)
            if film:
                COUNTER.increase('screened films')
            else:
                COUNTER.increase('no screened film')
                continue
            for combination_url in combination_urls:
                combination_film = None
                try:
                    combination_film = festival_data.get_film_by_key(None, combination_url)
                except (KeyError, ValueError) as e:
                    if combination_film:
                        raise e
                finally:
                    if not combination_film:
                        # Read film that has not been read yet.
                        get_film_by_url(festival_data, combination_url, 'UTF-8')  # TODO: derive charset.
                        combination_film = festival_data.get_film_by_key('', combination_url)
                    if not combination_film:
                        ERROR_COLLECTOR.add(f'Combination film not found', f'screened {film}')
                        break

                    if combination_film.title:
                        COUNTER.increase('combi url linked to film')
                    else:
                        ERROR_COLLECTOR.add('combi film no title', f'{combination_url}')
                        break

                # Add combination program to the list.
                append_to_dict_value(screened_films_by_combination, combination_film, film)

        # Link the combination programs to their screened films.
        for combi_film, screened_films in screened_films_by_combination.items():
            COUNTER.increase('combination films')
            combi_film_info = combi_film.film_info(festival_data)
            for screened_film in screened_films:
                link_screened_film(festival_data, screened_film, combi_film, main_film_info=combi_film_info)


class ScreeningsPageParser(HtmlPageParser):
    class ScreeningsParseState(Enum):
        IDLE = auto()
        IN_SCREENINGS = auto()
        IN_DATE = auto()
        IN_PAST = auto()
        AFTER_DATE = auto()
        IN_TIMES = auto()
        AFTER_TIMES = auto()
        IN_LOCATION = auto()
        AFTER_LOCATION = auto()
        IN_LABEL = auto()
        DONE = auto()

    nl_month_by_name: Dict[str, int] = {'mrt': 3, 'apr': 4}
    en_month_by_name: Dict[str, int] = {'Mar': 3, 'Apr': 4}

    default_by_prop = {
        'qa': '',
        'subtitles': '',
        'extra': '',
        'sold_out': True,
        'in_past': True,
    }
    restore_props_by_film = {}
    screen_id_by_film_start_dt = {}

    def __init__(self, festival_data, film, subtitles):
        super().__init__(festival_data, DEBUG_RECORDER, 'S')
        self.film = film
        self.subtitles = subtitles
        self.print_debug(self.bar, f"Analysing screenings of {film}, {film.url}")
        self.screening_nr = 0
        self.screen_name = None
        self.start_date = None
        self.qa = None
        self.end_dt = None
        self.start_dt = None
        self.extra = None
        self.audience = None
        self.screen = None
        self.sold_out = None
        self.in_past = None

        self.init_screening_data()
        self.state_stack = self.StateStack(self.print_debug, self.ScreeningsParseState.IDLE)

    def feed(self, data):
        if self.film is None:
            ERROR_COLLECTOR.add('No film object when parsing screenings', "")
        else:
            super().feed(data)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.ScreeningsParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'div', a] if a and a[0][1] == 'film-detail__viewings tile-side':
                stack.change(state.IN_SCREENINGS)
            case [state.IN_SCREENINGS, 'div', a] if a and a[0][1] == 'tile-date':
                stack.push(state.IN_DATE)
            case [state.IN_SCREENINGS, 'div', a] if a and a[0][1] == 'tile-day date-in-past':
                self.in_past = True
                stack.push(state.IN_PAST)
            case [state.IN_SCREENINGS, 'div', a] if a and a[0][1].startswith('tile-time  '):
                stack.push(state.AFTER_DATE)
            case [state.AFTER_DATE, 'a', a] if a and a[0][1] == 'time':
                self.read_screen_if_needed(attrs[1][1])
                stack.change(state.IN_TIMES)
            case [state.AFTER_TIMES, 'p', a] if a and a[0][1] == 'location':
                stack.change(state.IN_LOCATION)
            case [state.AFTER_TIMES, 'span', a] if a and a[0][1] == 'label uitverkocht':
                self.sold_out = True
            case [state.AFTER_LOCATION, 'span', a] if a and a[0][1] == 'label label__verdieping':
                self.qa = 'met verdieping'
            case [state.AFTER_LOCATION, 'span', a] if a and a[0][1] == 'label':
                stack.push(state.IN_LABEL)
            case [state.IN_SCREENINGS, 'script', a] if a and attrs[0][1] == 'application/json':
                stack.change(state.DONE)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        if self.state_stack.state_is(self.ScreeningsParseState.AFTER_LOCATION) and tag == 'div':
            self.add_screening_if_possible()
            self.state_stack.pop()

    def handle_data(self, data):
        super().handle_data(data)

        stack = self.state_stack
        state = self.ScreeningsParseState
        match stack.state():
            case state.IN_DATE:
                self.start_date = self.parse_date(data)
                stack.change(state.AFTER_DATE)
            case state.IN_PAST:
                stack.change(state.IN_DATE)
            case state.IN_TIMES:
                self.set_screening_times(data)
                stack.change(state.AFTER_TIMES)
            case state.IN_LOCATION:
                self.set_screen(data)
                stack.change(state.AFTER_LOCATION)
            case state.IN_LABEL:
                self.parse_label(data)
                stack.pop()

    def init_screening_data(self):
        self.audience = 'publiek'
        self.extra = ''
        self.qa = ''
        self.screen_name = None
        self.screen = None
        self.start_dt = None
        self.end_dt = None
        self.sold_out = False
        self.in_past = False

    def add_screening_if_possible(self):
        if self.screen:
            self.add_mtmf_screening()
        else:
            print(f'No screening added, screen must be recovered.')
            if not self.sold_out and not self.in_past:
                ERROR_COLLECTOR.add('Screening has no screen', f'Film {self.film}')
            self.init_screening_data()

    def add_mtmf_screening(self):
        # Maintain statistics.
        self.maintain_screening_stats(self.screen)

        # Add a screening based on the parsed data.
        kwargs = {
            'qa': self.qa,
            'subtitles': self.subtitles,
            'extra': self.extra,
            'audience': self.audience,
            'sold_out': self.sold_out,
            'display': DISPLAY_ADDED_SCREENING,
        }
        self.add_screening_from_fields(self.film, self.screen, self.start_dt, self.end_dt, **kwargs)

        # Initialize the next round of parsing.
        self.init_screening_data()

    @classmethod
    def add_screening_from_props(cls, festival_data, film, screen, start_dt, end_dt,
                                 qa='', extra='', subtitles='', audience=None, sold_out=None):
        # Maintain statistics.
        cls.maintain_screening_stats(screen)

        # Create a screening based on the parsed data.
        kwargs = {
            'qa': qa,
            'subtitles': subtitles,
            'extra': extra,
            'audience': audience,
            'sold_out': sold_out,
        }
        screening = Screening(film, screen, start_dt, end_dt, **kwargs)
        print(f'{"Sold out" if sold_out else "Past"} screening recovered: {str(screening)}.')

        # Add the screening.
        festival_data.screenings.append(screening)

    @classmethod
    def maintain_screening_stats(cls, screen):
        COUNTER.increase('screenings')
        if screen.theater.city.name != FESTIVAL_CITY:
            COUNTER.increase('not in dh')

    def parse_date(self, data):
        items = data.split()  # zo 23 mrt
        day = int(items[1])
        month = self.nl_month_by_name[items[2]]
        year = FESTIVAL_YEAR
        return datetime.date(year, month, day)

    def parse_label(self, data):
        if data == 'Invitation only':
            self.audience = 'genodigden'

    def set_screening_times(self, data):
        items = data.split()  # 10:15  - 11:48
        start_time = datetime.time.fromisoformat(items[0])
        try:
            end_time = datetime.time.fromisoformat(items[2])
        except IndexError:
            try:
                start_dt = datetime.datetime.combine(self.start_date, start_time, tzinfo=None)
                end_time = datetime.datetime.time(start_dt + self.film.duration)
            except TypeError:
                COUNTER.increase('end time not reconstructed')
                end_time = start_time
            COUNTER.increase('no end time')
        self.start_dt = datetime.datetime.combine(self.start_date, start_time)
        end_date = self.start_date if end_time > start_time else self.start_date + datetime.timedelta(days=1)
        self.end_dt = datetime.datetime.combine(end_date, end_time)

    def set_screen(self, data):
        items = data.split(',')    # Den Haag, Filmhuis Den Haag
        city = items[0] or FESTIVAL_CITY
        theater = items[1].strip()
        if self.sold_out or self.in_past:
            COUNTER.increase('sold out' if self.sold_out else 'in past')
            props = {
                'city': city,
                'theater': theater,
                'start_dt': self.start_dt,
                'end_dt': self.end_dt,
                'qa': self.qa,
                'subtitles': self.subtitles,
                'extra': self.extra,
                'audience': self.audience,
                'sold_out': self.sold_out,
                'in_past': self.in_past,
            }
            append_to_dict_value(self.restore_props_by_film, self.film, props)
        else:
            screen_name = self.screen_name if self.screen_name else theater
            if screen_name:
                self.screen = self.festival_data.get_screen(city, screen_name, theater)
            else:
                self.print_debug('NO THEATER', f'city={city}, theater={theater}, screen={screen_name}')
                COUNTER.increase('no theater')
        if city != FESTIVAL_CITY:
            self.print_debug('OTHER CITY', f'city={city}, theater={theater}, screen={self.screen}')

    @classmethod
    def recover_sold_out_screens(cls, festival_data):
        props_list_by_film = {}

        for org_film, props_list in cls.restore_props_by_film.items():
            # Use the combination film if the original film is part of a combination program.
            film_info = org_film.film_info(festival_data)
            combi_films = film_info.combination_films
            film = combi_films[0] if combi_films else org_film  # No parts in multiple combi programs in MTMF.

            # Set the screenings properties for the resulting film.
            if film in props_list_by_film:
                if props_list_by_film[film] != props_list:
                    DEBUG_RECORDER.add(
                        'Different screenings in combi parts\n'
                        f'{film}, \n\tprops {props_list_by_film[film]}, \n\tnew   {props_list}')
                    cls.keep_common_props(props_list_by_film[film], props_list, film)
            else:
                props_list_by_film[film] = props_list

        # Get screening data from saved file.
        cls.get_screens_from_file(festival_data, props_list_by_film)

        # Recover the screens.
        for film, props_list in props_list_by_film.items():
            for props in props_list:
                cls.recover_sold_out_screen(festival_data, film, props)

    @classmethod
    def recover_sold_out_screen(cls, festival_data, film, props):
        city = props['city']
        theater = props['theater']
        start_dt = props['start_dt']
        end_dt = props['end_dt']
        qa = props['qa']
        subtitles = props['subtitles']
        extra = props['extra']
        audience = props['audience']
        sold_out = props['sold_out']
        in_past = props['in_past']

        # Get the screen from file.
        screen = cls.try_get_screen_from_file(festival_data, film, start_dt)

        # Recover the screening.
        film_screenings = film.screenings(festival_data)
        list_ = [s for s in film_screenings if s.start_datetime == start_dt]
        if list_:
            screening = list_[0]  # No combi parts in MTMF that are screened in multiple programs.
            screening.sold_out = sold_out
            print(f"screening {str(screening)} updated. {sold_out=}, {in_past=}")
        elif screen:
            args = [festival_data, film, screen, start_dt, end_dt]
            kwargs = {'qa': qa, 'extra': extra, 'subtitles': subtitles, 'audience': audience, 'sold_out': sold_out}
            cls.add_screening_from_props(*args, **kwargs)
        else:
            ERROR_COLLECTOR.add('Screen not recovered',
                                f'{film}: {city=}, {theater=}, {start_dt.isoformat(sep=" ")}')
            COUNTER.increase('screen not recovered')

    @classmethod
    def keep_common_props(cls, recovery_props_list, new_props_list, film):
        """
        Set screening properties of combi that differ from parts to predefined defaults.
        TODO: Consider to display screening details of screened films individually in the planner.
        :param recovery_props_list: List of property dicts of the combination screening
        :param new_props_list: List of property dicts of the next combi screening part
        :param film: Film of the mentioned screenings
        :return: None
        """
        for i in range(len(recovery_props_list)):
            for prop, default in cls.default_by_prop.items():
                if new_props_list[i][prop] != recovery_props_list[i][prop]:
                    props = recovery_props_list[i]
                    COUNTER.increase('combi screening props fixed')
                    DEBUG_RECORDER.add(
                        f"\t{film}: {props['theater'], props['start_dt']}: Setting {prop} to '{default}'")
                    recovery_props_list[i][prop] = default

    @classmethod
    def try_get_screen_from_file(cls, festival_data, film, start_dt):
        try:
            screen = cls.get_screen_from_file(festival_data, film, start_dt)
        except FileNotFoundError:
            screen = None

        return screen

    @classmethod
    def get_screens_from_file(cls, festival_data, props_list_by_film):
        """Build a dictionary from saved screenings to recovers screens."""
        screenings_filename = os.path.basename(festival_data.screenings_file)
        screenings_path = os.path.join(FILE_KEEPER.interface_dir, screenings_filename)
        film_id_csv_field = 0
        screen_id_csv_field = 1
        start_time_csv_field = 2

        # Fill the search keys from the screenings properties by film dict.
        cls.screen_id_by_film_start_dt = {}
        for film, props_list in props_list_by_film.items():
            for props in props_list:
                key = (film.film_id, props['start_dt'].isoformat(sep=' '))
                cls.screen_id_by_film_start_dt[key] = None

        # Read the saved screenings as to fill the values for the found keys.
        with open(screenings_path, newline='') as csvfile:
            screenings_reader = csv.reader(csvfile, delimiter=';', quotechar='"')
            next(screenings_reader)     # Skip header.
            for row in screenings_reader:
                film_id = int(row[film_id_csv_field])
                start_date_str = row[start_time_csv_field]
                if (film_id, start_date_str) in cls.screen_id_by_film_start_dt.keys():
                    screen_id = int(row[screen_id_csv_field])
                    cls.screen_id_by_film_start_dt[(film_id, start_date_str)] = screen_id

    @classmethod
    def get_screen_from_file(cls, festival_data, film, start_dt):
        screen_id = cls.screen_id_by_film_start_dt[(film.film_id, start_dt.isoformat(sep=' '))]
        screen = festival_data.get_screen_by_id(screen_id)
        COUNTER.increase('screen reconstructed')
        return screen

    def read_screen_if_needed(self, url):
        self.screening_nr += 1
        netloc = get_netloc(url)
        if netloc in [MTMF_HOSTNAME, MTMF_TICKETS_HOSTNAME]:
            self.read_screen(url)

    def read_screen(self, url):
        locations_file_format = os.path.join(FILE_KEEPER.webdata_dir, "screenings_{:03d}_{:02d}.html")
        locations_file = locations_file_format.format(self.film.film_id, self.screening_nr)
        url_file = UrlFile(url, locations_file, ERROR_COLLECTOR, DEBUG_RECORDER)
        comment_at_download = f'Downloading shopping cart site {url}'
        try:
            locations_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
        except ValueError:
            pass
        else:
            if locations_html is not None:
                shopping_cart_parser = ShoppingCartPageParser(self.festival_data, self.film, self.screening_nr)
                shopping_cart_parser.feed(locations_html)
                self.screen_name = shopping_cart_parser.current_screen


class ShoppingCartPageParser(HtmlPageParser):
    class ShoppingCartState(Enum):
        IDLE = auto()
        IN_SCREEN = auto()
        IN_ORDER = auto
        DONE = auto()

    def __init__(self, festival_data, film, sequence_nr):
        super().__init__(festival_data, DEBUG_RECORDER, 'SC')
        self.film = film
        self.sequence_nr = sequence_nr
        self.state_stack = self.StateStack(self.print_debug, self.ShoppingCartState.IDLE)
        self.current_screen = None

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        if self.state_stack.state_is(self.ShoppingCartState.IDLE):
            match [tag, attrs]:
                case ['div', a] if a and a[0][1] == 'at-show-property at-show-location':
                    self.state_stack.change(self.ShoppingCartState.IN_SCREEN)
                case ['iframe', a] if len(a) > 5 and a[1][1] == 'order__iframe order__iframe--crossmarx':
                    self.state_stack.change(self.ShoppingCartState.IN_ORDER)
                    details_url = attrs[5][1]
                    self.get_theater_screen(details_url)
                    self.state_stack.change(self.ShoppingCartState.DONE)

    def handle_data(self, data):
        super().handle_data(data)

        if self.state_stack.state_is(self.ShoppingCartState.IN_SCREEN):
            self.current_screen = data.strip()
            self.state_stack.change(self.ShoppingCartState.DONE)

    def get_theater_screen(self, url):
        details_file_format = os.path.join(FILE_KEEPER.webdata_dir, "details_{:03d}_{:02d}.html")
        details_file = details_file_format.format(self.film.film_id, self.sequence_nr)
        url_file = UrlFile(url, details_file, ERROR_COLLECTOR, DEBUG_RECORDER)
        comment_at_download = f'Downloading site {url}'
        try:
            details_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
        except ValueError:
            pass
        else:
            if details_html is not None:
                theater_screen_parser = TheaterScreenPageParser(self.festival_data, self.film, url)
                theater_screen_parser.feed(details_html)
                self.current_screen = theater_screen_parser.current_screen


class TheaterScreenPageParser(HtmlPageParser):
    class ScreensParseState(Enum):
        IDLE = auto()
        IN_SCREENING_LOCATION = auto()
        DONE = auto()

    def __init__(self, festival_data, film, url):
        super().__init__(festival_data, DEBUG_RECORDER, 'TS')
        self.print_debug(self.bar, f'Analysing screening location of FILM {film}, {url}')
        self.stateStack = self.StateStack(self.print_debug, self.ScreensParseState.IDLE)
        self.current_screen = None

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        if self.stateStack.state_is(self.ScreensParseState.IDLE) and tag == 'div' and len(attrs) > 0:
            if attrs[0][1] == 'at-show-property at-show-location':
                self.stateStack.change(self.ScreensParseState.IN_SCREENING_LOCATION)

    def handle_data(self, data):
        super().handle_data(data)

        if self.stateStack.state_is(self.ScreensParseState.IN_SCREENING_LOCATION):
            self.current_screen = data.strip()
            self.stateStack.change(self.ScreensParseState.DONE)


class SubsectionDescriptionParser(HtmlPageParser):
    class DescriptionParseState(Enum):
        IDLE = auto()
        DONE = auto()

    def __init__(self, festival_data, subsection):
        super().__init__(festival_data, DEBUG_RECORDER, 'SUD')
        self.subsection = subsection
        self.print_debug(self.bar, f'Finding description of subsection {subsection}')
        self.state_stack = self.StateStack(self.print_debug, self.DescriptionParseState.IDLE)
        self.subsection_description = None

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.DescriptionParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'meta', a] if a[0] == ('property', 'og:description'):
                self.subsection_description = a[1][1]
                stack.change(state.DONE)


class MtmfData(FestivalData):

    def __init__(self, planner_data_dir):
        super().__init__(FESTIVAL_CITY, planner_data_dir)

    def film_key(self, title, url):
        return url

    def film_can_go_to_planner(self, film_id):
        return True

    def screening_can_go_to_planner(self, screening):
        can_go = super().screening_can_go_to_planner(screening)
        return can_go and screening.screen.theater.city.name == FESTIVAL_CITY


if __name__ == "__main__":
    main()
