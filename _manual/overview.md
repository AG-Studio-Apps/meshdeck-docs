---
title: Overview
lede: What meshDeck is, what you need, and how the app is laid out.
---
meshDeck is a native app for iPhone and iPad that shows the containers on your Docker, Podman and Portainer hosts and lets you act on them. It connects from your phone straight to your hosts, over Tailscale, SSH or HTTPS. There is no account, and there is no server of ours in the connection.

## What you need

- An iPhone or iPad running iOS 26 or later.
- A host running Docker or Podman that you can reach by **SSH** (your username needs to be able to use the engine's socket, see [Podman hosts]({{ '/manual/podman/' | relative_url }}) for rootful and rootless Podman), **or** a **Portainer** server and an access token.
- Optionally, a Tailscale account, if you want to reach hosts on your tailnet. meshDeck has a built-in Tailscale node, so the Tailscale app is not required.

<div class="note" markdown="1">
**Nothing to open on the host**

meshDeck never asks you to expose Docker's or Podman's API on the internet. It reaches the engine's socket through an SSH session, or talks to Portainer over HTTPS with a token you create.
</div>

## How the app is laid out

**On iPhone** there are three tabs: **Fleet**, **Topology** and **Settings**.

- **Fleet** is the home screen. It shows the selected host: a summary card, your stacks and your containers.
- **Topology** draws a map of how the containers on a host depend on each other.
- **Settings** holds your hosts, the built-in Tailscale node, notifications, the vault, AI diagnosis and your plan.

**On iPad** (and other regular-width layouts) the same things become a three-column cockpit: hosts and stacks on the left, containers in the middle, and the container you picked on the right. See [iPad and shortcuts]({{ '/manual/ipad/' | relative_url }}).

<figure class="shot"><img src="{{ '/assets/img/shots/iphone-02-fleet-healthy.webp' | relative_url }}" alt="The Fleet tab with a green summary card, stacks and containers" width="560" height="1217" loading="lazy">&lt;figcaption&gt;The Fleet tab on a healthy host.</figcaption></figure>

## What the colours mean

Colour is never the only signal: every status also has its own icon.

| Status | Colour | Meaning |
|---|---|---|
| **Down** | Red | Dead, exited with an error, killed for memory, or stuck in a restart loop. |
| **Unhealthy** | Amber | Running, but its health check is failing. |
| **Starting** | Amber | Starting up, restarting cleanly, or being removed. |
| **Healthy** | Green | Running, and its health check passes. |
| **Running** | Green | Running, with no health check defined. |
| **Stopped** | Grey | Created, paused, or exited cleanly. |

Only **Down** and **Unhealthy** count as "needs attention" on the summary card.

## Coming later

meshDeck is actively developed. High on the list, in rough order:

- **Light mode.** It is dark for now.
- **Home Screen widgets and Siri Shortcuts.**
- **Picking a host from your tailnet**, instead of typing each one in.
- **Passphrase-protected SSH keys.** Ed25519 and ECDSA keys work today.
- **Git stacks over SSH.** `https://` and `http://` URLs work today.
- **More languages.** English for now.

A few things stay out by design: no iCloud sync, so your hosts, drafts and settings live on the device; no Docker Swarm; and RSA SSH keys (Ed25519 and ECDSA are supported). Podman pods and Quadlets are not shown either, meshDeck works with containers, stacks and images. See [Podman hosts]({{ '/manual/podman/' | relative_url }}).
