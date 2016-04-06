#!/usr/bin/env bash

function prepare {
  if [ -n "$config_file" ]; then
    config_file=`readlink -f "$config_file"`
    export TEST_CONFIG_DIR=`dirname "$config_file"`
    export TEST_CONFIG_FILE=`basename "$config_file"`
  fi

  if [ ! -f "$config_file" ]; then
    python tools/configure.py $(readlink -f .) -p $contrail_fab_path
  fi

  #Start ssh-agent if not there
  if [ -z "$SSH_AUTH_SOCK" ] ; then
    eval `ssh-agent -s`
  fi
  if [ -z "$SSH_AUTH_SOCK" ] ; then
    echo "Error: SSH agent failed to start"
    exit 1
  fi
  ssh-add
}
