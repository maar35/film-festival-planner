#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 18:27:20 2020

@author: maarten
"""

from html.parser import HTMLParser
import urllib.request
import urllib.error
from urllib.parse import quote                                                                                                                                                                


def uripath_to_iripath(path):
    return quote(path)

def get_charset(file):
    with open(file, 'r') as f:
        pre_text = f.read(512)
    pre_parser = HtmlCharsetParser()
    pre_parser.feed(pre_text)
    return str(pre_parser)


class HtmlCharsetParser(HTMLParser):
    
    def __init__(self):
        HTMLParser.__init__(self)
        self.charset = None

    def __str__(self):
        return self.charset if self.charset is not None else 'ascii'
           
    def handle_starttag(self, tag, attrs):
        HTMLParser.handle_starttag(self, tag, attrs)
        if tag == 'meta':
            for attr in attrs:
                if attr[0] == 'charset':
                    self.charset = attr[1]
                    break


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
            if hasattr(e, 'reason'):
                extra_info += f' - Reason: {e.reason}'
            elif hasattr(e, 'code'):
                extra_info += f' - Error code: {e.code}'
            self.eror_collector.add(str(e), extra_info)
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
