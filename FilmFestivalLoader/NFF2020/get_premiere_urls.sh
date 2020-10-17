#!/bin/bash

declare -r workdir="/Users/maarten/Documents/Film/NFF/NFF2020/_website_data"
declare -r premieres_site="https://www.filmfestival.nl/festivalpremieres"
declare -r premieres_file=festivalpremieres.html

cd $workdir
curl -o $premieres_file $premieres_site
for site in $(../split_tags.sh festivalpremieres.html | grep festivalpremiere- | cut -d"=" -f3 | cut -d" " -f1); do name=$(echo $site | cut -d"/" -f4); curl -o $name.html $site; done
