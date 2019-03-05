#!/bin/bash

declare -r project_dir="$HOME/Documents/Film/IFFR/IFFR2019"
declare -r films_dir=$project_dir/_website_data
declare -r url_dir="https://iffr.com/nl/programma/2019"

declare url_pages="a-z"
declare page_count=21
declare page_number=0

declare url
declare films_file

for ((n=1; n<=$page_count; n++)); do
    url_pages="$url_pages a-z?page=$n"
done

for url_page in $url_pages; do
    url=$url_dir/$url_page
    films_file=$films_dir/page${page_number}.html
    echo "$(date +"%Y-%m-%d %H:%M:%S") $url"
    curl "$url" > $films_file
    (( ++page_number ))
done

