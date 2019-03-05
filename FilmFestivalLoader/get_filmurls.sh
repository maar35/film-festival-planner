#!/bin/bash

declare -r command=$(basename $0)
declare -r error_log=${command}.err
declare -r project_dir="$HOME/Documents/Film/IFFR/IFFR2019"
declare -r filmurl_file="$project_dir/_planner_data/filmurls.txt"
declare -r films_dir=$project_dir/_website_data

declare html_file
declare stat

IFS=";"
while read -r id url; do
    html_file=$films_dir/$(printf "filmpage_%03d.html" $id)
    curl "$url" >$html_file
    stat=$?
    if [ $stat -ne 0 ]; then
        echo "ERROR ($stat) with id=$id creating $html_file" >$error_log
    fi
done <"$filmurl_file" 
