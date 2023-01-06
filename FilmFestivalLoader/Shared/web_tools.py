#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 18:27:20 2020

@author: maarten
"""

import html.parser
import json
import os
from urllib.error import HTTPError
from urllib.parse import quote, urlparse, urlunparse
from urllib.request import urlopen, Request


DEFAULT_BYTE_COUNT = 512
DEFAULT_ENCODING = 'ascii'


def iripath_to_uripath(path):
    return quote(path)


def iri_slug_to_url(host, slug):
    host_obj = urlparse(host)
    slug_obj = urlparse(slug)
    slug_obj = slug_obj._replace(path=quote(slug_obj.path))
    result_url = urlunparse([host_obj.scheme, host_obj.hostname, slug_obj.path, '', '', ''])
    return result_url


def get_encoding_from_url(url, byte_count=DEFAULT_BYTE_COUNT):
    request = UrlReader.get_request(url)
    with urlopen(request) as response:
        encoding = response.headers.get_content_charset()
        if encoding is None:
            html_bytes = response.read(byte_count)
            encoding = get_encoding_from_bytes(html_bytes)
    return encoding


def get_encoding_from_file(file, byte_count=DEFAULT_BYTE_COUNT):
    with open(file, 'r') as f:
        sample_text = f.read(byte_count)
    charset = get_encoding_from_bytes(sample_text)
    return charset


def get_encoding_from_bytes(html_bytes):
    charset_parser = HtmlCharsetParser()
    charset = charset_parser.get_charset(html_bytes)
    return charset


def fix_json(code_point_str):
    """Replace HTML entity code points by the corresponding symbols.

    @param code_point_str: String possibly containing not decoded HTML code points like '\u003c'.
    @return: String with code points replaced by the corresponding symbols.
    """

    result_str = json.loads('"' + code_point_str + '"')
    return result_str


def get_encoding(url, error_collector, byte_count=DEFAULT_BYTE_COUNT):
    encoding = get_encoding_from_url(url, byte_count)
    if encoding is None:
        error_collector.add('No encoding found', f'{url}')
        encoding = UrlFile.default_encoding
    return encoding


class UrlFile:
    default_byte_count = DEFAULT_BYTE_COUNT
    default_encoding = DEFAULT_ENCODING

    def __init__(self, url, path, error_collector, byte_count=None):
        self.url = url
        self.path = path
        self.error_collector = error_collector
        self.byte_count = byte_count if byte_count is not None else self.default_byte_count
        self.encoding = None

    def get_text(self, comment_at_download=None):
        try:
            self.set_encoding()
        except HTTPError as e:
            self.error_collector.add(str(e), f'{self.url}')
            return None
        if os.path.isfile(self.path):
            with open(self.path, 'r', encoding=self.encoding) as f:
                html_text = f.read()
        else:
            if comment_at_download is not None:
                print(comment_at_download)
            reader = UrlReader(self.error_collector)
            html_text = reader.load_url(self.url, self.path)
        return html_text

    def set_encoding(self):
        if self.encoding is None:
            if os.path.isfile(self.path):
                self.encoding = get_encoding_from_file(self.path, self.byte_count)
            if self.encoding is None:
                self.encoding = get_encoding_from_url(self.url)
            if self.encoding is None:
                self.error_collector.add('No encoding found', f'{self.url}')
                self.encoding = self.default_encoding


class UrlReader:
    user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
    headers = {'User-Agent': user_agent}

    def __init__(self, error_collector):
        self.error_collector = error_collector

    @classmethod
    def get_request(cls, url):
        return Request(url, headers=cls.headers)

    def load_url(self, url, target_file=None, encoding=DEFAULT_ENCODING):
        request = self.get_request(url)
        with urlopen(request) as response:
            html_bytes = response.read()
            if html_bytes is not None:
                if len(html_bytes) == 0:
                    self.error_collector.add(f'No text found, file {target_file} not written', f'{url}')
                elif target_file is not None:
                    with open(target_file, 'wb') as f:
                        f.write(html_bytes)
        decoded_html = html_bytes.decode(encoding=encoding)
        return decoded_html


class HtmlCharsetParser(html.parser.HTMLParser):

    default_charset = None

    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.charset = None

    def get_charset(self, text):
        self.feed(text)
        charset = (self.charset if self.charset is not None else self.default_charset)
        return charset

    def handle_starttag(self, tag, attrs):
        html.parser.HTMLParser.handle_starttag(self, tag, attrs)
        if tag == 'meta' and len(attrs) > 0 and attrs[0] == 'charset':
            self.charset = attrs[0][1]


if __name__ == "__main__":
    print("This module is not executable.")
