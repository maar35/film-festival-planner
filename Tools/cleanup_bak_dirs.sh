#!/bin/bash

declare -r root_dir=~/Documents/Film
declare -r plan_dir=FestivalPlan

. source_confirm.sh

function rel_path() {
    local -r abs_dir=$1
    local -r base_dir=${2:-$root_dir}
    cmd="print(os.path.relpath('$abs_dir', start='$base_dir'))"
    python -c "import os.path; $cmd"
}

for dir in $root_dir/*/*/$plan_dir; do
    comment "Cleanup $(rel_path $dir)"
    confirm
    cd $dir
    archive_bak_dirs.sh
done
