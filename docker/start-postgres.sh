#!/bin/sh
set -eu
# Generate once inside a Docker volume, never in the repository or build context.
if [ ! -s /run/db-secret/password ]; then
  umask 022
  head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > /run/db-secret/password
fi
exec docker-entrypoint.sh postgres
