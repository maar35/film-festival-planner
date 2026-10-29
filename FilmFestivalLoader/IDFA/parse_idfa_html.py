#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load films, film information, screens and screenings from the IDFA 2020
website.

Created on Wed Nov  4 20:36:18 2020

@author: maarten
"""
import csv
import datetime
import os
import re
from enum import Enum, auto
from typing import Dict

from Shared.application_tools import ErrorCollector, DebugRecorder, comment, Counter, broadcast, Config
from Shared.parse_tools import FileKeeper, HtmlPageParser, try_parse_festival_sites
from Shared.planner_interface import FestivalData, Screening, FilmInfo, ScreenedFilm, get_screen_from_parse_name, \
    AUDIENCE_PUBLIC, Film, CATEGORY_FIELD_FILMS, CATEGORY_FIELD_COMBINATIONS, CATEGORY_FIELD_EVENTS
from Shared.web_tools import UrlFile

FESTIVAL = 'IDFA'
FESTIVAL_CITY = 'Amsterdam'
FESTIVAL_YEAR = 2026

DEBUGGING = True
TRY_AZ_PAGES = False
ALWAYS_DOWNLOAD = True
ALWAYS_DOWNLOAD_FILMS = True
DISPLAY_ADDED_SCREENING = False
USE_NEWS_PAGES = True

# Files.
FILE_KEEPER = FileKeeper(FESTIVAL, FESTIVAL_YEAR)
LOCAL_CONFIG = Config(FILE_KEEPER.local_config_file).config
AZ_PAGE_COUNT = 11
NEWS_PAGE_COUNT = 1     # Should be 2 but that doesn't work (yet).
COMBI_DATA_PATH = os.path.join(FILE_KEEPER.plandata_dir, 'combination_data.csv')

# URL information.
FESTIVAL_HOSTNAME = 'https://festival.idfa.nl'

# Application tools.
ERROR_COLLECTOR = ErrorCollector()
DEBUG_RECORDER = DebugRecorder(FILE_KEEPER.debug_file, active=DEBUGGING)
COUNTER = Counter()

# Config items.
LANGUAGE_BY_TITLE = LOCAL_CONFIG['title_languages']
PAGE_2_THEMES = LOCAL_CONFIG['page_2_themes']
COLOR_BY_SECTION_ID = LOCAL_CONFIG['section_colors']
IGNORE_SCREENING_FILMS = LOCAL_CONFIG['ignore_screenings_films']

CATEGORY_BY_STR = {
    'film': CATEGORY_FIELD_FILMS,
    'composition': CATEGORY_FIELD_COMBINATIONS,
    'event': CATEGORY_FIELD_EVENTS,
}


def main():
    # Initialize a festival data object.
    comment('Creating festival data object.')
    festival_data = IdfaData(FILE_KEEPER.plandata_dir)

    # Setup counters.
    setup_counters()

    # Take known title languages into account.
    add_title_languages()

    # Try parsing the websites.
    try_parse_festival_sites(parse_idfa_sites, festival_data, ERROR_COLLECTOR, DEBUG_RECORDER, FESTIVAL, COUNTER)


def setup_counters():
    COUNTER.start('film URLs')
    COUNTER.start('films')
    COUNTER.start('duplicate films')
    COUNTER.start('theme urls')
    COUNTER.start('news themes')
    COUNTER.start('titles found')
    COUNTER.start('pathways')
    COUNTER.start('sections')
    COUNTER.start('subsections')
    COUNTER.start('film infos')
    COUNTER.start('meta dicts')
    COUNTER.start('multi day')
    COUNTER.start('funny location')
    COUNTER.start('public screening')
    COUNTER.start('ignore screenings')
    COUNTER.start('combinations')
    COUNTER.start('screening parse error')
    COUNTER.start('unexpected sections')
    COUNTER.start('unexpected theme part title')
    COUNTER.start('empty html')

    # Counters for A-Z parsing.
    if TRY_AZ_PAGES:
        COUNTER.start('az-counters')


def add_title_languages():
    Film.language_by_title |= LANGUAGE_BY_TITLE


def get_readable_theme_str(pathway_url):
    index = -2 if pathway_url.endswith('/') else -1
    pathway_str = pathway_url.split('/')[index]
    return pathway_str


def parse_idfa_sites(festival_data):
    if TRY_AZ_PAGES:
        comment('Trying new AZ pege(s)')
        load_az_pages(festival_data)

    # comment(f'Parsing combination films.')
    # get_combination_films(festival_data)

    comment('Parsing news pages.')
    get_all_theme_parts(festival_data, 'NewsPath', 'news.html')

    # comment('Parsing section pages.')
    # get_theme_parts(festival_data, 'SectionsPath', 'sections.html')
    #
    # comment('Parsing pathway pages.')
    # get_theme_parts(festival_data, 'PathwaysPath', 'pathways.html')

    # comment(f'Write combination data to {COMBI_DATA_PATH}.')
    # CombinationsKeeper.write_combination_data(festival_data)
    # print(f'{len(CombinationsKeeper.combination_props_list)} combination date records written.')

    comment(f'Done parsing {FESTIVAL}{FESTIVAL_YEAR} pages.')


def load_az_pages(festival_data):
    az_path = LOCAL_CONFIG['Paths']['AzPath']
    az_url_base = FESTIVAL_HOSTNAME + az_path
    for page_number in range(1, AZ_PAGE_COUNT + 1):
        debug_file = os.path.join(os.path.dirname(FILE_KEEPER.debug_file), f'debug_{page_number:02d}.txt')
        debugger = DebugRecorder(debug_file)
        az_file = FILE_KEEPER.az_file(page_number)
        az_url = az_url_base + f'&page={page_number}'
        url_file = UrlFile(az_url, az_file, ERROR_COLLECTOR, debugger)
        az_html = url_file.get_text(comment_at_download='Downloading AZ page.', always_download=ALWAYS_DOWNLOAD)
        if az_html:
            comment(f'Downloaded AZ page #{page_number}, encoding={url_file.encoding}, bytes={len(az_html)}')
            AzPageParser(festival_data, debugger).feed(az_html)
        debugger.write_debug()


def get_combination_films(festival_data):
    for title, path in LOCAL_CONFIG['UrlpathByCombinationTitle'].items():
        url = FESTIVAL_HOSTNAME + path
        get_film_from_theme_part_page(festival_data, title, url, 'combinations/', use_section_keeper=False)


def get_all_theme_parts(festival_data, theme_path_key, target_file):
    """Read the sub-themes from the given theme base site."""
    theme_path = LOCAL_CONFIG['Paths'][theme_path_key]
    for page_nr_ in range(NEWS_PAGE_COUNT):
        page_nr = page_nr_ + 1
        broadcast(f'Getting "{get_readable_theme_str(theme_path)}" parts page {page_nr}', DEBUG_RECORDER)
        get_theme_parts(festival_data, theme_path, target_file, page_nr)


def get_theme_parts(festival_data, theme_path, target_file_, page_nr):
    """Read the sub-themes from the given theme site page."""
    sleep_secs = 0
    theme_url = FESTIVAL_HOSTNAME + theme_path + f'?page={page_nr}'
    theme_str = target_file_.split('.')[0]
    target_file = FILE_KEEPER.numbered_webdata_file(theme_str, page_nr)
    url_file = UrlFile(theme_url, target_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
    comment_ = f'Downloading "{theme_str}" theme from {theme_url}'
    if page_nr > 1:
        sleep_secs = 2
        comment(f'Sleeping {sleep_secs} seconds')
    theme_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_, sleep_secs=sleep_secs)
    if theme_html:
        comment(f'Analysing "{theme_str}" theme page {page_nr}, encoding={url_file.encoding}')
        ThemePartsPageParser(festival_data, theme_str).feed(theme_html)


def get_films_by_theme(festival_data, theme_urls, theme_str):
    """Read the films from each of the given theme URLs."""
    comment(f'Finding films with "{theme_str}" theme ({len(theme_urls)})')
    for i, theme_url in enumerate(theme_urls):
        theme_file = FILE_KEEPER.numbered_webdata_file(theme_str, i)
        url_file = UrlFile(theme_url, theme_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
        comment_ = f'Downloading {theme_url} to find the "{theme_str}" films'
        theme_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_)
        if theme_html:
            comment(f'Analysing "{theme_str}" item {i}, encoding={url_file.encoding}')
            match theme_str:
                case('news'):
                    ThemesFromNewsPageParser(festival_data, theme_url).feed(theme_html)
                case('sections'):
                    FilmsFromSectionPageParser(festival_data, theme_url).feed(theme_html)
                case(_):
                    FilmsFromPathwayPageParser(festival_data, theme_url).feed(theme_html)


def get_film_from_theme_part_page(festival_data, film_title, film_url, theme_part_url, use_section_keeper=True):
    """Store the sections of a film that was found in the given theme page."""
    # Check if the film is already loaded.
    film_id = None
    try:
        film = festival_data.get_film_by_key(film_title, film_url)
    except KeyError as e:
        broadcast('New film.', DEBUG_RECORDER)
        raise KeyError(f'{e} - new film')
    except ValueError as e:
        broadcast('Known film not yet parsed.', DEBUG_RECORDER)
        raise ValueError(f'{e} - Unparsed know film')
    else:
        comment(f'Existing film {film_title}, as expected.')
        film_id = film.film_id
        # comment(f'Existing film {film_title} not parsed.')
        # return

    # Load the pathway film.
    theme_str = get_readable_theme_str(theme_part_url)
    comment(f'Parsing film "{film_title}" with theme "{theme_str}".')
    # TODO in 2026: Stop using a "section keeper" to bookkeep film ID's.
    if film_id:
        pass
    elif use_section_keeper:
        msg = f'Used SectionsKeeper plus trying to create a new film for title {film_title}'
        broadcast(msg, DEBUG_RECORDER)
        raise ValueError(msg)
        # film_id = SectionsKeeper.get_new_film_id(film_url)
    else:
        msg = f'Trying to crate a new film for title {film_title}, stopping'
        broadcast(msg, DEBUG_RECORDER)
        raise KeyError(msg)
        # film_id = festival_data.new_film_id(festival_data.film_key(film_title, film_url)) + 1000
    theme_film_file = FILE_KEEPER.film_webdata_file(film_id)
    url_file = UrlFile(film_url, theme_film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
    comment_at_download = f'Downloading "{theme_str}" film "{film_title}" data from {film_url}'
    download = ALWAYS_DOWNLOAD or ALWAYS_DOWNLOAD_FILMS
    film_html = url_file.get_text(always_download=download, comment_at_download=comment_at_download)
    if film_html:
        message = (f'Analysing page of "{film_title}" from theme "{theme_str}", '
                   f'parsed from "{theme_film_file}" encoding={url_file.encoding}')
        broadcast(message, DEBUG_RECORDER)
        FilmPageParser(festival_data, theme_str, film_title, film_url).feed(film_html)
        # if use_section_keeper:
        #     FilmPageParser(festival_data, theme_str, film_title, film_url).feed(film_html)
        # else:
        #     CombinationFilmPageParser(festival_data, theme_str, film_title, film_url).feed(film_html)


class AzPageParser(HtmlPageParser):
    class AzParseState(Enum):
        IDLE = auto()
        IN_ARTICLE = auto()

    def __init__(self, festival_data, debugger=None):
        super().__init__(festival_data, debugger or DEBUG_RECORDER, 'AZ')
        self.sorting_from_site = False
        self.film = None
        self.state_stack = self.StateStack(self.print_debug, self.AzParseState.IDLE)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        if self.state_stack.state_is(self.AzParseState.IDLE) and tag == 'article':
            self.state_stack.push(self.AzParseState.IN_ARTICLE)
            COUNTER.increase('az-counters')

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        if self.state_stack.state_is(self.AzParseState.IN_ARTICLE) and tag == 'article':
            self.state_stack.pop()


class ThemePartsPageParser(HtmlPageParser):
    """Parse the given theme overview page for theme URLs."""
    class ThemePartsParseState(Enum):
        AWAITING_URL = auto()
        AWAITING_THEME_PART_TITLE = auto()
        IN_THEME_PART_TITLE = auto()
        AFTER_THEME_PART_TITLE = auto()
        DONE = auto()

    subsection_by_theme_url = {}

    @classmethod
    def get_subsection_(cls, theme_url):
        subsection = None
        try:
            subsection = cls.subsection_by_theme_url[theme_url]
        except KeyError as e:
            broadcast(f'No subsection known for theme URL {theme_url} ({str(e)})', DEBUG_RECORDER)
        return subsection

    def __init__(self, festival_data, theme_str):
        super().__init__(festival_data, DEBUG_RECORDER, 'TP')
        self.theme_str = theme_str
        self.theme_urls = []
        self.theme_name_by_url = {}
        self.theme_url = None
        self.theme_name = None
        self.print_debug(self.headed_bar(header=f'THEME {theme_str}'))
        self.state_stack = self.StateStack(self.print_debug, self.ThemePartsParseState.AWAITING_URL)

    def feed(self, data):
        super().feed(data)
        page_2_urls = self._add_page_2_themes()
        theme_urls = self.theme_urls + page_2_urls
        get_films_by_theme(self.festival_data, theme_urls, self.theme_str)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.ThemePartsParseState
        match [stack.state(), tag, attrs]:
            case [state.AWAITING_URL, 'a', a] if len(a) > 1 and a[1][1].startswith('/section/'):
                COUNTER.increase('unexpected sections')
            case [state.AWAITING_URL, 'a', a] if a[0][0] == 'href' and a[0][1].startswith('/en/news/') and len(a[0][1].split('/')) > 4:
                self.theme_url = FESTIVAL_HOSTNAME + a[0][1]
                self.theme_urls.append(self.theme_url)
                COUNTER.increase('theme urls')
                stack.push(state.AWAITING_THEME_PART_TITLE)
            case [state.AWAITING_THEME_PART_TITLE, 'img', a] if a and a[0][0] == 'alt':
                COUNTER.increase('unexpected theme part title')
            case [state.AWAITING_THEME_PART_TITLE, 'h2', _]:
                stack.push(state.IN_THEME_PART_TITLE)
            case [state.AWAITING_URL, 'footer', _]:
                stack.change(state.DONE)
            case [_, _, _]:
                pass

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        stack = self.state_stack
        state = self.ThemePartsParseState
        match [stack.state(), tag]:
            case [state.AWAITING_THEME_PART_TITLE, 'img' | 'h2']:
                stack.change(state.AFTER_THEME_PART_TITLE)
            case [state.AFTER_THEME_PART_TITLE, 'a']:
                self._init_theme_part()
                stack.pop()
            case [_, _, _]:
                pass

    def handle_data(self, data):
        super().handle_data(data)

        stack = self.state_stack
        state = self.ThemePartsParseState
        match stack.state():
            case state.IN_THEME_PART_TITLE:
                self.theme_name = data.strip()
                _ = SectionsKeeper.add_section_props(self.theme_name)
                self.theme_name_by_url[self.theme_url] = self.theme_name
                self._add_section()
                COUNTER.increase('titles found')
                stack.pop()

    def _init_theme_part(self):
        self.theme_url = None
        self.theme_name = None

    def _add_section(self):
        DEBUG_RECORDER.add(f'ADD SECTION {self.theme_name}, {self.theme_url}')
        section = self.festival_data.get_section(self.theme_name, color_by_id=COLOR_BY_SECTION_ID)
        if section:
            subsection = self.festival_data.get_subsection(self.theme_name, self.theme_url, section)
            self.subsection_by_theme_url[self.theme_url] = subsection
            COUNTER.increase('subsections')
            broadcast(f'Added subsection "{str(subsection)}" of section "{section}"', DEBUG_RECORDER)

    def _add_page_2_themes(self):
        keys = PAGE_2_THEMES.keys()
        subsection_urls = []
        for key in keys:
            subsection_url = PAGE_2_THEMES[key]['url']
            subsection_description = PAGE_2_THEMES[key]['description']
            section_id = PAGE_2_THEMES[key]['section_id']
            section = self.festival_data.section_by_id[section_id]
            subsection = self.festival_data.get_subsection(key, subsection_url, section)
            subsection.description = subsection_description
            self.subsection_by_theme_url[subsection_url] = subsection
            subsection_urls.append(subsection_url)
            COUNTER.increase('subsections')
        return subsection_urls


class ThemesFromNewsPageParser(HtmlPageParser):
    """Read the films from a News Theme page."""
    class NewsThemesParsState(Enum):
        IDLE = auto()
        AWAITING_TARGET_BUTTON = auto()
        PARSING_FILMS = auto()
        DONE = auto()

    def __init__(self, festival_data, news_url):
        super().__init__(festival_data, DEBUG_RECORDER, 'TFN')

        self.news_url = news_url
        self.subsection = ThemePartsPageParser.get_subsection_(news_url)
        self.theme_nr = 0
        self.page_nr = None

        msg = f'{self.debug_prefix} Getting news themes from "{self.news_url}'
        broadcast(msg, DEBUG_RECORDER)
        self.state_stack = self.StateStack(self.print_debug, self.NewsThemesParsState.AWAITING_TARGET_BUTTON)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.NewsThemesParsState
        match [stack.state(), tag, attrs]:
            case [state.AWAITING_TARGET_BUTTON, 'a', a] if a and a[0] == ('target', '_blank'):
                theme_url = a[1][1] if a[1][0] == 'href' else a[2][1]
                if theme_url.startswith(f'{FESTIVAL_HOSTNAME}/en/section/'):
                    stack.push(state.PARSING_FILMS)
                    self._parse_films(theme_url)
                    stack.pop()

    def _parse_films(self, url):
        self.theme_nr += 1
        prefix = 'news'
        film_file = FILE_KEEPER.numbered_webdata_file(prefix, self.theme_nr)
        url_file = UrlFile(url, film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
        comment_at_download = f'Downloading {prefix} page: {url}, encoding: {url_file.encoding}'
        theme_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
        if theme_html:
            COUNTER.increase('news themes')
            FilmsFromNewsPageParser(self.festival_data, url, self.subsection).feed(theme_html)
        else:
            broadcast(comment_at_download + ' failed', DEBUG_RECORDER)
            COUNTER.increase('empty html')


class FilmsFromNewsPageParser(HtmlPageParser):
    """Laad the films from given pathway URL. Find the sections in each film."""
    class NewsFilmsParseState(Enum):
        IDLE = auto()
        AWAITING_SECTION_TITLE = auto()
        IN_SECTION_NAME = auto()
        AWAITING_SECTION_DESCRIPTION = auto()
        IN_SECTION_DESCRIPTION_ALT = auto()
        IN_SECTION_DESCRIPTION = auto()
        AWAITING_FILM = auto()
        IN_FILM = auto()
        IN_FILM_URL = auto()
        IN_FILM_TITLE = auto()
        IN_DIRECTOR = auto()
        IN_YEAR = auto()
        IN_LENGTH = auto()
        AWAITING_DATA_META = auto()
        IN_FILM_DESCRIPTION = auto()
        DONE = auto()

    def __init__(self, festival_data, section_url, subsection):
        super().__init__(festival_data, DEBUG_RECORDER, 'FFN')
        self.section_url = section_url
        self.section_name = None
        self.section_description = None
        self.readable_theme_str = get_readable_theme_str(self.section_url)

        # Initialize film properties.
        self.film_url = None
        self.film_title = None
        self.duration = None
        self.film_description = None
        self.subsection = subsection
        self.film_property_by_label = None
        self.metadata_key = None

        self.draw_headed_bar(self.readable_theme_str, bar_base='=')
        self.state_stack = self.StateStack(self.print_debug, self.NewsFilmsParseState.IDLE)

    def feed(self, data):
        super().feed(data)
        self.draw_headed_bar(f'{self.readable_theme_str} done', bar_base='=')
        print()

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.NewsFilmsParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'article', _]:
                self._init_film_props()
                stack.push(state.AWAITING_FILM)
            case [state.AWAITING_FILM, 'a', a] if a and a[0][0] == 'href' and a[0][1].startswith('/en/film/'):
                self.film_url = FESTIVAL_HOSTNAME + a[0][1]
                broadcast(f'Found film url of {get_readable_theme_str(self.film_url)}', DEBUG_RECORDER)
                COUNTER.increase('film URLs')
                stack.push(state.IN_FILM)
            case [state.IN_FILM, 'h2', _]:
                stack.change(state.IN_FILM_TITLE)
            case [state.AWAITING_DATA_META, 'div', a] if a and a[0] == ('data-meta', 'director'):
                stack.push(state.IN_DIRECTOR)
            case [state.AWAITING_DATA_META, 'div', a] if a and a[0] == ('data-meta', 'year'):
                stack.push(state.IN_YEAR)
            case [state.AWAITING_DATA_META, 'div', a] if a and a[0] == ('data-meta', 'length'):
                stack.push(state.IN_LENGTH)
            case [state.AWAITING_DATA_META, 'div', a] if len(a) > 1 and a[1][1].endswith('-Body-Description'):
                stack.push(state.IN_FILM_DESCRIPTION)
            case [state.IDLE, 'a', a] if a and a[0] == ('target', '_blank'):
                stack.change(state.DONE)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        stack = self.state_stack
        state = self.NewsFilmsParseState
        match [stack.state(), tag]:
            case [state.IN_FILM_TITLE, 'h2']:
                stack.change(state.AWAITING_DATA_META)
            case [state.IN_DIRECTOR | state.IN_YEAR | state.IN_LENGTH | state.IN_FILM_DESCRIPTION, 'div']:
                stack.pop()
            case [state.AWAITING_DATA_META, 'a']:
                stack.pop()
            case [_, 'article']:
                stack.pop()
                comment(f'Ready to create film "{self.film_title}" from {self.film_url}')
                self._add_film()
                self.print_debug('End of article', f'stack is {str(stack)}')
                stack.change(state.IDLE)

    def handle_data(self, data):
        super().handle_data(data)

        stack = self.state_stack
        state = self.NewsFilmsParseState
        match stack.state():
            case state.IN_SECTION_DESCRIPTION | state.IN_SECTION_DESCRIPTION_ALT:
                self.section_description = data
            case state.IN_FILM_TITLE:
                self.film_title = data.strip()
            case state.IN_DIRECTOR:
                self.film_property_by_label['Director'] = data.strip()
            case state.IN_YEAR:
                self.film_property_by_label['Year'] = data.strip()
            case state.IN_LENGTH:
                self.film_property_by_label['length'] = data.strip()
                self.duration = get_duration(self.film_property_by_label)
            case state.IN_FILM_DESCRIPTION:
                self.film_description = data.strip()
                self.print_debug('handle_data', f'{self.film_description=}')

    def _init_film_props(self):
        self.film_url = None
        self.film_title = None
        self.duration = 0
        self.film_description = ''
        self.film_property_by_label = {}
        self.metadata_key = None

        # Reinitialize HtmlPageParser variables.
        self.description = None
        self.article_paragraphs = []
        self.article_paragraph = ''
        self.article = None

        self.print_debug('_init_film_props', f'{self.film_description=}')

    def _read_film(self):
        comment(f'About to parse film "{self.film_title}" from {self.film_url}')
        comment("BUT WON'T DO IT")
        get_film_from_theme_part_page(self.festival_data, self.film_title, self.film_url, self.section_url,
                                      use_section_keeper=False)

    def _get_medium_category(self):
        """Get category from e.g. 'https://festival.idfa.nl/film/4e98a274-4110-4b21-a09f-732759e6ee9f/32-meters/'"""
        category_str = self.film_url.split('/')[4]
        return CATEGORY_BY_STR[category_str]

    def _add_film(self):
        self.film = self.festival_data.create_film(self.film_title, self.film_url)
        if self.film is None:
            broadcast(f"Couldn't create film, {self.film_title}, {self.film_url}", DEBUG_RECORDER)
            COUNTER.increase('duplicate films')
        else:
            # Fill details.
            self.film.duration = self.duration
            self.film.subsection = self.subsection
            self.film.medium_category = self._get_medium_category()

            # Add the film to the list.
            COUNTER.increase('films')
            self.festival_data.films.append(self.film)

            # Get the film info.
            self._add_film_info()

            # Get even more info, e.h. screenings.
            self._read_film()

    def _add_film_info(self):
        # Set metadata.
        metadata = self.film_property_by_label
        if not metadata:
            ERROR_COLLECTOR.add('No metadata', f'film {self.film_title}')
            raise RuntimeError(f'No metadata in film {self.film_title}')

        # Add description and article.
        self.set_article()
        self.set_description_from_article(self.film_description)

        # Add film info.
        COUNTER.increase('film infos')
        self.film_info = FilmInfo(self.film.film_id, self.description, self.article_paragraphs, metadata=metadata)
        self.festival_data.film_infos.append(self.film_info)


class FilmsFromSectionPageParser(HtmlPageParser):
    """Laad the films from given pathway URL. Find the sections in each film."""
    class SectionFilmsParseState(Enum):
        IDLE = auto()
        AWAITING_SECTION_TITLE = auto()
        IN_SECTION_NAME = auto()
        AWAITING_SECTION_DESCRIPTION = auto()
        IN_SECTION_DESCRIPTION_ALT = auto()
        IN_SECTION_DESCRIPTION = auto()
        AWAITING_FILM = auto()
        IN_FILM = auto()
        IN_FILM_URL = auto()
        IN_FILM_TITLE = auto()
        DONE = auto()

    def __init__(self, festival_data, section_url):
        super().__init__(festival_data, DEBUG_RECORDER, 'FFS')
        self.section_url = section_url
        self.section_name = None
        self.section_description = None

        # Initialize film properties.
        self.film_url = None
        self.film_title = None

        self.draw_headed_bar(get_readable_theme_str(section_url))
        self.state_stack = self.StateStack(self.print_debug, self.SectionFilmsParseState.IDLE)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.SectionFilmsParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'a', a] if a and a[0][1].startswith('/section/'):
                stack.change(state.AWAITING_SECTION_TITLE)
            case [state.AWAITING_SECTION_TITLE, 'span', a] if a:
                self.section_name = a[0][1]
                stack.change(state.AWAITING_SECTION_DESCRIPTION)
            case [state.AWAITING_SECTION_DESCRIPTION, 'p', a] if a and a[0] == ('index', '0'):
                stack.change(state.IN_SECTION_DESCRIPTION)
            case [state.AWAITING_SECTION_DESCRIPTION, 'div', a] if a and a[0][1] == 'ey43j5h0 css-uu0j5i-Body-Body':
                stack.change(state.IN_SECTION_DESCRIPTION_ALT)
            case [state.AWAITING_FILM, 'article', _]:
                stack.push(state.IN_FILM)
            case [state.IN_FILM, 'a', a] if a and a[0][0] == 'href':
                self.film_url = FESTIVAL_HOSTNAME + a[0][1]
                stack.push(state.IN_FILM_URL)
            case [state.IN_FILM_URL, 'img', a] if a and a[0][0] == 'alt':
                self.film_title = a[0][1]
                stack.push(state.IN_FILM_TITLE)
            case [state.AWAITING_FILM, 'footer', _]:
                stack.change(state.DONE)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        stack = self.state_stack
        state = self.SectionFilmsParseState
        match [stack.state(), tag]:
            case [state.IN_SECTION_DESCRIPTION, 'p']:
                stack.change(state.AWAITING_FILM)
            case [state.IN_SECTION_DESCRIPTION_ALT, 'div']:
                stack.change(state.AWAITING_FILM)
            case [state.IN_FILM_TITLE, 'img']:
                stack.pop()
            case [state.IN_FILM_URL, 'a']:
                stack.pop()
            case [state.IN_FILM, 'article']:
                comment(f'Ready to read film "{self.film_title}" from {self.film_url}')
                self._read_film()
                stack.pop()

    def handle_data(self, data):
        super().handle_data(data)

        stack = self.state_stack
        state = self.SectionFilmsParseState
        match stack.state():
            case state.IN_SECTION_DESCRIPTION | state.IN_SECTION_DESCRIPTION_ALT:
                self.section_description = data

    def _init_film_props(self):
        self.film_url = None
        self.film_title = None

    def _read_film(self):
        comment(f'About to parse film "{self.film_title}" from {self.film_url}')
        get_film_from_theme_part_page(self.festival_data, self.film_title, self.film_url, self.section_url)
        self._init_film_props()


class FilmsFromPathwayPageParser(HtmlPageParser):
    """Laad the films from given pathway URL. Find the sections in each film."""
    class PathwayFilmsParseState(Enum):
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

    sections_by_film = {}

    def __init__(self, festival_data, pathway_url):
        super().__init__(festival_data, DEBUG_RECORDER, 'FFP')
        self.pathway_url = pathway_url

        # Initialize film data.
        self.film_url = None
        self.film_title = None
        self.section_title = None
        self.section_name = None
        self.subsection = None
        self.film_property_by_label = None
        self.metadata_key = None

        # Draw a bar with section info.
        self.draw_headed_bar(get_readable_theme_str(pathway_url))

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.PathwayFilmsParseState.AWAITING_TITLE)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        stack = self.state_stack
        state = self.PathwayFilmsParseState
        match [stack.state(), tag, attrs]:
            case [state.AWAITING_TITLE, 'title', _]:
                stack.change(state.IN_TITLE)
            case [state.AWAITING_DESCR, 'meta', a] if len(a) > 1 and a[0][1] == 'description':
                self.description = a[1][1]
                stack.change(state.AWAITING_FILM_URL)
            case [state.AWAITING_FILM_URL, 'a', a] if a and a[0][0] == 'href' and a[0][1].startswith(FESTIVAL_HOSTNAME):
                self.film_url = a[0][1]
                COUNTER.increase('film URLs')
                stack.change(state.AWAITING_FILM_TITLE)
            case [state.AWAITING_FILM_TITLE, 'img', a] if len(a) > 2 and a[0][0] == 'alt':
                self.film_title = a[0][1]
                self._read_film()
                stack.change(state.AWAITING_FILM_URL)
            case [state.AWAITING_FILM_URL, 'footer', _]:
                stack.change(state.DONE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        stack = self.state_stack
        state = self.PathwayFilmsParseState
        match [stack.state(), tag]:
            case [state.IN_TITLE, 'title']:
                stack.change(state.AWAITING_DESCR)
            case [state.IN_FILM_PROPERTY, 'div']:
                stack.change(state.IN_FILM_PROPERTIES)
            case [state.IN_FILM_PROPERTIES, 'div']:
                self._reset_film_parsing()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        stack = self.state_stack
        state = self.PathwayFilmsParseState
        match stack.state():
            case state.IN_TITLE:
                self.section_title = data.split('|')[-1].strip()

    def _read_film(self):
        comment(f'About to parse film {self.film_title} from {self.film_url}')
        get_film_from_theme_part_page(self.festival_data, self.film_title, self.film_url, self.pathway_url)
        self._init_film_data()

    def _init_film_data(self):
        self.film_url = None
        self.film_title = None
        self.section_title = None
        self.section_name = None
        self.subsection = None
        self.film_property_by_label = {}
        self.metadata_key = None

    def _reset_film_parsing(self):
        stack_dump = f'RESET FILM PARSING\n{str(self.state_stack)}'
        broadcast(stack_dump, DEBUG_RECORDER)
        ERROR_COLLECTOR.add('STOPPED PARSING A SCREENING', f'{str(self.screening)}')
        self._init_film_data()


class FilmPageParser(HtmlPageParser):
    """Parse the page of a film of which title and url were found in a specific theme page."""
    class FilmsParseState(Enum):
        IDLE = auto()
        AWAITING_TITLE = auto()
        IN_TITLE = auto()
        AWAITING_META_DICT = auto()
        IN_META_DICT = auto()
        IN_META_PROPERTY = auto()
        AWAITING_TICKETS = auto()
        AWAITING_ARTICLE = auto()
        NEAR_ARTICLE = auto()
        IN_ARTICLE = auto()
        IN_PARAGRAPH = auto()
        AWAITING_CHAPTER = auto()
        AWAITING_SCREENINGS = auto()
        IN_SCREENINGS = auto()
        IN_SCREENING = auto()
        IN_DATE = auto()
        AFTER_DATE = auto()
        IN_AUDIENCE = auto()
        IN_COMBINATION_PROGRAM = auto()
        AWAITING_TIME = auto()
        IN_TIME = auto()
        IN_LOCATION = auto()
        AFTER_LOCATION = auto()
        SKIP_GRAPHICS = auto()
        IN_SCREENING_PROPS = auto()
        IN_TICKET_BUTTON = auto()
        BETWEEN_BUTTONS = auto()
        IN_CALENDAR_BUTTON = auto()
        IN_SUB_HEADER = auto()
        AWAITING_SECTION_URL = auto()
        IN_SECTION_URL = auto()
        DONE = auto()

    nl_month_by_name: Dict[str, int] = {'november': 11}
    path_by_combi_title = LOCAL_CONFIG['UrlpathByCombinationTitle']
    re_title = re.compile(r'Onderdeel van (.*)')  # "Onderdeel van Shorts: Manufactured Control"

    def __init__(self, festival_data, theme_str, film_title, film_url, debug_prefix=None):
        debug_prefix = debug_prefix or 'PFP'
        super().__init__(festival_data, DEBUG_RECORDER, debug_prefix)
        self.festival_data = festival_data
        self.film_title = film_title
        self.film_url = film_url
        self.film_property_by_label = {'sections': []}
        self.film = None
        self.metadata_key = None
        self.section_title = None
        self.section_url = None
        self.subsection = None
        self.film_info = None
        self.screened_films = set()
        self.combination_films = set()

        # Screening properties.
        self.start_date = None
        self.start_dt = None
        self.end_dt = None
        self.theater = None
        self.screen = None
        self.audience = None
        self.subtitles = None
        self.qa = None
        self.combi_program = None
        self.combi_props = None
        self.screening = None

        self.draw_headed_bar(f'{theme_str} - {film_title}')
        self.state_stack = self.StateStack(self.print_debug, self.FilmsParseState.IDLE)
        self._init_screening_props()

    def feed(self, data):
        super().feed(data)

        comment('Add the sections found to the sections keeper.')
        sections = self.film_property_by_label['sections'] if self.film_property_by_label else []
        print(f'{", ".join([s for s in sections]) if sections else["No sections found"]}')
        DEBUG_RECORDER.add(f'{len(sections)} SECTIONS: {sections or "None"}')
        for section_title in self.film_property_by_label['sections']:
            _ = SectionsKeeper.add_section_props(section_title)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        stack = self.state_stack
        state = self.FilmsParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'script', _]:
                stack.push(state.AWAITING_TITLE)
            case [state.AWAITING_TITLE, 'h1', _]:
                stack.change(state.IN_TITLE)
            case [state.AWAITING_META_DICT | state.IN_META_DICT, 'div', a] if a and a[0][0] == 'data-meta':
                self.metadata_key = a[0][1]
                stack.change(state.IN_META_PROPERTY)
            case [state.AWAITING_ARTICLE, 'div', a] if a and a[0] == ('class', 'enmft8s0 css-146pwl1-Body'):
                stack.change(state.IN_ARTICLE)
            case [state.AWAITING_ARTICLE, 'div', a] if a and a[0] == ('variant', '3'):
                stack.change(state.AWAITING_CHAPTER)
            case [state.IN_ARTICLE, 'p', a] if a and a[0][0] == 'index':
                stack.push(state.IN_PARAGRAPH)
            case [state.AWAITING_SCREENINGS, 'div', a] if a and a[0] == ('variant', '3'):
                stack.change(state.AWAITING_CHAPTER)
            case [state.IN_SCREENINGS, 'div', a] if a and a[0] == ('variant', '4'):
                stack.push(state.IN_DATE)
            case [state.AFTER_DATE, 'div', a] if a and a[0] == ('variant', '5'):
                stack.push(state.IN_AUDIENCE)
            case [state.AFTER_DATE, 'span', _]:
                stack.change(state.IN_TIME)
            case [state.AFTER_LOCATION, 'button', _]:
                stack.change(state.IN_TICKET_BUTTON)
            case [state.AFTER_LOCATION, 'svg', _]:
                stack.change(state.SKIP_GRAPHICS)
            case [state.IN_SCREENING_PROPS, 'button', _]:
                # self.print_debug('Found a button in screening props.', f'Stack is:\n{str(stack)}\n')
                stack.change(state.IN_TICKET_BUTTON)
            case [state.BETWEEN_BUTTONS, 'button', _]:
                stack.change(state.IN_CALENDAR_BUTTON)
            case [state.IN_SCREENINGS, 'button', _]:
                self.print_debug('Found a button.', f'Stack is:\n{str(stack)}\n')
                stack.push(state.IN_TICKET_BUTTON)

            case [state.IN_SCREENINGS, 'a', a] if len(a) > 1 and a[1][0] == 'href' and a[1][1].startswith('/section/'):
                self.section_url = FESTIVAL_HOSTNAME + a[1][1]
                self._add_section()
                self._add_combinations()
                stack.change(state.DONE)
            case [state.IN_SCREENINGS | state.AWAITING_SCREENINGS | state.DONE, 'footer', _]:
                self._add_combinations()
                stack.change(state.DONE)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)

        stack = self.state_stack
        state = self.FilmsParseState
        match [stack.state(), tag]:
            case [state.IN_TITLE, 'h1']:
                stack.change(state.AWAITING_META_DICT)
            case [state.IN_META_PROPERTY, 'div']:
                stack.change(state.IN_META_DICT)
            case [state.IN_META_DICT, 'div']:
                stack.change(state.AWAITING_ARTICLE)
            case [state.IN_PARAGRAPH, 'p']:
                self.add_paragraph()
                stack.pop()
            case [state.NEAR_ARTICLE, 'div']:
                stack.change(state.IN_ARTICLE)
            case [state.IN_ARTICLE, 'div']:
                self._add_film()
                if self.film.url in IGNORE_SCREENING_FILMS:
                    self.film.medium_category = CATEGORY_BY_STR['event']
                    stack.change(state.DONE)
                    COUNTER.increase('ignore screenings')
                else:
                    stack.change(state.AWAITING_SCREENINGS)
            case [state.IN_DATE, 'div']:
                stack.change(state.AFTER_DATE)
            case [state.IN_AUDIENCE, 'div']:
                stack.pop()
            case [state.IN_COMBINATION_PROGRAM, 'div']:
                stack.pop()
            case [state.IN_TIME, 'span']:
                stack.change(state.IN_LOCATION)
            case [state.SKIP_GRAPHICS, 'svg']:
                # self.print_debug('Done skipping graphics.', f'Stack is:\n{str(stack)}\n')
                stack.change(state.IN_SCREENING_PROPS)
            case [state.IN_TICKET_BUTTON, 'button']:
                # self.print_debug('Done parsing a screening.', f'Stack is:\n{str(stack)}\n')
                stack.change(state.BETWEEN_BUTTONS)
            case [state.IN_CALENDAR_BUTTON, 'button']:
                self.print_debug('Passed calendar button.', f'Stack is:\n{str(stack)}\n')
                self._add_screening()
                stack.pop()

    def handle_data(self, data):
        super().handle_data(data)

        stack = self.state_stack
        state = self.FilmsParseState
        match stack.state():
            case state.IN_META_PROPERTY:
                self._add_film_property(data.strip())
            case state.IN_PARAGRAPH:
                self.add_article_text(data)
            case state.AWAITING_CHAPTER if data == 'Synopsis':
                stack.change(state.NEAR_ARTICLE)
            case state.AWAITING_CHAPTER if data == 'Tickets & Times':
                stack.change(state.IN_SCREENINGS)
            case state.AWAITING_CHAPTER if data == 'Credits':
                self.print_debug(f'{str(stack)}')
                self.print_debug('End of screening data', f'stack is {str(stack)}')
                stack.change(state.DONE)
            case state.IN_DATE:
                self._set_screening_date(data)
            case state.IN_AUDIENCE:
                self._get_audience(data.strip())
            case state.IN_COMBINATION_PROGRAM:
                self._handle_combination_data(data)
            case state.IN_TIME:
                self._set_screening_times(data)
            case state.IN_LOCATION:
                if not self._set_idfa_screen(data):
                    raise ValueError(f'could not make a screen from "{data}"')
                DEBUG_RECORDER.add(f'SCREEN: {data=}, {self.screen=}')
                stack.change(state.AFTER_LOCATION)
            case state.IN_SCREENING_PROPS if 'Q&A' in data:
                self.qa = 'Q&A'
                self.print_debug('assigned Q&A', f'{self.qa=}')
            case state.IN_SCREENING_PROPS if 'subtitle' in data:
                self.subtitles = data.strip()
                self.print_debug('assigned subtitles', f'{self.subtitles=}')

    def add_article_text(self, data):
        if not data.startswith('.css'):
            super().add_article_text(data)

    def _exit_screening(self, except_code):
        COUNTER.increase('screening parse error')
        error, message = f'{except_code} in {self.film_title}', 'Proceeding to next film'
        ERROR_COLLECTOR.add(error, message)
        DEBUG_RECORDER.add(f'{error=}, {message=}')
        self.state_stack.change(self.FilmsParseState.DONE)

    def _add_film_property(self, data):
        if self.metadata_key == 'sections':
            DEBUG_RECORDER.add(f'FOUND SECTIONS {data}')
            section_titles = [section_title.strip() for section_title in data.split(sep=',')]
            self.film_property_by_label['sections'].extend(section_titles)
            self.section_title = section_titles[0]
        else:
            self.film_property_by_label[self.metadata_key] = data

    def _add_section(self):
        DEBUG_RECORDER.add(f'ADD SECTION {self.section_title}, {self.section_url}')
        section = self.festival_data.get_section(self.section_title, color_by_id=COLOR_BY_SECTION_ID)
        if section:
            self.subsection = self.festival_data.get_subsection(self.section_title, self.section_url, section)
            self.film.subsection = self.subsection if self.subsection else self.film.subsection

    def _get_medium_category(self):
        """Get category from e.g. ''https://festival.idfa.nl/en/film/45793ccc-02d5-4bda-92aa-1e09aff38f56/absences/''"""
        category_str = self.film_url.split('/')[4]
        return CATEGORY_BY_STR[category_str]

    def _get_audience(self, data):
        self.audience = AUDIENCE_PUBLIC if data == 'Public' else data
        if self.audience == AUDIENCE_PUBLIC:
            COUNTER.increase('public screening')

    def _add_film(self):
        self.film = self.festival_data.add_film(self.film_title, self.film_url)
        # self.film = self.festival_data.create_film(self.film_title, self.film_url)
        if self.film is None:
            ERROR_COLLECTOR.add("Couldn't create film", f'{self.film_title}, {self.film_url}')
        else:
            # Fill details.
            self.film.duration = self._get_duration()
            if self.subsection:
                self.film.subsection = self.subsection
            self.film.medium_category = self._get_medium_category()

            if not USE_NEWS_PAGES:
                # Add the film to the list.
                COUNTER.increase('films')
                self.festival_data.films.append(self.film)

            # Get the film info.
            self._add_film_info()

    def _add_film_info(self):
        # Set metadata.
        metadata = self.film_property_by_label
        if not metadata:
            ERROR_COLLECTOR.add('No metadata', f'film {self.film_title}')
            raise RuntimeError(f'No metadata in film {self.film_title}')

        # Add description and article.
        self.set_article()
        self.set_description_from_article(self.film.title)

        # Add film info.
        COUNTER.increase('meta dicts')
        self.film_info = self.film.film_info(self.festival_data)
        if self.film_info.film_id:
            self.film_info.article_paragraphs = self.article_paragraphs
            self.film_info.metadata |= metadata
        else:
            self.film_info = FilmInfo(self.film.film_id, self.description, self.article_paragraphs, metadata=metadata)
            self.festival_data.film_infos.append(self.film_info)

    def _add_screening(self):
        # Create an IDFA screening from the gathered data.
        self.screening = IdfaScreening(self.film,
                                       self.screen,
                                       self.start_dt,
                                       self.end_dt,
                                       qa=self.qa,
                                       audience=self.audience,
                                       subtitles=self.subtitles,
                                       combi_program=self.combi_program
                                       )
        self.add_screening(self.screening, DISPLAY_ADDED_SCREENING)

        # Add combination data.
        if self.combi_props:
            self.combi_props['screening_str'] = f'{self.screening}'
            CombinationsKeeper.add_row(list(self.combi_props.values()))

        # Initialize the next round of parsing.
        self._init_screening_props()

    def _init_screening_props(self):
        self.start_date = None
        self.start_dt = None
        self.end_dt = None
        self.theater = None
        self.screen = None
        self.audience = None
        self.subtitles = ''
        self.qa = None
        self.combi_program = None
        self.combi_props = None
        self.screening = None
        self.print_debug('screening props initialized', f'stack is {str(self.state_stack)}')

    def _get_duration(self):
        return get_duration(self.film_property_by_label)

    def _set_screening_date(self, data):
        """Parse screening date, which is formatted different per language. See also `set_nl_url()` in MTMF"""
        parts = data.split()  # 'Fri, november 13'
        # parts = data.split()  # 'ma 17 november'
        try:
            day = int(parts[2])
            month = int(self.nl_month_by_name[parts[1]])
            # day = int(parts[1])
            # month = int(self.nl_month_by_name[parts[2]])
        except ValueError:
            screen = self._set_idfa_screen(data)
            if screen:
                self.film.medium_category = CATEGORY_FIELD_EVENTS
                msg = f'Location instead of screening date on "{str(self.film)}" page'
                broadcast(msg, DEBUG_RECORDER)
                COUNTER.increase('multi day')
                self.state_stack.change(self.FilmsParseState.DONE)
        else:
            self.start_date = datetime.date(day=day, month=month, year=FESTIVAL_YEAR)

    def _set_screening_times(self, data):
        def _time(time_str):
            """Get time from strings as '17.15–18.48' or '18-11-2025, 21.45 – 19-11-2025, 00.08'"""
            hh_dot_mm = time_str.split(',')[-1].strip()
            return hh_dot_mm

        times = data.split(' – ')     # '15:30 – 17:40' or '19:30 – 21:08'
        if len(times) == 1:
            times = data.split(' – ')
        # times = data.split('–')     # '17.15–18.48' or '18-11-2025, 21.45 – 19-11-2025, 00.08'

        start_time_str = _time(times[0])
        start_hour, start_minute = start_time_str.split(':')
        start_time = datetime.time(hour=int(start_hour), minute=int(start_minute))

        end_hour_str = _time(times[1])
        end_hour, end_minute = end_hour_str.split(':')
        end_time = datetime.time(hour=int(end_hour), minute=int(end_minute))

        self.start_dt, self.end_dt = self.get_screening_date_times(self.start_date, start_time, end_time)

    def _handle_combination_data(self, data):
        # Find a combination title in the data.
        m = self.re_title.match(data)
        combi_title = m.group(1) if m else None
        if combi_title:
            COUNTER.increase('combinations')

        # Try to get a combination URL.
        try:
            combi_url = FESTIVAL_HOSTNAME + self.path_by_combi_title[combi_title]
        except KeyError:
            combi_url = None

        self.combi_props = {
            'film_id': self.film.film_id,
            'screening_str': None,
            'combination_data': combi_title,
            'combination_url': combi_url,
        }

        # Get the combination program if possible and add it to the set of combination programs.
        if combi_url:
            combi_program = self.festival_data.get_film_by_key(combi_title, combi_url)
            self.combination_films.add(combi_program)

    def _add_combinations(self):
        for combi_program in self.combination_films:
            # Set this film as screened film in the combination program.
            combi_info = combi_program.film_info(self.festival_data)
            if self.film.film_id not in [sf.film_id for sf in combi_info.screened_films]:
                screened_film = ScreenedFilm(self.film.film_id, self.film.title, self.description)
                combi_info.screened_films.append(screened_film)

            # Set the combination program of this film.
            self.film_info.combination_films.append(combi_program)

    def _set_idfa_screen(self, data):
        if data.startswith('.css'):
            COUNTER.increase('funny location')
            return False
        elif data.startswith('Loading') or data.startswith('Inloggen'):
            self._exit_screening(f'Missed a screening while parsing "{self.film_title}"')
            return False

        screen_parse_name = data.strip()
        splitter = LocationSplitter.split_location
        self.screen = get_screen_from_parse_name(self.festival_data, screen_parse_name, splitter)
        return True

    def _added_screening(self, data):
        can_add = self._set_idfa_screen(data)
        if can_add:
            DEBUG_RECORDER.add(f'SCREEN: {data=}, {self.screen=}')
            self._add_screening()
        return can_add


