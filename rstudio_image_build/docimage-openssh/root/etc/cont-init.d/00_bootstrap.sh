#!/usr/bin/with-contenv /bin/sh

set -e

#User params

#Internal params
if [ -z "$BOOTSTRAP_COMMAND" ]; then
	RUN_CMD="/bin/true"
else
	RUN_CMD=${BOOTSTRAP_COMMAND}
fi

# Test for Interactiveness
if test -t 0; then
  $RUN_CMD

  if [ "$@" ]; then
    eval "$@"
  else
    export PS1='[\u@\h : \w]\$ '
    /bin/sh
  fi

else
  if [ "$@" ]; then
    eval "$@"
  fi
  $RUN_CMD
fi