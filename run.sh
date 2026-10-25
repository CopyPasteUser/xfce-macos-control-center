#!/usr/bin/env bash
set -u
HERE="$(cd "$(dirname "$0")" && pwd)" || exit 1
case "${1:-}" in
  --direct)
    shift
    exec python3 "$HERE/macos-control-center" "$@"
    ;;
  --daemon)
    exec python3 "$HERE/macos-control-center" "$@"
    ;;
esac
# Default to the same self-healing resident toggle used by the installed menu entry.
exec bash "$HERE/macos-control-center-toggle" "$@"
