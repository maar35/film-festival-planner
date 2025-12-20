#!/bin/bash

declare -r festival_year=$(basename $(dirname $(pwd)))
declare -r festival=${festival_year%%[0-9][0-9][0-9][0-9]}
declare -r year=${festival_year##${festival}}
declare -r festival_dir=~/Documents/Film/$festival/$festival_year
declare -r root_dir=$festival_dir
declare -r source_dir=$festival_dir/_planner_data
declare -r source_files="$source_dir/*.csv $source_dir/filmids.txt $source_dir/*.yml"
declare -r target_dir=$festival_dir/FestivalPlan
declare -r archive_dir=$target_dir/_archive
declare -r archive_pattern="*.gz"
declare -r save_pattern="./*.csv ./*.txt ./*.yml"

. source_comment.sh
. source_confirm.sh
. source_next_archive_nr.sh

function main() {
    local -r rel_target_path=$(rel_path $target_dir)
    comment "Copying planner data of $festival_year to $rel_target_path"
    if [ ! -d $source_dir ]; then
        echo "Source directory $source_dir not found."
        exit 1
    fi

    if [ ! -d $target_dir ]; then
        echo "Target directory $target_dir not found."
        exit 2
    fi

    echo "Source files in $(rel_path $source_dir):"
    cd $source_dir
    ls -lt $(for source_file in $source_files; do basename $source_file; done)
    cd - >/dev/null

    echo
    echo "Target directory $(rel_path $target_dir):"
    ls -lt $target_dir

    comment "Archiving $(rel_path $target_dir)"
    archive

    confirm "Continue copying source files to $(rel_path $target_dir)?"
    cp -p $source_files $target_dir

    echo "Target directory after copy:"
    ls -lt $target_dir

    comment "Done saving planner data of $festival_year"
}

function archive() {
    local -ri archive_nr=$(next_sequence_nr "$archive_dir/$archive_pattern")
    local -r archive_postfix=_$(printf "%03s" $archive_nr).gz
    local -r archive_name=planner_data${archive_postfix}
    local -r archive_path=$archive_dir/$archive_name

    if [ ! -d $archive_dir ]; then
        confirm "Create new archive directory $archive_dir?"
        mkdir $archive_dir
    fi

    comment -n "Archiving to $(rel_path $archive_path)"
    cd $target_dir
    tar -cjf $archive_path $save_pattern
    if [ $? -ne 0 ]; then
        comment "Archiving failed"
        exit 3
    fi
}

function rel_path() {
    local -r abs_dir=$1
    local -r base_dir=${2:-$root_dir}
    cmd="print(os.path.relpath('$abs_dir', start='$base_dir'))"
    python -c "import os.path; $cmd"
}

main

