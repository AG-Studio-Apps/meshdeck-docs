---
title: Instant alerts
lede: Push notifications when a host needs attention. What works today, and what does not yet.
---
<div class="note note--warn" markdown="1">
**In progress**

Instant alerts are not finished. Today you can register your phone, enrol a host, and send yourself a **test alert** to prove the path works. The agent that would watch a host and send real alerts is **not released yet**, so no container alerts are sent. This page describes what is there and what is coming.
</div>

## The idea

A small agent on your host will watch your containers and tell your phone when something needs attention: a container crashes or keeps restarting, a health check fails, the disk is nearly full, an image has an update, or a container recovers. The notification travels through a relay we run and Apple's push service, and is **encrypted on the host and decrypted on your phone**, so the relay never learns which host or container it is about.

## What works today

**Turn it on.** In **Settings → Notifications**, switch on **Instant alerts**. iOS asks for permission to send notifications. The status line reads "Registering this phone…" and then "On."

**Choose what you want.** Six switches control what a host may tell you about. They are applied at the relay, so a change takes effect straight away, and the local switch only flips once the relay accepts it.

| Switch | Default | What it will cover |
|---|---|---|
| **Crashes and restart loops** | On | A container exited with an error, was killed for memory, or keeps restarting. |
| **Unhealthy containers** | On | A container's health check is failing. |
| **Low disk space** | On | The host's Docker storage is nearly full. |
| **Image updates** | Off | A daily digest of images with a newer version available. |
| **Recovered** | On | A container that had a problem is running again. |
| **Host silent** | On | A host stopped reporting in, or is back. |

**Enrol a host.** In **Settings → Hosts**, tap the bell beside a host, then switch on **Alerts for this host**. This creates the host on the relay and makes a key that only your phone and the host will hold. It shows "Enrolled · key stored on this phone."

**Send a test alert.** In the same sheet tap **Send test alert**. The app plays the agent for one event, and a banner for "&lt;host&gt; · meshdeck-test" should arrive within a moment, decrypted on your phone. Tap it and the app opens on that host.

## What does not work yet

- The agent that runs on your host and sends real events is not released.
- Until it is, nothing will send alerts about your containers.

## Turning it off

- **For one host:** switch off **Alerts for this host**. The host is removed from the relay and its keys from your phone.
- **For everything:** switch off **Instant alerts**. Your phone's record is deleted from the relay, along with any host that no longer has a phone attached.
- If iOS shows "Notifications are off for meshDeck", turn them on in **iOS Settings → Notifications → meshDeck**.

## Privacy

Alerts go through `mdrelay.meshterm.com`. The relay holds your push token, random identifiers and your preferences, and cannot read what an alert says. The [Privacy Policy]({{ '/privacy/' | relative_url }}) lists exactly what it holds and can see.
