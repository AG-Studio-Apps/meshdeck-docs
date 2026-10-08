#!/usr/bin/env bash
# Signs templates.json with the OFFLINE emergency key (plan-s4-templates.md 4.5), for when the
# primary key in CI is leaked or lost. The publish workflow sees the committed
# templates.json.minisig, checks it against keys/catalog-emergency.pub and publishes it as is
# (the signing job still needs its approval, but uses no secret).
#
#   scripts/sign-emergency.sh --key /media/usb1/catalog-emergency/emergency.key
#   scripts/sign-emergency.sh --key FILE --dry-run      # restore test: signs a probe only
#
# Run it on a trusted machine (not the agent box), from a clone of this repository with the
# new catalogue already in templates.json. It refuses unless:
#   - every catalogue gate passes (scripts/check-catalog.py),
#   - templates.json's version is ABOVE the live one (fetched with a cache-busting query),
#   - the signature verifies against keys/catalog-emergency.pub with the trusted comment
#     `catalog=templates version=<n>`.
# Only then is templates.json.minisig written. minisign asks for the key's passphrase (from the
# password manager). Then commit templates.json and templates.json.minisig together and push
# to main. After the incident, the next catalogue change must delete templates.json.minisig
# (the gates refuse a committed signature that no longer matches).
#
# --dry-run is the restore test (once at setup and once a year, from the offline copy): it
# signs a throwaway probe with the key and verifies it against keys/catalog-emergency.pub.
# Nothing in the repository is touched and nothing is fetched.
#
# Incident hygiene: when the primary key leaked, assume the repository (and this box's GitHub
# token) may be compromised too. This script and the gates it runs are repository code, run on
# the machine that holds the emergency key while you type its passphrase. So run it only from a
# clone whose scripts/ and keys/ match a commit you have reviewed: it refuses uncommitted changes
# there and prints both tree ids, to compare with the ids recorded when the pipeline was reviewed
# (or run the copy of this script kept with the offline key). Prefer a fresh clone over an old one.
#
# For tests only: --pub FILE verifies against another public key, --live-file FILE stands in
# for the live templates.json, and --no-gates skips the gates.
set -euo pipefail
umask 077

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LIVE_URL="https://meshdeck.ag-applications.com/templates.json"
KEY=""
PUB="$REPO_DIR/keys/catalog-emergency.pub"
DRY_RUN=0
LIVE_FILE=""
GATES=1

usage() { sed -n '6,7p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --key) shift; KEY="${1:-}" ;;
    --dry-run) DRY_RUN=1 ;;
    --pub) shift; PUB="${1:-}" ;;
    --live-file) shift; LIVE_FILE="${1:-}" ;;
    --no-gates) GATES=0 ;;
    -h|--help) usage ;;
    *) echo "unknown argument $1" >&2; usage ;;
  esac
  shift
done

for tool in minisign python3; do
  command -v "$tool" >/dev/null || { echo "$tool is not installed" >&2; exit 1; }
done
[ -n "$KEY" ] || { echo "--key FILE is required (the emergency secret key, from the offline copy)" >&2; usage; }
[ -f "$KEY" ] || { echo "no key file at $KEY" >&2; exit 2; }
[ -f "$PUB" ] || { echo "no public key at $PUB" >&2; exit 1; }
if head -n 1 "$KEY" | grep -qi 'public key'; then
  echo "$KEY is a public key; --key takes the SECRET key file" >&2; exit 2
fi
case "$(cd "$(dirname "$KEY")" && pwd)/" in
  "$HOME/appfactory/"*) echo "warning: the emergency key should not live under ~/appfactory (agents on the build box can read it)" >&2 ;;
esac

key_id() { python3 -c 'import base64, sys; b = base64.b64decode(open(sys.argv[1]).read().splitlines()[1]); print(b[2:10][::-1].hex().upper())' "$1"; }
PUB_ID="$(key_id "$PUB")"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- Restore test ------------------------------------------------------------------------
if [ "$DRY_RUN" -eq 1 ]; then
  printf '{"probe": "emergency restore test", "at": "%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$TMP/probe.json"
  echo "Signing a probe with $KEY (minisign asks for its passphrase)."
  minisign -S -s "$KEY" -m "$TMP/probe.json" -x "$TMP/probe.json.minisig" -t "catalog restore test" >/dev/null
  if minisign -V -q -p "$PUB" -m "$TMP/probe.json" -x "$TMP/probe.json.minisig"; then
    echo "OK: the emergency key signs, and its signature verifies against $(basename "$PUB") (key id $PUB_ID)."
    echo "Nothing was written to the repository."
    exit 0
  fi
  echo "FAILED: this key does not match $(basename "$PUB") (key id $PUB_ID)." >&2
  exit 1
