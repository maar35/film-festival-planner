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
function comment() {
    local message=$1
    local time_stamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "$time_stamp  $message"
}

comment "Archiving $source_pattern files in $bak_dir"

comment "Checking directories"
if [ ! -d $bak_dir ]; then
    comment "Source directory $bak_dir not found"
    exit 1
fi

if [ ! -d $archive_dir ]; then
    mkdir $archive_dir
    comment "Target directory $archive_dir created"
fi

comment "Checking source files"
declare -r source_count=$(ls $bak_dir/$source_pattern | wc -w)
if [ $source_count -eq 0 ]; then
    comment "No $source_pattern files found"
    exit 3
fi

comment "Listing archive directory $archive_dir"
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

comment "Archiving to $archive_path"
tar -cjf $archive_path $source_pattern
if [ $? -ne 0 ]; then
    comment "Archiving failed"
    exit 5
fi

comment "Listing archive directory $archive_dir"
ls -l $archive_dir

comment "Removing source files $source_pattern from $bak_dir"
rm $bak_dir/$source_pattern

comment "Done."
