#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 18:27:20 2020

@author: maarten
"""

from html.parser import HTMLParser


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
        return self.charset
           
    def handle_starttag(self, tag, attrs):
        HTMLParser.handle_starttag(self, tag, attrs)
        if tag == 'meta':
            for attr in attrs:
                if attr[0] == 'charset':
                    self.charset = attr[1]
                    break


if __name__ == "__main__":
    print("This module is not executable.")