def get_duration(film_property_by_label):
    try:
        duration_str = film_property_by_label['length']  # "96 min"
    except KeyError:
        duration_str = '0'
    minutes = int(duration_str.split()[0])
    return datetime.timedelta(minutes=minutes)


class CombinationFilmPageParser(FilmPageParser):
    """Get minimal information to create a combination film."""
    def __init__(self, festival_data, theme_str, film_title, film_url):
        super().__init__(festival_data, theme_str, film_title, film_url, debug_prefix='CFP')

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        stack = self.state_stack
        state = self.FilmsParseState
        match [stack.state(), tag, attrs]:
            case [state.IDLE, 'meta', a] if len(a) > 1 and a[0] == ('property', 'og:description'):
                self.description = a[1][1]
            case [state.IDLE, 'div', a] if len(a) > 1 and a[1] == ('clamp', '3'):
                stack.change(state.IN_TITLE)
            case [state.AWAITING_ARTICLE, 'div', a] if a and a[0] == ('variant', '3'):
                stack.change(state.NEAR_ARTICLE)
            case [state.IN_ARTICLE, 'p', a] if a and a[0][0] == 'index':
                stack.push(state.IN_PARAGRAPH)
            case [state.AWAITING_SCREENINGS, 'article', _]:
                stack.push(state.IN_SCREENING)
            case [state.IN_SCREENING, 'div', a] if a and a[0] == ('variant', '4'):
                stack.push(state.IN_DATE)
            case [state.AWAITING_TIME, 'div', a] if a and a[0][1] == 'ey43j5h0 css-1cky3te-Body-Body':
                stack.push(state.IN_COMBINATION_PROGRAM)
            case [state.AWAITING_TIME, 'span', _]:
                stack.change(state.IN_TIME)
            # case [state.AWAITING_SCREENINGS, 'div', a] if a and a[0] == ('variant', '3'):
            #     stack.push(state.IN_SUB_HEADER)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        stack = self.state_stack
        state = self.FilmsParseState
        match [stack.state(), tag]:
            case [state.IN_TITLE, 'div']:
                stack.change(state.AWAITING_ARTICLE)
            case [state.NEAR_ARTICLE, 'div']:
                stack.change(state.IN_ARTICLE)
            case [state.IN_PARAGRAPH, 'p']:
                self.add_paragraph()
                stack.pop()
            case [state.IN_ARTICLE, 'div']:
                self._add_film()
                stack.change(state.AWAITING_SCREENINGS)
            case [state.IN_DATE, 'div']:
                stack.change(state.AWAITING_TIME)
            case [state.IN_COMBINATION_PROGRAM, 'div']:
                stack.pop()
            case [state.IN_TIME, 'span']:
                stack.change(state.IN_LOCATION)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        stack = self.state_stack
        state = self.FilmsParseState
        match stack.state():
            case state.IN_TITLE:
                self.film_title = data.strip()
            case state.IN_PARAGRAPH:
                self.add_article_text(data)
            case state.IN_DATE:
                self._set_screening_date(data)
            case state.IN_TIME:
                self._set_screening_times(data)
            case state.IN_LOCATION:
                if self._added_screening(data):
                    stack.pop(2)  # Pop stack twice to get back to "AWAITING_SCREENINGS".
            case state.IN_SUB_HEADER:
                if data == 'Tickets & Tijden':
                    stack.pop()
                else:
                    self._add_combinations()
                    stack.change(state.DONE)


