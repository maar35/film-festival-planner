#!/bin/bash

declare -r project_dir="$HOME/Documents/Film/IFFR/IFFR2020"
declare -r films_dir=$project_dir/_website_data
declare -r azurl_dir="https://iffr.com/nl/programma/2020"
declare -r page_count=4

declare url_pages="a-z"
declare page_number=0
declare url

function check_make_dir() {
    local -r dir=$1
    [ -d $dir ] || mkdir $dir
}

check_make_dir $project_dir
check_make_dir $films_dir

for ((n=1; n<$page_count; n++)); do
    url_pages="$url_pages a-z?page=$n"
done

for url_page in $url_pages; do
    url=$azurl_dir/$url_page
    echo "$(date +"%Y-%m-%d %H:%M:%S") $url"
    curl "$url" > $films_dir/$(printf "azpage_%02d.html" $page_number)
    (( ++page_number ))
done

