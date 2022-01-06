#!/bin/bash

declare -r old_dir=${1:-FestivalPlan}
declare -r new_dir=${2:-_planner_data}
declare -r festival_year=$(basename $(dirname $(pwd)))
declare -r festival=${festival_year:0:4}
declare -r year=${festival_year:4:4}
declare -r documents_dir=~/Documents/Film/${festival}/${festival_year}
declare -r csv_file=films.csv

cd $documents_dir
echo "$old_dir <> $new_dir"
diff <(cut -d";" -f2- $old_dir/$csv_file | sort -k1n) <(cut -d";" -f2- $new_dir/$csv_file | sort -k1n)