class LocationSplitter:
    num_screen_re = re.compile(r'^(?P<theater>.*?) (?P<number>\d+)$')

    @classmethod
    def split_location(cls, location):
        city_name = FESTIVAL_CITY
        theater_parse_name = location
        default_screen_abbreviation = 'zaal'
        num_match = cls.num_screen_re.match(location)

        location_words = location.split()
        screen_abbreviation = ''
        location_words.extend(['', '', ''])
        match [location_words[0], location_words[1], location_words[2], location_words[3]]:
            case ['De', 'Balie:', 'Grote', 'Zaal']:
                theater_parse_name = 'De Balie'
                screen_abbreviation = 'groot'
            case ['OT', '301', '', '']:
                theater_parse_name = 'OT 301'
            case ['SPUI', '25', '', '']:
                theater_parse_name = location
                screen_abbreviation = default_screen_abbreviation
            case ['OBA', 'Oosterdok', 'OBA', 'Theater']:
                theater_parse_name = ' '.join(location_words[:2])
                screen_abbreviation = ' '.join(location_words[2:])
            case ['@droog:', first_word, _, _]:
                theater_parse_name = '@droog'
                screen_abbreviation = first_word
            case ['Casa', 'Rosso:', _, _]:
                theater_parse_name = 'Casa Rosso'
            case ['Rialto', 'VU', 'Griffioen:', _]:
                theater_parse_name = 'Rialto VU'
                screen_abbreviation = 'Griffioen zaal 4'
            case ['Rialto', 'SILO', 'Zaal', '1']:
                theater_parse_name = 'Rialto SILO Zaal'
                screen_abbreviation = '11'
            case [_, _, _, _] if num_match:
                theater_parse_name = num_match.group(1)
                screen_abbreviation = num_match.group(2)
            case _:
                screen_abbreviation = default_screen_abbreviation

        return city_name, theater_parse_name, screen_abbreviation or default_screen_abbreviation


