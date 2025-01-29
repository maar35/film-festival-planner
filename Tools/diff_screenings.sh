#!/bin/bash

declare -r old_dir=${1:-FestivalPlan}
declare -r new_dir=${2:-_planner_data}

declare -r cmd=$(basename $0)
declare -r usage="USAGE: $cmd old_dir new_dir"
declare -r csv_file=screenings.csv

err=
[ -n "$err" ] || [ $# -eq 2 ] || err="Argument count ($#)"
[ -n "$err" ] || [ -d  $old_dir ] || err="$old_dir is not a directory"
[ -n "$err" ] || [ -d  $new_dir ] || err="$new_dir is not a directory"
[ -n "$err" ] || [ -f  $old_dir/$csv_file ] || err="$old_dir/$csv_file not found"
[ -n "$err" ] || [ -f  $new_dir/$csv_file ] || err="$new_dir/$csv_file not found"

if [ -n "$err" ]; then
    echo "$0: $err" >&2
    echo $usage >&2
    exit 1
fi

echo "$old_dir/$csv_file <> $new_dir/$csv_file"
diff <(sort -t";" -k1n -k2n -k3 $old_dir/$csv_file) <(sort -t";" -k1n -k2n -k3 $new_dir/$csv_file)
