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


def iripath_to_uripath(path):
    return urllib.parse.quote(path)


def get_charset(file, byte_count=512):
    with open(file, 'r') as f:
        pre_text = f.read(byte_count)
    pre_parser = HtmlCharsetParser()
    pre_parser.feed(pre_text)
    return str(pre_parser)


class HtmlCharsetParser(html.parser.HTMLParser):

    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.charset = None

    def __str__(self):
        return self.charset if self.charset is not None else 'ascii'

    def handle_starttag(self, tag, attrs):
        html.parser.HTMLParser.handle_starttag(self, tag, attrs)
        if tag == 'meta':
            for attr in attrs:
                if attr[0] == 'charset':
                    self.charset = attr[1]
                    break


class HtmlPageParser(html.parser.HTMLParser):

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


class UrlReader:

    def __init__(self, error_collector):
        self.error_collector = error_collector

    def read_url(self, url):
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
        headers = {'User-Agent': user_agent}
        req = urllib.request.Request(url, headers=headers)
        html = None
        try:
            with urllib.request.urlopen(req) as response:
                html = response.read().decode()
        except UnicodeEncodeError as e:
            self.error_collector.add(str(e), f'reading URL: {url}')
        except urllib.error.URLError as e:
            extra_info = f'{url}'
            self.error_collector.add(str(e), extra_info)
        return html

    def load_url(self, url, target_file):
        html = self.read_url(url)
        if html is not None:
            if len(html) == 0:
                self.error_collector.add(f'No text found, file {target_file} not written', f'{url}')
            else:
                with open(target_file, 'w') as f:
                    f.write(html)
        return html


if __name__ == "__main__":
    print("This module is not executable.")
