#!/usr/bin/env bash
# Generates the template catalogue's signing roster: a PRIMARY key (the publish
# workflow signs every catalogue with it) and an EMERGENCY key (kept offline;
# the apps trust it too, so a leaked or lost primary can be replaced without
# waiting for an app release). Adapted from stackGuard's provision-keys.sh.
#
#   scripts/provision-catalog-keys.sh --only primary   --set-secrets --backup DIR
#   scripts/provision-catalog-keys.sh --only primary   [--out DIR]
#   scripts/provision-catalog-keys.sh --only emergency  --out DIR
#   scripts/provision-catalog-keys.sh --restore-test ROLE SECRET_KEY_FILE
#
# PRIMARY
#   Run on a trusted machine with gh logged in. With --set-secrets the key and
#   its passphrase go straight into the `catalog-signing` ENVIRONMENT of the
#   catalogue repo (MINISIGN_KEY / MINISIGN_PASSWORD, fed on stdin, never on a
#   command line or clipboard). --backup DIR is then required: it writes a
#   recovery copy (primary.key, encrypted by minisign, and
#   primary.passphrase.age, that passphrase age-encrypted under a MASTER
#   passphrase you paste from your password manager when age asks) to DIR,
#   which must be off this box or on removable media (a path under ~/appfactory
#   is refused). The working copy here is destroyed. To recover after losing
#   the CI secret: age -d DIR/primary.passphrase.age gives the passphrase, and
#   DIR/primary.key plus that passphrase go back into the environment.
#   Without --set-secrets the key is kept in DIR (default
#   ~/appfactory/catalog_keys) with its passphrase age-encrypted under a master
#   passphrase you type once.
#
# EMERGENCY
#   Generate it on a machine OTHER than the build/agent box, straight onto
#   offline media (--out is required, and a path under ~/appfactory is
#   refused). It never goes into CI. Its minisign passphrase is printed ONCE:
#   put it in your password manager. Copy DIR to a second offline medium.
#
# Both roles: the public half is copied into keys/catalog-<role>.pub in this
# repository (public; anyone can verify a catalogue), and its key id and base64
# payload are printed for the apps' trusted-key roster (meshTerm's CatalogTrust).
# The two roles must never share a key id (the apps' verifier stops at the first
# id match), so the script refuses if they do.
#
# --restore-test ROLE FILE signs a probe with that secret key (minisign asks
# for its passphrase) and verifies it against keys/catalog-<role>.pub. Run it
# once after setup and once a year from the offline copy: an emergency key no
# one has opened since it was made is not a recovery path.
#
# Everything is built in a private temporary directory and kept only once the
# key has signed and verified a probe. It refuses to overwrite an existing key:
# move the old files aside to rotate.
set -euo pipefail
umask 077

[ "${BASH_VERSINFO[0]:-0}" -ge 4 ] || { echo "bash 4 or newer is needed (macOS: brew install bash)" >&2; exit 2; }

REPO="AG-Studio-Apps/meshdeck-docs"
ENVIRONMENT="catalog-signing"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT=""
SET_SECRETS=0
BACKUP=""
ROLE=""
RESTORE_ROLE=""
RESTORE_KEY=""

usage() { sed -n '7,9p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --only) shift; case "${1:-}" in primary|emergency) ROLE="$1" ;; *) echo "--only takes primary or emergency" >&2; exit 2 ;; esac ;;
    --out) shift; OUT="${1:-}"; [ -n "$OUT" ] || usage ;;
    --set-secrets) SET_SECRETS=1 ;;
    --backup) shift; BACKUP="${1:-}"; [ -n "$BACKUP" ] || usage ;;
    --restore-test) shift; RESTORE_ROLE="${1:-}"; shift || true; RESTORE_KEY="${1:-}" ;;
    -h|--help) usage ;;
    *) echo "unknown argument $1" >&2; usage ;;
  esac
  shift
done

for tool in minisign openssl; do
  command -v "$tool" >/dev/null || { echo "$tool is not installed" >&2; exit 1; }
done

key_id() { sed -n 1p "$1" | awk '{print $NF}'; }
payload() { sed -n 2p "$1"; }

