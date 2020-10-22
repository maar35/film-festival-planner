#!/bin/bash

declare -r workdir=/Users/maarten/Documents/Film/NFF/NFF2020/_website_data
declare -r file1=${1:-$workdir/azpage_00.html}
declare -r file2=${1:-$workdir/_py_Safari_605.1.15/azpage_00.html}

function split_tags() {
    local -r file=$1
    cat $file | tr ">" "\n" | sed 's/$/>/'
}

pwd
ls -l $file1 $file2
diff <(split_tags $file1) <(split_tags $file2)
