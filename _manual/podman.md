---
title: Podman hosts
lede: Podman works beside Docker, rootful or rootless, as a second environment on the same host.
---
meshDeck speaks the Docker Engine API, and Podman answers it too. A host running Podman, on its own, or beside Docker, shows up in the app as one or more **environments**, each with its own containers, stacks and alerts. Podman 4.9 or later is supported; Podman 5 is what we recommend.

## Environments

A host can expose more than one container engine. meshDeck keeps each as an environment of that host:

- **Docker**, the Docker socket, `/var/run/docker.sock`.
- **Podman**, root's Podman, the socket at `/run/podman/podman.sock`.
- **Podman (user)**, the SSH user's rootless Podman, the socket under that user's runtime directory.

When a host has more than one, a control at the top of **Fleet** (and of the containers column on iPad) switches between them; the app remembers which one you last used on each host. Systems, drafts and "copy to host" name an environment, not just a host, "orca12 · Podman (user)", so a stack goes exactly where you sent it.

Each environment is listed under **Environments** on the host's page in **Settings → Hosts**, with how it is reached (API, API via sudo, CLI), the engine version and its state. Swipe one to remove it; the host's first environment stays.

## Finding the engines

When you add an SSH host, meshDeck looks at what it runs: which of `docker` and `podman` are installed, which sockets exist, whether the rootless prerequisites are there, and whether the user has passwordless sudo. Every engine that is ready is added as an environment straight away; one that needs setup is listed under **Environments** with what to do first. **Find engines on this host** runs the same check again whenever you like, after you install Podman, enable a socket, or grant sudo.

### Rootful Podman

Root's socket is root-only; there is no group to join as there is for Docker. meshDeck reaches it with `sudo -n podman system dial-stdio`, so the SSH user needs **passwordless sudo**. Without it the environment is listed with the note "Rootful Podman is root-only. Allow passwordless sudo for &lt;user&gt; (visudo, /etc/sudoers.d), or add the host as root."

### Rootless Podman

The SSH user's own Podman needs three things, and the host page lists whichever are missing, as commands you can copy.

The rootless prerequisites are `uidmap` and `slirp4netns` (or `pasta`). On Debian and Ubuntu:

```
sudo apt install -y uidmap slirp4netns passt
```

On Fedora and RHEL:

```
sudo dnf install -y slirp4netns passt shadow-utils
```

Then enable the user socket:

```
systemctl --user enable --now podman.socket
```

And turn on linger, so the socket outlives your login:

```
loginctl enable-linger $USER
```

The package install is yours to run. The two user-level commands meshDeck can run for you over the SSH session, with your consent.

If Podman and its prerequisites are there but the user socket is not, the environment is added anyway, over the `podman` command line ("Added over the podman command line. Enable the user socket for the API path."). Once you enable the socket, **Find engines on this host** moves it to the API.

## What works

Everything you do on a Docker host: the fleet, stats, logs, the terminal, actions, the topology map, AI diagnosis, stacks and templates, the builder and systems, and instant alerts. A few things read differently on Podman:

- **Compose.** Stacks need Compose **2.26 or newer** on the host — see [Compose on Podman](#compose-on-podman) below.
- **Portability.** Before you deploy, the compose editor lists what will not carry to this environment as written: a mount of the Docker socket (Podman's is `/run/podman/podman.sock`, or under `$XDG_RUNTIME_DIR` for a user), and, under rootless Podman, a published port below 1024 and `privileged: true`. They are warnings, not blocks.
- **Topology on rootless Podman.** A rootless container reports no network attachments, so network links are not drawn for it; stacks, mounts and dependencies are.
- **Advanced (the command line).** On a Podman-only host, **Connect** tries `docker version` and then `podman version`. Without sudo it talks to the user's own rootless Podman, and the environment is recorded as such.

## Compose on Podman

`podman compose` runs an external provider — it is a wrapper, not an implementation — and finds one by searching `PATH` for `docker-compose`, then `podman-compose`. meshDeck's stacks need **Compose 2.26 or newer**, the version Debian 13 ships.

**Check what a host has:**

```
podman compose version --short
```

Podman prints the provider it chose to stderr, so to see which binary answered:

```
podman compose version 2>&1 >/dev/null | head -1
```

**Install one that qualifies:**

| Host | Command |
|---|---|
| Ubuntu, Linux Mint, Pop!_OS | `sudo apt install -y docker-compose-v2` |
| Fedora, RHEL family | `sudo dnf install -y docker-compose` |
| Debian, Raspberry Pi OS | Docker's own repository — see [Docker's install docs](https://docs.docker.com/engine/install/debian/) |

Reconnect the host afterwards; meshDeck checks the provider once per connection.

**Do not install these:**

- **`docker-compose` on Debian or Ubuntu.** That package is Compose **1.29.2**, from 2021. It is the most common cause of this problem: it takes the `docker-compose` name in `PATH`, so Podman prefers it over a newer Compose installed elsewhere on the same host. The package you want on Ubuntu is `docker-compose-v2`.
- **`podman-compose`.** It cannot run the commands meshDeck deploys with, whatever its version.

**If a newer Compose is already installed, meshDeck uses it.** Docker's plugin lives at `/usr/libexec/docker/cli-plugins/docker-compose`, which is not on `PATH`, so Podman ignores it — meshDeck finds it and points Podman at it for its own commands. Your own `podman compose` on that host still picks whatever `PATH` gives it; to change that for everything, set the provider in `~/.config/containers/containers.conf`:

```toml
[engine]
compose_providers = ["/usr/libexec/docker/cli-plugins/docker-compose"]
compose_warning_logs = false
```

### Rootless specifics

- The provider runs as **you**, against your own socket (`$XDG_RUNTIME_DIR/podman/podman.sock`) — so a plugin under `~/.docker/cli-plugins/` counts, and a stack you deploy is yours, not root's.
- Rootful and rootless are separate: a Compose installed for one is not automatically the provider for the other, and their stacks never mix.
- The portability warnings in the compose editor still apply — a port below 1024 and `privileged: true` behave differently rootless.

## Alerts on a Podman host

[Instant alerts]({{ '/manual/alerts/' | relative_url }}) enrol per **privilege domain**, because that is what one agent can see. Root's engines, Docker and rootful Podman, share one enrolment and one stackGuard, which watches both sockets and says which engine an alert came from. A rootless Podman environment enrols on its own ("Alerts for &lt;user&gt;'s rootless Podman") and gets its own stackGuard, run as that user; a rootless agent comes back after a reboot only with linger on and `systemctl --user enable podman-restart`.

## Not covered

Pods and Quadlets are Podman's own and are not shown; meshDeck sees containers, stacks and images through the Docker-compatible API. A Podman older than 4.9 may connect but is not something we test.
