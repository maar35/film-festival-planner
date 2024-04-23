#!/bin/bash

declare -r title_fragment=${*}

declare -r cmd=$(basename $0)
declare -r usage="USAGE: $cmd word ..."
declare -r base_dir=~/Documents/Film/
declare -r search_dir=FestivalPlan
declare -r exclude_dir=_bak
declare -r films_fn=films.csv
declare -r attendance_fn="Screenings Summary.csv"

err=
[ $# -eq 0 ] && err="Argument count ($#)"

if [ -n "$err" ]; then
    echo "$0: $err" >&2
    echo $usage >&2
    exit 1
fi

cd $base_dir
find . "(" -name "$films_fn" -or -name "$attendance_fn" ")" \
    -and -path "*$search_dir*" -and -not -path "*$exclude_dir*" \
    -exec grep -Hi "$title_fragment" {} \;
