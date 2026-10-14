#!/bin/sh
# Run the updater periodically until the container is stopped.
set -eu

interval="${UPDATE_INTERVAL:-300}"
stamp() { date +"[%H:%M - %d.%m.%Y]: "; }

echo "$(stamp)Starting Cloudflare DDNS updater (every ${interval}s)"

while true; do
    "$@" || echo "$(stamp)update failed (exit $?); will retry in ${interval}s"
    sleep "$interval"
done