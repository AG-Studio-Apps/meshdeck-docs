---
title: Instant alerts
lede: Push notifications when a host needs attention, from a small agent you deploy on the host.
---
## The idea

A small agent on your host, **stackGuard**, watches your containers and tells your phone when something needs attention: a container crashes or keeps restarting, a health check fails, the disk is nearly full, or a container recovers. The notification travels through a relay we run and Apple's push service, and is **encrypted on the host and decrypted on your phone**, so the relay never learns which host or container it is about.

Instant alerts are part of [meshDeck Pro]({{ '/manual/pro/' | relative_url }}). The free plan is one host; alerts, like extra hosts, need Pro.

## Turn it on

In **Settings → Notifications**, switch on **Instant alerts**. iOS asks for permission to send notifications. The status line reads "Registering this phone…" and then "On."

**Choose what you want.** These switches control what a host may tell you about. They are applied at the relay, so a change takes effect straight away, and the local switch only flips once the relay accepts it.

| Switch | Default | What it covers |
|---|---|---|
| **Crashes and restart loops** | On | A container exited with an error, was killed for memory, or keeps restarting. |
| **Unhealthy containers** | On | A container's health check is failing. |
| **Low disk space** | On | The host's container storage is nearly full. |
| **Recovered** | On | A container that had a problem is running again. |
| **Host silent** | On | A host stopped reporting in, or is back. |
| **Image updates** | Off | A daily digest of images with a newer version available. *Not sending yet, a later release.* |

## Enrol a host and deploy the agent

In **Settings → Hosts**, tap a host to open its page.

**Enrol it.** Under **Notifications**, switch on **Alerts for this host**. This creates the host on the relay and mints a key that only your phone and the host will hold. It shows "Enrolled · key stored on this phone."

Alerts enrol per **privilege domain**, because that is what one agent can see. On a host with only Docker (or Docker and rootful Podman) there is one switch. A host with a rootless Podman environment shows a second, "Alerts for &lt;user&gt;'s rootless Podman", with its own key and its own agent; the first is then labelled "Alerts for the system engines". See [Podman hosts]({{ '/manual/podman/' | relative_url }}).

**Send a test alert.** Under Notifications, tap **Send test alert**. The app plays the agent for one event, and a banner for "&lt;host&gt; · meshdeck-test" should arrive within a moment, decrypted on your phone. Tap it and the app opens on that host.

**Deploy stackGuard.** Under **Agent**, tap **Deploy stackGuard**. meshDeck runs one small container on the host that watches the engine sockets of that domain, Docker's, Podman's, or both, **read-only**, with every Linux capability dropped and no inbound port. It never starts, stops or changes anything, the app does that over its own connection. Be clear-eyed about the grant: **anything that can talk to an engine socket can control the host**, so deploy it only on hosts you already trust meshDeck with. Once it is running the host reports in every couple of minutes, and real alerts start arriving; each says which engine it came from, and tapping it opens that environment.

## Turning it off

- **For one host:** switch off **Alerts for this host**. The host is removed from the relay and its keys from your phone. To stop the agent too, redeploy is under **Agent**; removing the container is done like any other container.
- **For everything:** switch off **Instant alerts**. Your phone's record is deleted from the relay, along with any host that no longer has a phone attached.
- If iOS shows "Notifications are off for meshDeck", turn them on in **iOS Settings → Notifications → meshDeck**.

## Privacy

Alerts go through a small relay we run. It holds your push token, random identifiers and your preferences, and cannot read what an alert says. The agent has no relay built in: meshDeck tells it where to post when it deploys it. The [Privacy Policy]({{ '/privacy/' | relative_url }}) lists exactly what it holds and can see.
