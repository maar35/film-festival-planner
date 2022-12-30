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

function max_sequence_nr() {
    local archive_files=$(ls $archive_dir/$archive_pattern 2>/dev/null)
    if [ archive_files = "" ]; then
        echo 0
        return
    fi
    for archive_file in $archive_files; do
        local archive_base=$(basename $archive_file .gz)
        local nr=${archive_base##*_}
        echo $nr
    done | sort -r | sed -e 's/^0*//' -e 1q
}
function next_sequence_nr() {
    declare -ir  max_nr=$(max_sequence_nr)
    printf "%02s" $(expr $max_nr + 1)
}
function bak_dir_source_count() {
    ls $bak_dir/$source_pattern 2>/dev/null | wc -w
}
function rel_path() {
    local abs_dir=$1
    python -c "import os.path; print(os.path.relpath('$($pwd)' '$abs_dir'))"
}
function comment() {
    local message=$1
    local time_stamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "$time_stamp  $message"
}

comment "Archiving $source_pattern files in $(rel_path $bak_dir)"

comment "Checking directories"
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

comment "Setting new archive name"
declare -r sequence_nr=$(next_sequence_nr)
declare -r archive_name=webdata_${sequence_nr}.gz
declare -r archive_path=$archive_dir/$archive_name

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

comment "Done."