# --- Restore test --------------------------------------------------------------
if [ -n "$RESTORE_ROLE" ]; then
  case "$RESTORE_ROLE" in primary|emergency) ;; *) echo "--restore-test takes primary or emergency" >&2; exit 2 ;; esac
  [ -f "$RESTORE_KEY" ] || { echo "secret key file not found: $RESTORE_KEY" >&2; exit 2; }
  pub="$REPO_DIR/keys/catalog-$RESTORE_ROLE.pub"
  [ -f "$pub" ] || { echo "$pub is missing" >&2; exit 1; }
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  echo '{"probe":"restore-test"}' > "$TMP/probe.json"
  echo "minisign will ask for the $RESTORE_ROLE key's passphrase."
  minisign -S -s "$RESTORE_KEY" -t "catalog restore test" -m "$TMP/probe.json" >/dev/null
  if minisign -V -q -p "$pub" -m "$TMP/probe.json" >/dev/null; then
    echo "OK: the $RESTORE_ROLE key signs, and its signature verifies against keys/catalog-$RESTORE_ROLE.pub (id $(key_id "$pub"))."
  else
    echo "FAILED: this key does not match keys/catalog-$RESTORE_ROLE.pub" >&2; exit 1
  fi
  exit 0
fi

# --- Generate ------------------------------------------------------------------
[ -n "$ROLE" ] || { echo "say which key: --only primary or --only emergency" >&2; usage; }

if [ "$ROLE" = emergency ]; then
  [ "$SET_SECRETS" -eq 0 ] || { echo "the emergency key never goes into CI; drop --set-secrets" >&2; exit 2; }
  [ -n "$OUT" ] || { echo "--out DIR is required for the emergency key (offline media, on a machine other than the build box)" >&2; exit 2; }
  case "$(cd "$(dirname "$OUT")" 2>/dev/null && pwd)/$(basename "$OUT")/" in
    "$HOME/appfactory/"*) echo "refusing: the emergency key must not be written under ~/appfactory (agents on this box can read it)" >&2; exit 2 ;;
  esac
else
  [ -n "$OUT" ] || OUT="$HOME/appfactory/catalog_keys"
  if [ "$SET_SECRETS" -eq 1 ]; then
    [ -n "$BACKUP" ] || { echo "--set-secrets needs --backup DIR (a recovery copy off this box, unlocked by a master passphrase from your password manager)" >&2; exit 2; }
    case "$(cd "$(dirname "$BACKUP")" 2>/dev/null && pwd)/$(basename "$BACKUP")/" in
      "$HOME/appfactory/"*) echo "refusing: the primary's recovery copy must not be written under ~/appfactory (agents on this box can read it)" >&2; exit 2 ;;
    esac
    command -v age >/dev/null || { echo "age is not installed (needed for the recovery copy)" >&2; exit 1; }
    mkdir -p "$BACKUP"; chmod 700 "$BACKUP"
    for f in "$BACKUP/primary.key" "$BACKUP/primary.passphrase.age"; do
      [ -e "$f" ] && { echo "$f already exists; move it aside to rotate" >&2; exit 1; }
    done
    command -v gh >/dev/null || { echo "gh is not installed" >&2; exit 1; }
    gh auth status >/dev/null 2>&1 || { echo "gh is not logged in" >&2; exit 1; }
  else
    command -v age >/dev/null || { echo "age is not installed (needed to keep the primary locally)" >&2; exit 1; }
  fi
fi

mkdir -p "$OUT"
chmod 700 "$OUT"
for f in "$OUT/$ROLE.key" "$OUT/$ROLE.pub" "$OUT/$ROLE.passphrase.age"; do
  [ -e "$f" ] && { echo "$f already exists; move it aside to rotate" >&2; exit 1; }
done

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
chmod 700 "$TMP"

# 33 random bytes: 44 base64 characters. minisign encrypts the secret key with
# it (scrypt), so the .key file is useless without it.
PASS="$(openssl rand -base64 33 | tr -d '\n')"
printf '%s\n%s\n' "$PASS" "$PASS" \
  | minisign -G -p "$TMP/$ROLE.pub" -s "$TMP/$ROLE.key" -c "template catalogue $ROLE signing key" >/dev/null
chmod 600 "$TMP/$ROLE.key" "$TMP/$ROLE.pub"

# Prove the key signs and its public half verifies before anything is kept.
echo '{"probe":true}' > "$TMP/probe.json"
printf '%s\n' "$PASS" | minisign -S -s "$TMP/$ROLE.key" -t "catalog probe" -m "$TMP/probe.json" >/dev/null
minisign -V -q -p "$TMP/$ROLE.pub" -m "$TMP/probe.json" >/dev/null || { echo "$ROLE key failed to verify" >&2; exit 1; }

