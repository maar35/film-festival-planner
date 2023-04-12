#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 18:27:20 2020

@author: maarten
"""

import json
import os
from enum import Enum, auto
from urllib.error import HTTPError
from urllib.parse import quote, urlparse, urlunparse
from urllib.request import urlopen, Request

from Shared.parse_tools import BaseHtmlPageParser

DEFAULT_BYTE_COUNT = 512
DEFAULT_ENCODING = 'ascii'
DEFAULT_TIMEOUT = 10


def iripath_to_uripath(path):
    return quote(path)


def iri_slug_to_url(host, slug):
    host_obj = urlparse(host)
    slug_obj = urlparse(slug)
    slug_obj = slug_obj._replace(path=quote(slug_obj.path))
    result_url = urlunparse([host_obj.scheme, host_obj.hostname, slug_obj.path, '', '', ''])
    return result_url


def get_netloc(url):
    obj = urlparse(url)
    return urlunparse([obj.scheme, obj.netloc, '', '', '', ''])


def get_encoding_from_url(url, debug_recorder, byte_count=DEFAULT_BYTE_COUNT, timeout=DEFAULT_TIMEOUT):
    request = UrlReader.get_request(url)
    with urlopen(request, timeout=timeout) as response:
        encoding = response.headers.get_content_charset()
        if encoding is None:
            html_bytes = response.read(byte_count)
            encoding = get_encoding_from_bytes(html_bytes, debug_recorder)
    return encoding


def get_encoding_from_file(file, debug_recorder, byte_count=DEFAULT_BYTE_COUNT):
    with open(file, 'r') as f:
        sample_text = f.read(byte_count)
    charset = get_encoding_from_bytes(sample_text, debug_recorder)
    return charset


def get_encoding_from_bytes(html_bytes, debug_recorder):
    charset_parser = HtmlCharsetParser(debug_recorder)
    charset = charset_parser.get_charset(html_bytes)
    return charset


def get_encoding(url, error_collector, debug_recorder, byte_count=DEFAULT_BYTE_COUNT):
    encoding = get_encoding_from_url(url, debug_recorder, byte_count)
    if encoding is None:
        error_collector.add('No encoding found', f'{url}')
        encoding = UrlFile.default_encoding
    return encoding


def fix_json(code_point_str):
    """Replace HTML entity code points by the corresponding symbols.

    @param code_point_str: String possibly containing not decoded HTML code points like '\u003c'.
    @return: String with code points replaced by the corresponding symbols.
    """

    result_str = json.loads('"' + code_point_str + '"')
    return result_str


def get_home_page(home_url, file_keeper, error_collector, debug_recorder):
    home_file = os.path.join(file_keeper.webdata_dir, 'home.html')
    url_file = UrlFile(home_url, home_file, error_collector, debug_recorder, byte_count=500)
    home_html = url_file.get_text()
    if home_html is not None:
        print(f'Home page read into {home_file}, encoding={url_file.encoding}')


class UrlFile:
    default_byte_count = DEFAULT_BYTE_COUNT
    default_encoding = DEFAULT_ENCODING

    def __init__(self, url, path, error_collector, debug_recorder, byte_count=None):
        self.url = url
        self.path = path
        self.error_collector = error_collector
        self.debug_recorder = debug_recorder
        self.byte_count = byte_count if byte_count is not None else self.default_byte_count
        self.encoding = None
        try:
            self.set_encoding()
        except HTTPError as e:
            self.error_collector.add(str(e), f'{self.url}')
            self.encoding = self.default_encoding

    def get_text(self, comment_at_download=None):
        if os.path.isfile(self.path):
            with open(self.path, 'r', encoding=self.encoding) as f:
                html_text = f.read()
        else:
            if comment_at_download is not None:
                print(comment_at_download)
            reader = UrlReader(self.error_collector)
            html_text = reader.load_url(self.url, self.path, self.encoding)
        return html_text

    def set_encoding(self):
        if self.encoding is None:
            if os.path.isfile(self.path):
                self.encoding = get_encoding_from_file(self.path, self.debug_recorder, self.byte_count)
            if self.encoding is None:
                try:
                    self.encoding = get_encoding_from_url(self.url, self.debug_recorder, self.byte_count)
                except ValueError as e:
                    self.error_collector.add(e, f'in {self.url}')
            if self.encoding is None:
                self.error_collector.add('No encoding found', f'{self.url}')
                self.encoding = self.default_encoding


class UrlReader:
    user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
    alt_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
    headers = {'User-Agent': alt_user_agent}

    def __init__(self, error_collector, timeout=DEFAULT_TIMEOUT):
        self.error_collector = error_collector
        self.timeout = timeout

    @classmethod
    def get_request(cls, url):
        return Request(url, headers=cls.headers)

    def load_url(self, url, target_file=None, encoding=DEFAULT_ENCODING):
        request = self.get_request(url)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                html_bytes = response.read()
        except HTTPError as e:
            self.error_collector.add(e, f'while opening {url}')
            html_bytes = None
        if html_bytes is not None:
            if len(html_bytes) == 0:
                self.error_collector.add(f'No text found, file {target_file} not written', f'{url}')
            elif target_file is not None:
                with open(target_file, 'wb') as f:
                    f.write(html_bytes)
        decoded_html = html_bytes.decode(encoding=encoding) if html_bytes is not None else None
        return decoded_html


class HtmlCharsetParser(BaseHtmlPageParser):
    class CharsetParseState(Enum):
        AWAITING_CHARSET = auto()
        DONE = auto()

    default_charset = None

    def __init__(self, debug_recorder):
        BaseHtmlPageParser.__init__(self, debug_recorder, 'CH', debugging=True)
        self.state_stack = self.StateStack(self.print_debug, self.CharsetParseState.AWAITING_CHARSET)
        self.charset = None

    def get_charset(self, text):
        try:
            self.feed(text)
        except TypeError:
            return DEFAULT_ENCODING
        else:
            charset = self.charset or self.default_charset
            return charset

    def handle_starttag(self, tag, attrs):
        BaseHtmlPageParser.handle_starttag(self, tag, attrs)
        if self.state_stack.state_is(self.CharsetParseState.AWAITING_CHARSET):
            if tag == 'meta' and len(attrs) > 0 and attrs[0][0].lower() == 'charset':
                self.charset = attrs[0][1]
                self.state_stack.change(self.CharsetParseState.DONE)


if __name__ == "__main__":
    print("This module is not executable.")
