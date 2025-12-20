#!/bin/bash

declare -r festival_year=$(basename $(dirname $(pwd)))
declare -r festival=${festival_year%%[0-9][0-9][0-9][0-9]}
declare -r year=${festival_year##${festival}}
declare -r festival_dir=~/Documents/Film/$festival/${festival}${year}
declare -r source_pattern="*.html"
declare -r source_dir=$festival_dir/_website_data
declare -r bak_dir=$source_dir/_bak
declare -r archive_dir=$bak_dir/_archive
declare -r archive_pattern="*.gz"

. source_comment.sh
. source_next_archive_nr.sh

function main() {
    comment "Archiving $source_pattern files in $(rel_path $bak_dir)"

    comment -n "Checking directories"
    if [ ! -d $bak_dir ]; then
        mkdir $bak_dir
        comment "Source directory $(rel_path $bak_dir) created"
    fi

    if [ ! -d $archive_dir ]; then
        mkdir $archive_dir
        comment "Target directory $(rel_path $archive_dir) created"
    fi

    comment "Checking source files"
    if [ $(bak_dir_source_count) -eq 0 ]; then
        comment "Moving $source_pattern files to empty $(rel_path $bak_dir)"
        mv $source_dir/$source_pattern $bak_dir 2>/dev/null
    fi
    if [ $(bak_dir_source_count) -eq 0 ]; then
        comment "No $source_pattern files found to archive"
        exit 3
    fi

    comment "Listing archive directory $(rel_path $archive_dir)"
    ls -l $archive_dir

    comment "Archiving HTML files"
    archive_html_files

    comment "Done."
}

function archive_html_files() {
    local -ri sequence_nr=$(next_sequence_nr $archive_dir/$archive_pattern)
    local -r archive_postfix=_$(printf "%02s" $sequence_nr).gz
    local -r archive_name=webdata${archive_postfix}
    local -r archive_path=$archive_dir/$archive_name

    if [ -f $archive_path ]; then
        comment "Archive $archive_path already exists"
        exit 4
    fi

    cd $bak_dir

    comment "Archiving to $(rel_path $archive_path)"
    tar -cjf $archive_path $source_pattern
    if [ $? -ne 0 ]; then
        comment "Archiving failed"
        exit 5
    fi

    comment "Listing archive directory $(rel_path $archive_dir)"
    ls -l $archive_dir

    comment "Removing source files $source_pattern from $(rel_path $bak_dir)"
    rm $bak_dir/$source_pattern

}

function bak_dir_source_count() {
    ls $bak_dir/$source_pattern 2>/dev/null | wc -w
}

function rel_path() {
    local abs_dir=$1
    python -c "import os.path; print(os.path.relpath('$($pwd)' '$abs_dir'))"
}

main

