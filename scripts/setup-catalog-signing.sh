#!/usr/bin/env bash
# One-shot setup of the template catalogue's signing keys, for a Debian or
# Ubuntu machine with two USB sticks plugged in. Walks through every step and
# asks before each one:
#
#   1. installs git, minisign, age, openssl and gh (apt)
#   2. logs gh in if needed
#   3. clones (or updates) the catalogue repo on the catalog-signing branch
#   4. EMERGENCY key onto USB 1, copied to USB 2, restore test
#      (skipped if USB 1 already has one; its public half is reused)
#   5. creates the catalog-signing environment on GitHub
#   6. PRIMARY key into that environment, with a recovery copy on USB 1
#   7. commits and pushes the two public keys (keys/*.pub) to the branch
#
# Run it as yourself (not root):
#   curl -fsSL https://raw.githubusercontent.com/AG-Studio-Apps/meshdeck-docs/catalog-signing/scripts/setup-catalog-signing.sh -o setup-catalog-signing.sh
#   bash setup-catalog-signing.sh
#
# Have ready: your password manager, with a NEW entry for the master password
# (create the password before step 6), and the two USB sticks mounted.
set -euo pipefail

REPO="AG-Studio-Apps/meshdeck-docs"
BRANCH="catalog-signing"
ENVIRONMENT="catalog-signing"
WORKDIR="${WORKDIR:-$HOME/meshdeck-docs}"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
die()  { printf '\n\033[31m%s\033[0m\n' "$*" >&2; exit 1; }
ask()  { local a; read -r -p "$* [y/N] " a; [[ "$a" =~ ^[Yy] ]]; }

[ "$(id -u)" -ne 0 ] || die "Run this as your normal user, not root (it uses sudo only to install packages)."

