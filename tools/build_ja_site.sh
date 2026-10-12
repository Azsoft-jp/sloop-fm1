#!/bin/sh
# Build the local browser updater for this fork's SLOOP 2.6 Japanese UI.
set -eu
cd "$(dirname "$0")/.."
sh build.sh --release 2.6-ja
SLOOP_ONLINE_URL="${SLOOP_ONLINE_URL:-http://127.0.0.1:8766/}" \
    python3 web/make_site.py build/felucca-2.6-ja.fwsc 2.6-ja dist/ja-2.6
(cd dist/ja-2.6 && shasum -a 256 firmware/sloop-2.6-ja.fwsc > SHA256SUMS)
python3 tests/site_test.py
