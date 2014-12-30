#!/usr/bin/env bash

function apply_patch {
    patch -p0 -N --dry-run --silent $1 < $2 2>/dev/null
    #If the patch has not been applied then the $? which is the exit status 
    #for last command would have a success status code = 0
    if [ $? -eq 0 ];
    then
        #apply the patch
        echo 'Applied patch'
        patch -p0 -N $1 < $2
    fi
    return
}
apply_patch $1 $2
exit
