---
title: Terminal
lede: A shell inside a running container.
---
Open a terminal from the **Shell** tile, the **Shell** item in a container's menu, or ⌘T on iPad. It is available only while the container is running.

meshDeck runs `bash` if the container has it, and `sh` if not, with `TERM=xterm-256color`. The terminal resizes with the screen. Closing the screen closes the shell.

## Which connections support it

| Connection | Terminal |
|---|---|
| Docker over SSH | Yes |
| Portainer | Yes |
| Advanced (docker command line over SSH) | Yes |

## The status line

- "Opening a shell in &lt;container&gt;…" while it connects.
- "&lt;host&gt; · &lt;container&gt;" when it is open.
- "Exited with code N" or "Shell closed" when it ends, with a **Reconnect** button.
- The error, with a **Retry** button, if it could not open.

<div class="note" markdown="1">
**Exit codes on Tailscale SSH**

On an Advanced host reached over Tailscale SSH the exit code may not be reported, so you will see "Shell closed".
</div>