fi

# --- Emergency signature -----------------------------------------------------------------
if git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  if [ -n "$(git -C "$REPO_DIR" status --porcelain -- scripts keys)" ]; then
    echo "refusing: scripts/ or keys/ have uncommitted changes; sign only from reviewed code" >&2
    git -C "$REPO_DIR" status --short -- scripts keys >&2
    exit 1
  fi
  echo "Code in use: commit $(git -C "$REPO_DIR" rev-parse --short=12 HEAD), scripts/ tree $(git -C "$REPO_DIR" rev-parse --short=12 HEAD:scripts), keys/ tree $(git -C "$REPO_DIR" rev-parse --short=12 HEAD:keys)."
  echo "Compare them with the ids recorded for the reviewed pipeline before typing the passphrase."
else
  echo "warning: $REPO_DIR is not a git clone; the code in use cannot be checked" >&2
fi
CATALOG="$REPO_DIR/templates.json"
SIG="$REPO_DIR/templates.json.minisig"
[ -f "$CATALOG" ] || { echo "no templates.json in $REPO_DIR" >&2; exit 1; }
[ -e "$SIG" ] && { echo "$SIG already exists; delete it first if you mean to re-sign" >&2; exit 1; }

version="$(python3 -c 'import json, sys; v = json.load(open(sys.argv[1]))["version"]; assert type(v) is int and v > 0; print(v)' "$CATALOG")" \
  || { echo "templates.json has no positive integer version" >&2; exit 1; }

if [ -n "$LIVE_FILE" ]; then
  cp "$LIVE_FILE" "$TMP/live.json"
else
  command -v curl >/dev/null || { echo "curl is not installed" >&2; exit 1; }
  curl -fsS --max-time 20 -H 'Cache-Control: no-cache' "$LIVE_URL?r=$(date +%s)$RANDOM" -o "$TMP/live.json" \
    || { echo "cannot fetch the live catalogue from $LIVE_URL; refusing (the version must be checked)" >&2; exit 1; }
fi
live="$(python3 -c 'import json, sys; v = json.load(open(sys.argv[1]))["version"]; assert type(v) is int; print(v)' "$TMP/live.json")" \
  || { echo "the live catalogue has no integer version; refusing" >&2; exit 1; }
if [ "$version" -le "$live" ]; then
  echo "refusing: templates.json is version $version, the live catalogue is version $live." >&2
  echo "An emergency signature must publish a NEWER version (the apps refuse a rollback, and the same" >&2
  echo "version with different bytes). Set \"version\" to $((live + 1)) and run again." >&2
  exit 1
fi
[ "$version" -eq $((live + 1)) ] || echo "note: version $version skips ahead of live $live + 1; the publish gate requires deployed + 1." >&2

if [ "$GATES" -eq 1 ]; then
  echo "Running the catalogue gates."
  python3 "$REPO_DIR/scripts/check-catalog.py" || { echo "refusing: the gates fail; an emergency signature must not cover them" >&2; exit 1; }
fi

comment="catalog=templates version=$version"
echo "Signing templates.json version $version with the emergency key (minisign asks for its passphrase)."
minisign -S -s "$KEY" -m "$CATALOG" -x "$TMP/templates.json.minisig" -t "$comment" >/dev/null

minisign -V -q -p "$PUB" -m "$CATALOG" -x "$TMP/templates.json.minisig" \
  || { echo "FAILED: the signature does not verify against $(basename "$PUB") (key id $PUB_ID). Wrong key?" >&2; exit 1; }
got="$(sed -n 3p "$TMP/templates.json.minisig")"
[ "$got" = "trusted comment: $comment" ] || { echo "FAILED: trusted comment is '$got'" >&2; exit 1; }

mv "$TMP/templates.json.minisig" "$SIG"
chmod 644 "$SIG"
echo
echo "Wrote templates.json.minisig: version $version, emergency key $PUB_ID, verified."
echo "Next:"
echo "  git add templates.json templates.json.minisig"
echo "  git commit -m \"Catalogue v$version (emergency signature)\""
echo "  git push origin main      # then approve the catalog-signing job"
echo "After the incident, delete templates.json.minisig in the next catalogue change."
