#!/bin/bash

declare -r festival_year=$(basename $(dirname $(pwd)))
declare -r festival=${festival_year%%[0-9][0-9][0-9][0-9]}
declare -r year=${festival_year##${festival}}
declare -r festival_dir=~/Documents/Film/$festival/${festival}${year}
declare -r plan_dir=FestivalPlan
declare -r root_dir=$festival_dir/$plan_dir
declare -r backup_dir=$root_dir/_bak
declare -r archive_dir=$root_dir/_archive

declare -ix archive_nr=0

. source_confirm.sh

function main() {
    comment "Recursively archive $festival_year '$plan_dir/_bak' hierarchy"
    if [ ! -d $backup_dir ]; then
        echo "No $(rel_path $backup_dir) dir found"
        comment "Stop archiving $festival_year"
        exit
    fi

    if [ ! -d $archive_dir ]; then
        mkdir $archive_dir
        comment "Target directory $(rel_path $archive_dir) created"
    fi

    cd $backup_dir
    traverse_bakckup_dirs $PWD 0
    comment "Done with $festival_year"
}

function traverse_bakckup_dirs() {
    local -r dir=${1:?}
    local -i depth=${2:?}
    local -r source_dir=$PWD
    local -x at_bottom=1

    trap "
        trap 0
        at_bottom=0
    " ERR

    cd "$PWD"/_bak* 2>/dev/null

    if [ $at_bottom -ne 0 ]; then
        (( depth += 1 ))
        traverse_bakckup_dirs "$PWD" $depth
    else
        echo "Go archive, depth=$depth"
    fi

    (( archive_nr += 1 ))
    if archive_bak_dir $archive_nr; then
        cd ..
        rm -r "$source_dir"
    else
        exit 2
    fi
}

function archive_bak_dir() {
    local -ri archive_nr=${1:?}
    local -r archive_postfix=_$(printf "%03s" $archive_nr)
    local -r archive_name=planner_data${archive_postfix}.gz
    local -r archive_path=$archive_dir/$archive_name

    if [ -f $archive_path ]; then
        comment "Archive $archive_name already exists"
        confirm
    fi

    comment "Archiving $(rel_path "$PWD") to $archive_name"
    tar -cjf $archive_path ./*
    result=$?
    if [ $result -ne 0 ]; then
        comment "ERROR, archive failed"
        confirm
    fi
    true
}

function rel_path() {
    local -r abs_dir=$1
    local -r base_dir=${2:-$root_dir}
    cmd="print(os.path.relpath('$abs_dir', start='$base_dir'))"
    python -c "import os.path; $cmd"
}

main

