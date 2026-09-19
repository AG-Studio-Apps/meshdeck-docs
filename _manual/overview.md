---
title: Overview
lede: What meshDeck is, what you need, and how the app is laid out.
---
meshDeck is a native app for iPhone and iPad that shows the containers on your Docker and Portainer hosts and lets you act on them. It connects from your phone straight to your hosts, over Tailscale, SSH or HTTPS. There is no account, and there is no server of ours in the connection.

## What you need

- An iPhone or iPad running iOS 26 or later.
- A host running Docker that you can reach by **SSH** (your username needs to be able to use the Docker socket), **or** a **Portainer** server and an access token.
- Optionally, a Tailscale account, if you want to reach hosts on your tailnet. meshDeck has a built-in Tailscale node, so the Tailscale app is not required.

<div class="note" markdown="1">
**Nothing to open on the host**

meshDeck never asks you to expose Docker's API on the internet. It reaches the Docker socket through an SSH session, or talks to Portainer over HTTPS with a token you create.
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

## What meshDeck does not do

We would rather you know before you install:

- No widgets and no Siri Shortcuts. There *is* an optional lock — see Settings → Lock — which covers the app when it goes to the background and asks for Face ID, Touch ID or your passcode before it opens again. It is off until you turn it on.
- No iCloud sync. Your hosts, drafts and settings live on the device.
- No automatic discovery of hosts. You add each one by hand.
- No light mode. The app is dark.
- No changing a saved host's sign-in method. You can edit its name, address, port and username (swipe a host right in Settings, or press and hold it), and change how it is reached, its sudo settings and its alerts — but to sign in a different way, remove it and add it again.
- Images, volumes and networks are read-only. You can browse them, but not delete, prune or pull.
- Docker Swarm stacks are not supported.
- SSH keys must be Ed25519 or ECDSA and have no passphrase. RSA keys are not supported.
- Git stacks use `https://` or `http://` URLs. Repositories that need an SSH key are not supported.
- Podman is not something we have tested, so we do not claim it.
- The app is in English only.
