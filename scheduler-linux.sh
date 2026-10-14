#!/usr/bin/env bash
# Cloudflare DDNS - Linux scheduler (cron) installer / runner.
#
#   ./scheduler-linux.sh install   # create .venv, install deps, add cron entry
#   ./scheduler-linux.sh remove    # remove the cron entry
#   ./scheduler-linux.sh run       # run one update now (default)
#
# Interval via env: INTERVAL_MINUTES=15 ./scheduler-linux.sh install
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_DIR/.venv"
CRON_MARK="# cloudflare-ddns"
INTERVAL_MINUTES="${INTERVAL_MINUTES:-5}"

if ! [[ "$INTERVAL_MINUTES" =~ ^[1-9][0-9]?$ ]] || [ "$INTERVAL_MINUTES" -gt 59 ]; then
    echo "INTERVAL_MINUTES must be 1-59 (got: $INTERVAL_MINUTES)" >&2
    exit 1
fi

CRON_LINE="*/$INTERVAL_MINUTES * * * * $VENV_DIR/bin/python $PROJECT_DIR/__main__.py >> $PROJECT_DIR/ddns.log 2>&1"

usage() {
    echo "Usage: $0 {install|remove|run}"
    echo "  install  create .venv, install requirements, add cron entry (every ${INTERVAL_MINUTES} min)"
    echo "  remove   remove the cron entry"
    echo "  run      run one update now"
}

install() {
    [ -f "$PROJECT_DIR/config.json" ] || { echo "config.json not found in $PROJECT_DIR" >&2; exit 1; }
    [ -f "$PROJECT_DIR/.env" ] || echo "warning: .env not found; CF_API_KEY must be exported" >&2
    command -v python3 >/dev/null || { echo "python3 not found" >&2; exit 1; }

    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet -r "$PROJECT_DIR/requirements.txt"

    {
        crontab -l 2>/dev/null | grep -v -F "$CRON_MARK" | grep -v -F "$CRON_LINE" || true
        printf '%s\n%s\n' "$CRON_MARK" "$CRON_LINE"
    } | crontab -

    echo "Installed cron entry (every ${INTERVAL_MINUTES} min):"
    echo "  $CRON_LINE"
    echo "Logs: $PROJECT_DIR/ddns.log"
}

remove() {
    crontab -l 2>/dev/null | grep -v -F "$CRON_MARK" | grep -v -F "$CRON_LINE" | crontab - || true
    echo "Removed cloudflare-ddns cron entry (if present)."
}

case "${1:-run}" in
    install) install ;;
    remove)  remove ;;
    run)     "$VENV_DIR/bin/python" "$PROJECT_DIR/__main__.py" ;;
    *)       usage; exit 1 ;;
esac