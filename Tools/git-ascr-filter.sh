#!/bin/sh

if [ $# -ne 2 ]; then
    echo "Usage: $0 --clean/--smudge FILE">&2
    exit 1
fi

declare -r mode=${1:?}
declare -r ascr_file=${2:?}

if [ "$mode" = "--clean" ]; then
    osadecompile "$ascr_file" | sed 's/[[:space:]]*$//'
elif [ "$mode" = "--smudge" ]; then
    declare -r tmpfile=`mktemp -t tempXXXXXX`
    if [ $? -ne 0 ]; then
        echo "Error: \`mktemp' failed to create a temporary file.">&2
        exit 3
    fi
    declare -r scpt_tmpfile=$tmpfile.scpt
    if ! mv "$tmpfile" "$scpt_tmpfile" ; then
        echo "Error: Failed to create a temporary SCPT file.">&2
        rm "$tmpfile"
        exit 4
    fi
    # Compile the AppleScript source on stdin.
    if ! osacompile -l AppleScript -o "$scpt_tmpfile" "$ascr_file"; then
        rm "$scpt_tmpfile"
        exit 5
    fi
    cat "$scpt_tmpfile" && rm "$scpt_tmpfile"
else
    echo "Error: Unknown mode '$mode'">&2
    exit 2
fi

