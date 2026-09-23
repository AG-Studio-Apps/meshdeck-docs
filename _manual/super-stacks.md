---
title: Super stacks
lede: Curated multi-app projects, a media suite, a monitoring stack, wired to run together and deployed in one step.
---
A **super stack** is a curated Docker Compose project that runs several apps together as one
unit, already wired up: a media-automation suite behind a VPN killswitch, or a monitoring stack
that opens already graphing. You deploy it like any other [stack]({{ '/manual/stacks/' | relative_url }}), 
fill in a short form and tap deploy, but instead of one app you get a whole working setup.

## Finding them

Open the template gallery with **+ → Templates…** (or **Deploy → New stack…** on iPad). The
gallery has two tabs:

| Tab | What's there |
|---|---|
| **Stacks** | Single-app templates, WordPress, Jellyfin, Grafana, Pi-hole and the rest, grouped by category. A **Featured** row spotlights a few picks at the top. |
| **Super Stacks** | The curated multi-app projects, grouped by the same categories (Media, Monitoring and so on). |

<figure class="shot"><img src="{{ '/assets/img/shots/iphone-09-templates.webp' | relative_url }}" alt="The template gallery: single-app stacks grouped by category, with Super Stacks featured at the top and in their own tab" width="560" height="1217" loading="lazy"><figcaption>Super Stacks are featured at the top of the gallery and in their own tab.</figcaption></figure>

Templates are curated and versioned; a deployed stack keeps the version it was made from. Pull
the latest set any time with the refresh button in the gallery's toolbar.

## Deploying one

Pick a super stack and fill in its form. It uses the normal stack path, so everything on the
[Stacks]({{ '/manual/stacks/' | relative_url }}) page applies, the compose is written to
`~/.meshdeck/stacks/<name>/` over SSH, or stored on the server on a Portainer host.

- **Ports and paths** come with sensible defaults; change them if they clash with something you
  already run.
- **Passwords** marked as secrets are generated for you and kept in the [vault]({{ '/manual/vault/' | relative_url }}).
  Leave a password field blank to auto-generate a strong one; you can reveal or copy it later from
  the app's in-app browser when you open the app's web UI.
- **Each super stack lists its own setup steps** on the form, the wiring you do once after it's
  up. They're repeated below.

## A note on host access

Some super stacks ask for more of the host than a single app does, a folder of media, a VPN
credential, or read-only access to the host's metrics. Each one says so on its form and below.
meshDeck never exposes a Docker port on TCP; everything reaches the host over Tailscale or SSH.

---

## Media automation

**Jellyfin + Sonarr / Radarr / Lidarr + Prowlarr + qBittorrent (VPN) + SABnzbd + Jellyseerr.**
A complete media-automation suite: indexers, download clients, the *arr managers, subtitles, a
media server and a request front-end, with the torrent client locked behind a VPN killswitch.

**What it does.** qBittorrent has network **only** through the VPN (Gluetun): if the VPN drops,
its traffic stops. It stays down until the VPN connects, so a bad credential shows up as an
unhealthy VPN rather than a torrent client leaking. Usenet (SABnzbd) and everything else run on
the normal network.

**Before you start.** You need a VPN provider that supports **OpenVPN** in Gluetun, NordVPN,
Private Internet Access, Windscribe, Surfshark or ProtonVPN. (Mullvad is WireGuard-only and isn't
supported by this template.) Your OpenVPN username and password go in the form; the password is
stored in the vault.

**One folder for everything.** `DATA_PATH` is a single folder holding both downloads and media
(for example `/srv/media`), so Sonarr and Radarr **hardlink** imports instead of copying them, 
no wasted disk, instant imports.

**After it's up**, the wiring you do once:

1. In each *arr app, add the download client **qBittorrent** at host `gluetun`, port `8080`, and
   **SABnzbd** at `sabnzbd:8080`.
2. Add **Prowlarr** as the indexer source.
3. Point **Jellyseerr** at Jellyfin.
4. If qBittorrent (4.6+) rejects the connection, turn off **Enable Host header validation** in
   its Web UI (Options → Web UI).

---

## Observability

**Prometheus, Grafana, Alertmanager, node-exporter and cAdvisor**, a monitoring stack wired to
graph on first open. Grafana comes up with the Prometheus datasource already connected, scraping
your host's metrics and every container's.

**What you get.**

| App | Role |
|---|---|
| **Grafana** | The dashboard you look at. Password-gated; published on its port. |
| **Prometheus** | Collects and stores the metrics. |
| **Alertmanager** | Routes alerts (starts with no rules, add your own). |
| **node-exporter** | Host metrics: CPU, memory, disk, network. |
| **cAdvisor** | Per-container metrics. |

**Security stance, read this before deploying.**

- **Grafana** is the only app published for you to open, and it's password-gated. **Prometheus**
  and **Alertmanager** have no built-in authentication, so they bind to **localhost on the host
  only**, reach them through meshDeck's forwarding, never a public port.
- **cAdvisor** runs privileged with read-only access to the host's root filesystem, disks and the
  Docker socket; **node-exporter** reads the whole host filesystem read-only. That's the price of
  host and container metrics, and it's **host-level visibility**, deploy this only on a host you
  trust meshDeck with.

**The Grafana login.** The admin password is set on first launch and kept in your vault; leave the
field blank to generate one. Reveal or copy it from the in-app browser when you open Grafana. One
catch: it's the **initial** password only, if you change it inside Grafana, update it in meshDeck
too, because a redeploy won't reset it while Grafana's data volume is still there.

**After it's up.** Open Grafana, the Prometheus datasource is already wired. Import a dashboard to
start graphing straight away, for example Grafana.com dashboard **1860** (node-exporter) and
**14282** (cAdvisor). Tune the scrape interval and how long metrics are kept from the form
(`SCRAPE_INTERVAL`, `PROM_RETENTION`).

---

## When something goes wrong

A super stack is a normal stack, so the [Stacks]({{ '/manual/stacks/' | relative_url }}) and
[Troubleshooting]({{ '/manual/troubleshooting/' | relative_url }}) pages cover it. A multi-app
stack pulls several images and can take a minute or two to settle on first deploy, give it time
before assuming a service is stuck.
