#!/bin/bash

declare -r project_dir="$HOME/Documents/Film/NFF/NFF2020"
declare -r webdata_dir=$project_dir/_website_data
declare -r webdata_filename_format="$webdata_dir/azpage_%02d.html"
declare -r azurl_root="https://www.filmfestival.nl/films/"
declare -r azurl_leave_format="?s=&hPP=48&idx=prod_films&nr=%02d"
declare -r dump_fn=$webdata_dir/$(basename $0 .sh).dump
declare -r page_count=5

declare url_leaves=
declare page_number=0
declare url

function check_make_dir() {
    local -r dir=$1
    [ -d $dir ] || mkdir $dir
}

check_make_dir $project_dir
check_make_dir $webdata_dir

for ((n=0; n<$page_count; n++)); do
    url_leaves="$url_leaves $(printf "$azurl_leave_format" $n)"
done

for url_leave in $url_leaves; do
    url=$azurl_root/$url_leave
    echo "$(date +"%Y-%m-%d %H:%M:%S") trace $url in $dump_fn.$page_number"
    curl --trace-ascii $dump_fn.$page_number "$url" -o $(printf "$webdata_filename_format" $page_number)
    (( ++page_number ))
done

