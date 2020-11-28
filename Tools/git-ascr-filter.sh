#!/bin/sh

if [ $# -ne 2 ]; then
    echo "Usage: $0 --clean/--smudge FILE">&2
    exit 1
fi

declare -r mode=${1:?}
declare -r file=${2:?}
declare tmpfile

if [ "$mode" = "--clean" ]; then
    osadecompile "$file" | sed 's/[[:space:]]*$//'
elif [ "$mode" = "--smudge" ]; then
    tmpfile=`mktemp -t tempXXXXXX`
    if [ $? -ne 0 ]; then
        echo "Error: \`mktemp' failed to create a temporary file.">&2
        exit 3
    fi
    if ! mv "$tmpfile" "$tmpfile.scpt" ; then
        echo "Error: Failed to create a temporary SCPT file.">&2
        rm "$tmpfile"
        exit 4
    fi
    tmpfile="$tmpfile.scpt"
    # Compile the AppleScript source on stdin.
    if ! osacompile -l AppleScript -o "$tmpfile" "$file"; then
        rm "$tmpfile"
        exit 5
    fi
    cat "$tmpfile" && rm "$tmpfile"
else
    echo "Error: Unknown mode '$mode'">&2
    exit 2
fi

