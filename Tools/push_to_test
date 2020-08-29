#!/bin/bash

declare -r currbranch=$(git branch | grep -F "*" | cut -d" " -f2)
declare -r testbranch=test
declare -r remote=origin

function comment() {
    local message=$1
    echo "$(date +"%Y-%m-%d %H:%M:%S")  - $message"
}
function err() {
    local -r errornr=${1:?}
    local -r message=${2:?}
    comment "Error $errornr: $message"
    exit $errornr
}
function confirm() {
    local -r question=$1
    local answer=
    printf "\n$question [confirm] "
    read answer
    if [ -n "$answer" ]; then
        comment "Not confirmed"
        exit
    fi
}

comment "Copy current branch '$currbranch' to '$testbranch' and push it to '$remote'."

comment "Check the current branch."
if [ $currbranch == $testbranch ]; then
    err 1 "Already on branch '$testbranch'"
fi

comment "Confirm the git status."
echo
git status
confirm "Continue copying branch to test?"

comment "Copy branch '$currbranch' to branch '$testbranch'."
git branch -C $currbranch $testbranch

comment "Switch to the test branch."
git checkout $testbranch

comment "Push the test branch to the remote repository."
git push $remote HEAD

comment "Switch back to the copied branch."
git checkout $currbranch

comment "Done."