# --- 1. Packages ------------------------------------------------------------------
say "Step 1: tools"
missing=()
for t in git minisign age openssl gh; do command -v "$t" >/dev/null || missing+=("$t"); done
if [ ${#missing[@]} -gt 0 ]; then
  echo "Missing: ${missing[*]}"
  ask "Install them with apt (needs sudo)?" || die "Install them and run again."
  sudo apt-get update
  sudo apt-get install -y "${missing[@]}" || {
    command -v gh >/dev/null || echo "If gh failed: follow https://cli.github.com (Linux, apt) and run again."
    die "Package install failed."
  }
fi
echo "OK: git, minisign, age, openssl, gh."

# --- 2. gh login ------------------------------------------------------------------
say "Step 2: GitHub login"
if ! gh auth status >/dev/null 2>&1; then
  echo "gh is not logged in. A browser or device code will open."
  gh auth login -h github.com -p https -w
fi
gh api "repos/$REPO" >/dev/null 2>&1 || die "This GitHub login cannot see $REPO. Log in as an account with admin on it."
echo "OK: logged in as $(gh api user --jq .login)."

# --- 3. Repo ----------------------------------------------------------------------
say "Step 3: catalogue repo ($BRANCH) in $WORKDIR"
if [ -d "$WORKDIR/.git" ]; then
  git -C "$WORKDIR" fetch -q origin "$BRANCH"
  git -C "$WORKDIR" checkout -q "$BRANCH"
  git -C "$WORKDIR" pull -q --ff-only origin "$BRANCH"
else
  gh repo clone "$REPO" "$WORKDIR" -- -b "$BRANCH" -q
fi
cd "$WORKDIR"
PROVISION="$WORKDIR/scripts/provision-catalog-keys.sh"
[ -x "$PROVISION" ] || chmod +x "$PROVISION"
echo "OK: $(git log --oneline -1)"

# --- USB sticks -------------------------------------------------------------------
say "USB sticks"
echo "Mounted under /media/$USER:"
ls -1 "/media/$USER" 2>/dev/null || echo "  (nothing; plug the sticks in, or type a full path below)"
read -r -p "USB 1 (name under /media/$USER, or a full path): " U1
read -r -p "USB 2 (name under /media/$USER, or a full path): " U2
[[ "$U1" = /* ]] || U1="/media/$USER/$U1"
[[ "$U2" = /* ]] || U2="/media/$USER/$U2"
[ -d "$U1" ] && [ -w "$U1" ] || die "$U1 is not a writable folder."
[ -d "$U2" ] && [ -w "$U2" ] || die "$U2 is not a writable folder."
[ "$(realpath "$U1")" != "$(realpath "$U2")" ] || die "USB 1 and USB 2 are the same place."
EM1="$U1/catalog-emergency"; EM2="$U2/catalog-emergency"; PRI="$U1/catalog-primary"

# --- 4. Emergency key ---------------------------------------------------------------
say "Step 4: EMERGENCY key (offline only, never in CI)"
if [ -f "$EM1/emergency.key" ]; then
  echo "USB 1 already has an emergency key: keeping it."
  cp "$EM1/emergency.pub" keys/catalog-emergency.pub 2>/dev/null || { mkdir -p keys; cp "$EM1/emergency.pub" keys/catalog-emergency.pub; }
  chmod 644 keys/catalog-emergency.pub
else
  echo "It will print a passphrase ONCE. Copy it into your password manager before going on."
  ask "Generate the emergency key on $EM1 now?" || die "Stopped."
  [ -d "$EM1" ] && rmdir "$EM1" 2>/dev/null || true
  "$PROVISION" --only emergency --out "$EM1"
  read -r -p "Press Enter once the passphrase is saved in your password manager... " _
fi
if [ ! -f "$EM2/emergency.key" ]; then
  echo "Copying to USB 2."
  mkdir -p "$EM2"; chmod 700 "$EM2"
  cp "$EM1/emergency.key" "$EM1/emergency.pub" "$EM2/"
  chmod 600 "$EM2/emergency.key"
fi
cmp -s "$EM1/emergency.key" "$EM2/emergency.key" || die "The emergency key on USB 2 differs from USB 1; sort that out first."
say "Restore test: type the emergency passphrase (from your password manager)"
"$PROVISION" --restore-test emergency "$EM2/emergency.key"

# --- 5. Environment -----------------------------------------------------------------
say "Step 5: GitHub environment '$ENVIRONMENT'"
if gh api "repos/$REPO/environments/$ENVIRONMENT" >/dev/null 2>&1; then
  echo "Already exists."
else
  gh api -X PUT "repos/$REPO/environments/$ENVIRONMENT" >/dev/null
  echo "Created."
fi
echo "Restrict it to the main branch (needed before the first signed publish):"
gh api -X PUT "repos/$REPO/environments/$ENVIRONMENT" \
  -F 'deployment_branch_policy[protected_branches]=false' \
  -F 'deployment_branch_policy[custom_branch_policies]=true' >/dev/null \
  && gh api -X POST "repos/$REPO/environments/$ENVIRONMENT/deployment-branch-policies" -f name=main >/dev/null 2>&1 || true
echo "OK. Add the required reviewer (your signer account, 'Prevent self-review' on, admin bypass off)"
echo "in Settings > Environments > $ENVIRONMENT before the first signed publish."

# --- 6. Primary key -----------------------------------------------------------------
say "Step 6: PRIMARY key (into GitHub, recovery copy on USB 1)"
if [ -f "$PRI/primary.key" ]; then
  echo "USB 1 already has a primary recovery copy: not making another."
  [ -f keys/catalog-primary.pub ] || cp "$PRI/primary.pub" keys/catalog-primary.pub
else
  echo "Create the MASTER password in your password manager now. age will ask for it twice: paste it."
  ask "Generate the primary key and upload it to the $ENVIRONMENT environment?" || die "Stopped."
  [ -d "$PRI" ] && rmdir "$PRI" 2>/dev/null || true
  "$PROVISION" --only primary --set-secrets --backup "$PRI"
  echo "Now attach the three files in $PRI to the master password's entry in your password manager."
fi
secrets="$(gh api "repos/$REPO/environments/$ENVIRONMENT/secrets" --jq '[.secrets[].name]|join(",")')"
[[ "$secrets" == *MINISIGN_KEY* && "$secrets" == *MINISIGN_PASSWORD* ]] \
  && echo "OK: $ENVIRONMENT has $secrets." \
  || echo "WARNING: $ENVIRONMENT secrets are '$secrets'; expected MINISIGN_KEY and MINISIGN_PASSWORD."

# --- 7. Public keys -----------------------------------------------------------------
say "Step 7: publish the public keys to the branch"
[ -f keys/catalog-primary.pub ] && [ -f keys/catalog-emergency.pub ] || die "keys/ is missing a public key."
p_id="$(sed -n 1p keys/catalog-primary.pub | awk '{print $NF}')"
e_id="$(sed -n 1p keys/catalog-emergency.pub | awk '{print $NF}')"
[ "$p_id" != "$e_id" ] || die "Primary and emergency share a key id ($p_id); regenerate one."
git add keys/catalog-primary.pub keys/catalog-emergency.pub
if git diff --cached --quiet; then
  echo "Public keys already committed."
else
  git -c user.name="$(gh api user --jq .login)" -c user.email="$(gh api user --jq '.id|tostring')+$(gh api user --jq .login)@users.noreply.github.com" \
    commit -q -m "Catalogue public keys (primary $p_id, emergency $e_id)"
  git push -q origin "$BRANCH"
  echo "Pushed."
fi

say "Done."
echo "  primary   key id $p_id  (in GitHub $ENVIRONMENT; recovery copy on $PRI)"
echo "  emergency key id $e_id  (on $EM1 and $EM2; passphrase in your password manager)"
echo "Unmount and store the USB sticks in two different places."
