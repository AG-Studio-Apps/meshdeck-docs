---
title: A container
lede: Live stats, the actions you can take, and what asks first.
---
Tap a container in Fleet to open it. The header shows its name, "&lt;image&gt; · &lt;host&gt;" and a status pill.

## What you see

- **CPU** and **Memory** charts of the last minute (one-second samples). They read "collecting…" until there are a couple of samples.
- Rows for its **Ports**, **Network**, **Volumes**, **Environment** (how many variables, and how many come from the vault) and **Health check** (passing, failing, starting or none).

## The action tiles

| Tile | What it does |
|---|---|
| **Logs** | Opens the [log stream]({{ '/manual/logs/' | relative_url }}). |
| **Restart** | Restarts the container. Enabled only while it is running. |
| **Stop** / **Resume** / **Start** | Stops a running container, resumes a paused one, or starts a stopped one. |
| **More** | **Pause**, **Restart**, **Stop**, **Shell** (open a [terminal]({{ '/manual/terminal/' | relative_url }})), **Kill** and **Remove**. |
| **Shell** | Opens a terminal in the container. Enabled only while it is running. |
| **Redeploy** | **Pull latest & recreate**, **Recreate**, or **Edit environment…**. |

If the container is **Unhealthy** or **Down**, a **What's wrong?** tile appears too. See [AI diagnosis]({{ '/manual/diagnosis/' | relative_url }}).

## What asks first

| Action | Asks first? |
|---|---|
| **Restart**, **Pause**, **Resume**, **Start** | No. They run as soon as you tap. |
| **Stop**, **Kill** | Yes. |
| **Remove** | Yes. It offers **Remove** and **Remove with volumes**, and removing volumes deletes their data. |
| **Pull latest & recreate**, **Recreate** | Yes. |

Recreating makes a new container with the same settings, and keeps the old one until the new one is running. If the container is managed by Docker Compose, the confirmation warns you that the next `compose up` will recreate it again from the compose file. If any of its environment values come from the vault, it warns that Docker shows environment values to anyone who can inspect the container.

A redeploy shows its progress: checking the image, contacting the registry, pulling layers, recreating and starting. If it fails, meshDeck rolls back to the original container where it can, and says so. If the original could not be restored, it tells you to check the host.

## Edit environment

**Redeploy → Edit environment…** opens the environment editor. Each row has a key and a value. The key icon lets you use a [vault secret]({{ '/manual/vault/' | relative_url }}) instead of typing a value; the row becomes a blue chip with the secret's name. **Save & recreate** recreates the container with the new environment.

## New container

**+ → New container…** opens a form: a **Name**, an **Image** (for example `nginx:1.27`), an optional **Command**, and **Pull image first**. Below it are **Environment**, **Ports**, **Volumes**, and **Networking & restart**, where you choose the network and a restart policy (**Never**, **Unless stopped**, **Always** or **On failure**). **Create & start** creates it, with the label `meshdeck.created=true`.

<div class="note" markdown="1">
**On the docker command line (Advanced) hosts**

Some containers cannot be recreated from here, because part of their configuration has no `docker create` flag. The app tells you, and suggests using Compose or an Engine API connection.
</div>
