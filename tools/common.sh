#!/usr/bin/env bash

function ssh_key_gen {
  if [[ -f ${HOME}/.ssh/id_rsa && -f ${HOME}/.ssh/id_rsa.pub ]]; then
    return 0
  else
    if [ ! -d ${HOME}/.ssh ]; then
      mkdir -p  ${HOME}/.ssh
    fi
    ssh-keygen  -f ${HOME}/.ssh/id_rsa -t rsa -N ''
  fi
}

function source_file_ssh_agent {
  cat <<EOF > /etc/profile.d/ssh-agent
if [ -f ~/.ssh-agent ]; then
  source ~/.ssh-agent
fi
EOF
}

function start_ssh_agent {
  ssh-add -l &>/dev/null
  if [ "$?" == 2 ]; then
    test -r ~/.ssh-agent && \
      eval "$(<~/.ssh-agent)" >/dev/null

    ssh-add -l &>/dev/null
    if [ "$?" == 2 ]; then
      (umask 066; ssh-agent > ~/.ssh-agent)
      eval "$(<~/.ssh-agent)" >/dev/null
      ssh-add
    fi
  fi
}

function prepare {
  if [ -n "$config_file" ]; then
    config_file=`readlink -f "$config_file"`
    export TEST_CONFIG_DIR=`dirname "$config_file"`
    export TEST_CONFIG_FILE=`basename "$config_file"`
  fi

  if [ ! -f "$config_file" ]; then
    python tools/configure.py $(readlink -f .) -p $contrail_fab_path
  fi
  ssh_key_gen
  start_ssh_agent
  source_file_ssh_agent
}
