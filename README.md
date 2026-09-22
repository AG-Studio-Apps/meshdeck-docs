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

GitHub Pages, from `main`, custom domain `meshdeck.ag-applications.com` (the `CNAME` file). DNS is a
CNAME from `meshdeck` to `ag-studio-apps.github.io`.
