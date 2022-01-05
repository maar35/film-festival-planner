#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 18:27:20 2020

@author: maarten
"""

import html.parser
import urllib.request
import urllib.error
import urllib.parse
import os
import inspect


def iripath_to_uripath(path):
    return urllib.parse.quote(path)


def get_charset(file, byte_count=512):
    with open(file, 'r') as f:
        sample_text = f.read(byte_count)
    charset_parser = HtmlCharsetParser()
    charset = charset_parser.get_charset(sample_text)
    return charset


class UrlFile:
    default_byte_count = 512
    default_encoding = 'ascii'

    def __init__(self, url, path, error_collector, bytecount=None):
        self.url = url
        self.path = path
        self.error_collector = error_collector
        self.byte_count = bytecount if bytecount is not None else self.default_byte_count
        self.encoding = None

    def get_text(self, comment_at_download=None):
        reader = UrlReader(self.error_collector)
        self.set_encoding(reader)
        if os.path.isfile(self.path):
            with open(self.path, 'r', encoding=self.encoding) as f:
                html_text = f.read()
        else:
            if comment_at_download is not None:
                print(comment_at_download)
            html_text = reader.load_url(self.url, self.path, self.encoding)
        return html_text

    def set_encoding(self, reader):
        if self.encoding is None:
            if os.path.isfile(self.path):
                self.encoding = get_charset(self.path, self.byte_count)
            if self.encoding is None:
                request = reader.get_request(self.url)
                with urllib.request.urlopen(request) as response:
                    self.encoding = response.headers.get_content_charset()
            if self.encoding is None:
                self.error_collector.add('No encoding found', f'{self.url}')
                self.encoding = self.default_encoding


class UrlReader:
    user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
    headers = {'User-Agent': user_agent}

    def __init__(self, error_collector):
        self.error_collector = error_collector

    def get_request(self, url):
        return urllib.request.Request(url, headers=self.headers)

    def load_url(self, url, target_file, sample_bytes=512, encoding='utf-8'):
        request = self.get_request(url)
        html_bytes = None
        with urllib.request.urlopen(request) as response:
            html_bytes = response.read()
            if html_bytes is not None:
                if len(html_bytes) == 0:
                    self.error_collector.add(f'No text found, file {target_file} not written', f'{url}')
                else:
                    with open(target_file, 'wb') as f:
                        f.write(html_bytes)
        html = html_bytes.decode(encoding=encoding)
        return html


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
        if tag == 'meta':
            for attr in attrs:
                if attr[0] == 'charset':
                    self.charset = attr[1]
                    break


class HtmlPageParser(html.parser.HTMLParser):

    class StateStack:

        debugging = None

        def __init__(self, print_debug, state):
            self.print_debug = print_debug
            self.stack = [state]

        def _print_debug(self, new_state):
            frame = inspect.currentframe().f_back
            caller = frame.f_code.co_name if frame.f_code is not None else 'code'
            self.print_debug(f'Parsing state after {caller:6} is {new_state}', '')

        def push(self, state):
            self.stack.append(state)
            self._print_debug(state)

        def pop(self):
            self.stack[-1:] = []
            self._print_debug(self.stack[-1])

        def change(self, state):
            self.stack[-1] = state
            self._print_debug(state)

        def state_is(self, state):
            return state == self.stack[-1]

        def state_in(self, states):
            return self.stack[-1] in states

    def __init__(self, debug_recorder, debug_prefix):
        html.parser.HTMLParser.__init__(self)
        self.debug_recorder = debug_recorder
        self.debug_prefix = debug_prefix

    def print_debug(self, str1, str2):
        if self.debugging:
            self.debug_recorder.add(self.debug_prefix + ' ' + str(str1) + ' ' + str(str2))

    def handle_starttag(self, tag, attrs):
        if len(attrs) > 0:
            sep = f'\n{self.debug_prefix}   '
            extra = sep + sep.join([f'attr:  {attr}' for attr in attrs])
        else:
            extra = ''
        self.print_debug(f'Encountered a start tag: \'{tag}\'', extra)

    def handle_endtag(self, tag):
        self.print_debug('Encountered an end tag :', f'\'{tag}\'')

    def handle_data(self, data):
        self.print_debug('Encountered some data  :', f'\'{data}\'')

    def handle_comment(self, data):
        self.print_debug('Comment  :', data)

    def handle_decl(self, data):
        self.print_debug('Decl     :', data)


if __name__ == "__main__":
    print("This module is not executable.")
