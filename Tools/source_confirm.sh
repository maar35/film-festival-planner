#!/bin/bash
#
# source_confirm
#   Source file to source function confirm().

. source_comment.sh

function confirm() {
    local -r question=${1-Continue?}
    local answer=
    printf "\n$question [ confirm ] "
    read answer
    if [ -n "$answer"  ]; then
        comment "Not confirmed"
        exit
    fi
}
