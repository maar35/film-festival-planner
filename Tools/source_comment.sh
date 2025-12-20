#!/bin/bash
#
# source_comment
#   Source file to source function comment().

function comment() {
    local -r cmd=$(basename $0)
    local -r USAGE="Usage: $cmd [-n] message"
    local -r time_stamp=$(date +"%Y-%m-%d %H:%M:%S")

    local prefix="\n"
    local err=

    OPTIND=1
    while getopts n c; do
        case "$c"
        in n )  prefix=""       # Suppress prefixed newline before message
        ;; * )  err="Error while parsing options ($*)"
        esac
    done
    shift $(expr $OPTIND - 1)

    [ $# -gt 1 ]    && err="Argument count ($#)"

    if [ -n "$err" ]; then
        printf "$0: $err!\n$USAGE" >&2
        exit 1
    fi

    local -r message=$1

    printf "$prefix$time_stamp  $message\n"
}
