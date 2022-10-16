#!/bin/bash

declare -r festival_year=$(basename $(dirname $(pwd)))
declare -r festival=${festival_year%%[0-9][0-9][0-9][0-9]}
declare -r year=${festival_year##${festival}}
declare -r festival_dir=~/Documents/Film/$festival/${festival}${year}
declare -r source_dir=$festival_dir/_planner_data
declare -r source_files="$source_dir/*.csv $source_dir/*.xml $source_dir/filmids.txt"
declare -r target_dir=$festival_dir/FestivalPlan
declare -r backup_dir=$target_dir/_bak
declare -r temp_dir=$target_dir/newbak

function confirm() {
    local -r question=$1
    local answer=
    printf "\n$question [ confirm ] "
    read answer
    if [  -n "$answer"  ]; then
        comment "Not confirmed"
        exit
    fi
}

if [ ! -d $source_dir ]; then
    echo "Source directory $source_dir not found."
    exit 1
fi

if [ ! -d $target_dir ]; then
    echo "Target directory $target_dir not found."
    exit 2
fi

if [ ! -d $backup_dir ]; then
    confirm "Create new backup directory $backup_dir?"
    mkdir $backup_dir
fi

echo "Source files:"
pushd $source_dir
ls -lt $(for source_file in $source_files; do basename $source_file; done)
popd

pushd $target_dir
mkdir $temp_dir
mv $backup_dir $temp_dir
cp -p *.csv *.xml $temp_dir
mv $temp_dir $backup_dir
popd

echo "Files saved in $backup_dir:"
ls -l $backup_dir

confirm "Continue copying source files to $target_dir?"
cp -p $source_files $target_dir

echo "Target directory:"
ls -l $target_dir
