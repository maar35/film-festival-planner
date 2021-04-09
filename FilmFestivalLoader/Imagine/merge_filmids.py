#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 16:42:45 2021

@author: maartenroos
"""

import os
from csv import reader

# Parameters.
delimiter = ';'
encoding = 'UTF-8'
festival = 'Imagine'
year = 2021

# Directories.
documents_dir = os.path.expanduser("~/Documents/Film/{0}/{0}{1}".format(festival, year))
plandata_dir = os.path.join(documents_dir, "_planner_data")
bakdata_dir = os.path.join(plandata_dir, "_bak")
newdata_dir = os.path.join(plandata_dir, "_new")
correctdata_dir = os.path.join(plandata_dir, "_correct")

# Files.
filmids_file = "filmids.txt"
old_filmids = os.path.join(bakdata_dir, filmids_file)
new_filmids = os.path.join(newdata_dir, filmids_file)
correct_filmids = os.path.join(correctdata_dir, filmids_file)


def main():
    old_id_list = read_csv(old_filmids)
    new_id_list = read_csv(new_filmids)
    merge_ids(old_id_list, new_id_list)


def read_csv(file):
    list = []
    with open(file, 'r', encoding=encoding) as read_obj:
        csv_reader = reader(read_obj, delimiter=delimiter)
        for row in csv_reader:
            filmid = int(row[0])
            title = row[1]
            url = row[2]
            list.append(FilmBaseInfo(filmid, title, url))
    return list


def merge_ids(old_infos, new_infos):
    curr_id = max([info.filmid for info in old_infos])
    correct_infos = []
    old_id_by_title = {info.title: info.filmid for info in old_infos}
    new_url_by_title = {info.title: info.url for info in new_infos}
    for title in new_url_by_title.keys():
        if title in old_id_by_title.keys():
            filmid = old_id_by_title[title]
        else:
            curr_id += 1
            filmid = curr_id
        url = new_url_by_title[title]
        correct_info = FilmBaseInfo(filmid, title, url)
        correct_infos.append(correct_info)
    with open(correct_filmids, 'w', encoding=encoding) as f:
        for info in correct_infos:
            f.write(str(info) + '\n')
    print(f"Done writing {len(correct_infos)} records to {correct_filmids}.")


class FilmBaseInfo:

    def __init__(self, filmid, title, url):
        self.filmid = filmid
        self.title = title
        self.url = url

    def __str__(self):
        return delimiter.join([str(self.filmid), self.title, self.url])


if __name__ == "__main__":
    main()
