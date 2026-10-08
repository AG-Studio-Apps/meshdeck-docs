# meshdeck-docs

The public site for [meshDeck](https://meshdeck.ag-applications.com): landing page, manual,
security notes, support, Privacy Policy and Licence Agreement. Jekyll on GitHub Pages, plain CSS,
no build step of our own.

## Edit

- Content: `index.html`, `get-started/`, `security/`, `support/`, `privacy/`, `eula/`, and the manual
  in `_manual/` (order and titles in `_data/manual.yml`).
- Site facts (company, contact, legal date, App Store URL): `_config.yml`.
- Look and feel: `assets/css/main.css`. Images: `assets/img/` (WebP, generated from the app's
  screenshots; see `AppStore/compose.py` in the app repo).

## Before you publish a change to the legal pages

`privacy/index.md` and `eula/index.md` describe what the app and the relay do. If either changes,
change the page in the same commit and bump `legal_effective` and `legal_version` in `_config.yml`.
Facts in the privacy policy come from the app and relay source; when in doubt, read the code.

## Build locally

    bundle install
    bundle exec jekyll serve      # http://127.0.0.1:4000

Pages builds with the `github-pages` gem, so what builds here is what is published.

## Deploy

GitHub Pages, deployed by `.github/workflows/publish.yml` on every push to `main`, custom domain
`meshdeck.ag-applications.com` (the `CNAME` file). DNS is a CNAME from `meshdeck` to
`ag-studio-apps.github.io`.

## The template catalogue

`templates.json` is served with a detached minisign signature, `templates.json.minisig`, which the
apps verify against two pinned keys (`keys/catalog-primary.pub`, `keys/catalog-emergency.pub`).
The publish workflow builds the site, runs the gates, signs the catalogue in the protected
`catalog-signing` environment (a reviewer approves each new signature) and deploys body and
signature together. A push that leaves `templates.json` unchanged reuses the live signature and
needs no approval.

Approving a signature (the `catalog-signing` job waits for its reviewer): the job summary is
produced by the pushed code, so it is a guide, not proof. Find the commit the live catalogue was
signed from, independently of the run: `curl -s https://meshdeck.ag-applications.com/templates.json.minisig | sed -n 3p`
(the `commit=` token; for the first signed publish, `bfd4c63`). Then read
`https://github.com/AG-Studio-Apps/meshdeck-docs/compare/<that commit>...<the run's commit>` on
github.com. Approve only when everything in it is expected; any change under `.github/`, `scripts/`,
`keys/` or `_config.yml` means reading that code, not the summary.

To change the catalogue: edit `templates.json`, set `version` to the deployed version + 1, bump the
`version` of every template you changed, and run `scripts/check-catalog.py --deployed-ref origin/main`
before you push. No app names in template text, no em-dashes or en-dashes, no default on a secret.

If the primary key is leaked or lost: delete `MINISIGN_KEY` from the environment, then sign the next
version offline with `scripts/sign-emergency.sh --key <emergency.key>`, commit `templates.json` and
`templates.json.minisig` together and push. Delete the `.minisig` in the next normal catalogue change.
Run `scripts/sign-emergency.sh --key <emergency.key> --dry-run` once a year to prove the offline key
still works.