# The two roles must never share a key id.
NEW_ID="$(key_id "$TMP/$ROLE.pub")"
for other in primary emergency; do
  [ "$other" = "$ROLE" ] && continue
  op="$REPO_DIR/keys/catalog-$other.pub"
  if [ -f "$op" ] && [ "$(key_id "$op")" = "$NEW_ID" ]; then
    echo "refusing: the new $ROLE key has the same id as the $other key ($NEW_ID); run again" >&2; exit 1
  fi
done
echo "generated $ROLE key: id $NEW_ID"

destroy() { if command -v shred >/dev/null; then shred -u "$@"; else rm -P "$@" 2>/dev/null || rm -f "$@"; fi; }

if [ "$ROLE" = primary ] && [ "$SET_SECRETS" -eq 1 ]; then
  # Recovery copy first, so a failed upload never leaves the only copy in CI.
  echo
  echo "age will now ask for the MASTER passphrase that locks the recovery copy."
  echo "Create it in your password manager first, then paste it here (twice)."
  printf '%s' "$PASS" | age -p -o "$TMP/$ROLE.passphrase.age"
  chmod 600 "$TMP/$ROLE.passphrase.age"
  cp "$TMP/$ROLE.key" "$BACKUP/$ROLE.key"
  cp "$TMP/$ROLE.passphrase.age" "$BACKUP/$ROLE.passphrase.age"
  cp "$TMP/$ROLE.pub" "$BACKUP/$ROLE.pub"
  chmod 600 "$BACKUP/$ROLE.key" "$BACKUP/$ROLE.passphrase.age"
  echo "recovery copy written to $BACKUP"
  gh secret set MINISIGN_KEY --env "$ENVIRONMENT" -R "$REPO" < "$TMP/$ROLE.key"
  printf '%s' "$PASS" | gh secret set MINISIGN_PASSWORD --env "$ENVIRONMENT" -R "$REPO"
  echo "secrets set on $REPO, environment $ENVIRONMENT: MINISIGN_KEY, MINISIGN_PASSWORD"
  # The working copy is no longer needed: CI has one, the recovery copy has one.
  destroy "$TMP/$ROLE.key" "$TMP/$ROLE.passphrase.age"
  mv "$TMP/$ROLE.pub" "$OUT/"
  KEPT="the public key only (the secret key is in the $ENVIRONMENT environment and the recovery copy in $BACKUP)"
elif [ "$ROLE" = primary ]; then
  echo
  echo "age will now ask for a master passphrase to encrypt the primary's passphrase."
  printf '%s' "$PASS" | age -p -o "$TMP/$ROLE.passphrase.age"
  chmod 600 "$TMP/$ROLE.passphrase.age"
  mv "$TMP/$ROLE.key" "$TMP/$ROLE.pub" "$TMP/$ROLE.passphrase.age" "$OUT/"
  KEPT="$ROLE.key (encrypted by minisign), $ROLE.pub, $ROLE.passphrase.age"
else
  mv "$TMP/$ROLE.key" "$TMP/$ROLE.pub" "$OUT/"
  KEPT="$ROLE.key (encrypted by minisign), $ROLE.pub"
fi

mkdir -p "$REPO_DIR/keys"
cp "$OUT/$ROLE.pub" "$REPO_DIR/keys/catalog-$ROLE.pub"
chmod 644 "$REPO_DIR/keys/catalog-$ROLE.pub"

echo
echo "Kept in $OUT: $KEPT."
echo "Public key copied to keys/catalog-$ROLE.pub; commit it."
echo
echo "Roster entry for the apps (meshTerm CatalogTrust):"
echo "    role: $ROLE   key id: $NEW_ID"
echo "    payload: $(payload "$OUT/$ROLE.pub")"

if [ "$ROLE" = emergency ]; then
  echo
  echo "Emergency key passphrase, shown ONCE. Put it in your password manager now:"
  echo "    $PASS"
  echo "Then copy $OUT to a second offline medium and run:"
  echo "    scripts/provision-catalog-keys.sh --restore-test emergency $OUT/emergency.key"
elif [ "$SET_SECRETS" -eq 0 ]; then
  echo
  echo "Not uploaded. To use it in CI, set MINISIGN_KEY (contents of $OUT/$ROLE.key) and"
  echo "MINISIGN_PASSWORD (decrypt $OUT/$ROLE.passphrase.age with age -d) in the"
  echo "$ENVIRONMENT environment, then delete the local copies."
fi
