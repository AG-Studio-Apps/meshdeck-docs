---
title: Why meshDeck never asks for your Docker socket
eyebrow: Design decision
lede: Exposing the Docker API is a root-equivalent hole in your host. Here's what we do instead.
description: Why meshDeck connects over SSH or Tailscale instead of asking you to open Docker's API, how host-key and certificate pinning work, and what that does and doesn't protect against.
---

A lot of tools that manage Docker remotely start the same way: bind the daemon to a TCP
port, maybe put a password in front of it, and let a phone or browser talk to it directly.
It's the easy way to build a remote client, and it's also, functionally, giving out root.

## What "exposing the socket" actually means

The Docker API isn't a scoped, read-mostly control surface. Anyone who can reach it can
mount the host's root filesystem into a new container and read or write anything on it —
that's not a bug to patch, it's what the API is for. `dockerd -H tcp://0.0.0.0:2375` with
no TLS is one of the most common "how did they get in" stories in container security
writeups, and it's still the default a surprising number of remote-management guides walk
you through, because it's the path of least resistance for the person building the tool.
A Docker socket bind-mounted into a container is the same hole with different plumbing.

meshDeck's one rule, from day one: **never ask for that.** Not TCP 2375, not a socket
mount, not a password in front of an open port. If a feature needed it, the feature waited.

## What it does instead

meshDeck talks to Docker or Podman the way you'd choose to if you were doing it by hand:
over an SSH session, running `docker system dial-stdio` (or the `podman` equivalent, or
the CLI itself for a socket the SSH user can't reach), or over Portainer's own HTTPS API
with a token you already control. Nothing new is opened on the host. The port that has to
be reachable is the one you already run SSH on, or none at all if you're on Tailscale.

A few things that follow from that:

- **No middleman.** The connection goes from your phone to your host. There's no meshDeck
  server relaying it, and no account to create in the first place.
- **Trust On First Use, not "trust everything."** The first connection shows you the
  host's key fingerprint (or its certificate) and asks you to confirm it, the same as
  logging in with `ssh` for the first time would. If it ever changes afterward, meshDeck
  stops and shows you both fingerprints side by side rather than silently reconnecting —
  a changed key can mean a reinstalled host, or something worse, and the app doesn't
  guess which.
- **Tailscale, if you want zero exposed ports at all.** The built-in node speaks
  WireGuard through Tailscale's own library; sign-in happens on Tailscale's page, not
  meshDeck's.

## The rootless case, specifically

If your Docker or Podman daemon already runs rootless, meshDeck notices — it discovers a
rootless socket as its own thing (distinct from a rootful one on the same host, and
reconciled against it if both exist) rather than only knowing about the rootful default.
That's not a checkbox feature; it's the same story one layer deeper. A host already run
rootless has already shrunk what a compromised daemon can do to it, and meshDeck's job is
to not be the thing that widens that back out just to get a phone talking to it. (Rootless
Podman does lose a little: topology can't draw network edges the same way, because the
information isn't there the same way it is on a rootful daemon. Everything else — fleet,
inspect, stats, logs, deploy — works the same.)

## What this doesn't protect against

Worth saying plainly, because a security pitch that only lists what's covered isn't one
you should trust: SSH access to a host is still access — meshDeck doesn't add a second
lock on top of your SSH key or password, it just refuses to ask you to weaken the one you
already have. A phone someone else can unlock can use whatever hosts you've added to it
(there's an optional app lock for that). And nothing here controls what Tailscale, your
own Headscale, Portainer or an AI provider you connect logs or keeps on their end.

The full breakdown — Keychain storage, what AI diagnosis sends and masks, what the push
relay can and can't see — is on the [Security page]({{ '/security/' | relative_url }}).

{% if site.app_store_url != "" %}
[Try meshDeck]({{ site.app_store_url }}) · [Get started in five minutes]({{ '/get-started/' | relative_url }})
{% else %}
[Get started in five minutes]({{ '/get-started/' | relative_url }})
{% endif %}