class CombinationsKeeper:
    combination_props_header = ['film_id', 'screening_str', 'combination_str', 'combination_url']
    combination_props_list = []

    @classmethod
    def add_row(cls, prop_row):
        cls.combination_props_list.append(prop_row)

    @classmethod
    def write_combination_data(cls, festival_data):
        dialect = festival_data.dialect
        header = cls.combination_props_header
        rows = cls.combination_props_list
        with open(COMBI_DATA_PATH, 'w') as csvfile:
            csv_writer = csv.writer(csvfile, dialect=dialect)
            csv_writer.writerow(header)
            csv_writer.writerows(rows)


class SectionsKeeper:
    """Uses films found in pathways to support finding sections."""
    section_titles = set()
    film_id = 0

    @classmethod
    def get_new_film_id(cls, film_url):
        msg = f'Trying to create film_id {cls.film_id + 1} without library tools - {film_url}'
        raise RuntimeError(msg)
        # cls.film_id += 1
        # return cls.film_id

    @classmethod
    def add_section_props(cls, section_title):
        if section_title in cls.section_titles:
            return False
        cls.section_titles.add(section_title)
        COUNTER.increase('sections')
        return True


class IdfaScreening(Screening):
    re_num_screen = re.compile(r'^(?P<theater>.*?)\s+(?P<number>\d+)$')
    re_colon_screen = re.compile(r'^(?P<theater>.*?):\s+(?P<room>.+)$')

    def __init__(self, film, screen, start_datetime, end_datetime, qa='', extra='',
                 audience=None, combi_program=None, subtitles=''):
        super().__init__(film, screen, start_datetime, end_datetime, qa or '', extra, audience,
                         combination_program=combi_program, subtitles=subtitles)

    @classmethod
    def get_idfa_screen(cls, festival_data, data):
        screen_parse_name = data.strip()
        return get_screen_from_parse_name(festival_data, screen_parse_name, cls.split_location)

    @classmethod
    def split_location(cls, location):
        city_name = FESTIVAL_CITY
        theater_parse_name = location
        screen_abbreviation = 'zaal'
        colon_match = cls.re_colon_screen.match(location)
        if colon_match:
            theater_parse_name = colon_match.group(1)
            screen_abbreviation = colon_match.group(2)
        else:
            num_match = cls.re_num_screen.match(location)
            if num_match:
                theater_parse_name = num_match.group(1)
                screen_abbreviation = num_match.group(2)
        return city_name, theater_parse_name, screen_abbreviation

    def film_is_combi(self):
        return self.film.medium_category == 'combinations'


class IdfaData(FestivalData):
    def __init__(self, directory, common_data_dir=None):
        super().__init__(FESTIVAL_CITY, directory, common_data_dir=common_data_dir)
        self.compilation_by_url = {}

    def film_key(self, title, url):
        return url

    def film_can_go_to_planner(self, film_id):
        return True

    def screening_can_go_to_planner(self, screening):
        can_go = screening.is_public() and not self.included_in_combi(screening)
        return can_go

    def included_in_combi(self, screening):
        if screening.film_is_combi():
            return False
        coinciding_screenings = [s for s in self.screenings if s.film_is_combi() and screening.is_part_of(s)]
        return coinciding_screenings


if __name__ == "__main__":
    main()
