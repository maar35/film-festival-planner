#!/bin/bash
#
# source_next_archive_nr.sh:
#   Function `next_sequence_nr()` returns the next number in the sequence
#   of the given numbered archives with names like path_002.gz).

function next_sequence_nr() {
    local -r archive_patterns=${*:?}
    local -r archive_files=$(ls $archive_patterns 2>/dev/null)
    local -ri max_nr=$(max_sequence_nr "$archive_files")
    expr $max_nr + 1
}

function max_sequence_nr() {
    local -r archive_files=${1}
    if [ -z "$archive_files" ]; then
        echo 0
        return
    fi
    for archive_file in $archive_files; do
        local archive_base=$(basename $archive_file .gz)
        local nr=${archive_base##*_}
        echo $nr
    done | sort -r | sed -e 's/^0*//' -e 1q
}

