#!/bin/bash

declare -r comp_dir=../FestivalPlan/
declare -r files="
    filmids.txt
    films.csv
    screenings.csv
    sections.csv
    subsections.csv
    filminfo.xml
"
declare -r film_file=films.csv
declare -r tools_dir=~/Projects/FilmFestivalPlanner/Tools/

for file in $files;
    do echo $file
    if [ $file = $film_file ]; then
        $tools_dir/diff_films.sh . $comp_dir
    else
        diff $file $comp_dir
    fi
done
