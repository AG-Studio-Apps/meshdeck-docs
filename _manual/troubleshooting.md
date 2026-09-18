---
title: Troubleshooting
lede: What the messages mean and what to try.
---
These are the messages meshDeck shows, and the usual fix for each. If yours is not here, [get in touch]({{ '/support/' | relative_url }}).

## Connecting over SSH

| Message | What it means | Try |
|---|---|---|
| **Authentication failed** | The host rejected your key or password. | For **New key**, run the copied `authorized_keys` command on the host, then reconnect. For an imported key, check it is Ed25519 or ECDSA with no passphrase. |
| **Host key not trusted** | You declined the host's fingerprint. | Connect again and choose **Trust and save** once you have compared it. |
| **Host key changed** | The host presents a different key than the one saved. | If you reinstalled the host, choose **Trust the new key**. If not, choose **Cancel**: something may be intercepting the connection. |
| **The host did not answer** | The address is wrong, the host is down, or a firewall or tailnet is in the way. | Check the address and port. For a tailnet host, check **Settings → Built-in Tailscale**. |
| **Connection closed** | The session dropped. | meshDeck reconnects on its own. **Retry** forces it. |
| "sign in under Settings" | A tailnet host, but the built-in node is not signed in. | Sign in under **Settings → Built-in Tailscale**. |
| "The phone can't resolve &lt;address&gt; without the Tailscale app" | A tailnet name the phone cannot look up. | Tap **Use built-in** if the node is running. |

## Docker on the host

| Message | Try |
|---|---|
| "docker is not installed on the host, or not on &lt;user&gt;'s PATH." | Install Docker, or make sure the SSH user's PATH includes it. |
| "&lt;user&gt; cannot use the Docker socket. Add the user to the docker group, or turn on sudo." | Run `sudo usermod -aG docker <user>` and reconnect, or use **Advanced** with sudo. |
| "sudo asked for a password; passwordless sudo is required for docker." | Use the **Copy sudoers line** command, or choose a sudo password source. |
| "sudo rejected the password." | Re-enter it under **Settings → Hosts** (the sudo button). |
| "The Docker daemon did not answer" | Start the Docker service on the host. |
| "This Docker version is too old" | Update Docker on the host. |

## Portainer

| Message | Try |
|---|---|
| "Portainer rejected the access token." | Create a new token under **My account → Access tokens**. |
| "This Portainer has no Docker environments." | Add an environment in Portainer first. |
| "You declined the server's certificate." | Connect again and trust it, if you know the server. |
| "The server's certificate does not match the one saved for it." | The certificate changed. Trust the new one only if you expected it. |
| "The server did not answer in time." | Check the URL and port (9443 by default). |

## Stacks and containers

| Message | Try |
|---|---|
| "docker compose is not available on this host." | Install the Docker Compose plugin. |
| "git is not installed on this host." | Install `git` on the host. |
| "&lt;path&gt; is not readable by the SSH user." | Fix the file's permissions, or connect as the user that owns it. |
| "A vault secret used by this stack is missing." | Add the secret again under **Settings → Vault**, or change the variable. |
| "The stack is already being worked on." | Wait for the current action to finish. |
| "Recreate isn't available for this container on a CLI host" | Use Compose, or connect with SSH or Portainer instead of **Advanced**. |
| "A container with this name already exists." / "A stack with this name already exists." | Pick another name. |

## AI diagnosis

| Message | Try |
|---|---|
| "Set up diagnosis in Settings first." | Add a provider, a key, and turn on **Send container data to this provider**. |
| "The provider rejected the key." | Check the key and the provider you chose. |
| "The reply was cut short; try again with fewer log lines." | Try again, or ask about a quieter moment. |
| "The evidence still contained something that looks like a secret; nothing was sent." | This is the safety check working. Find and remove the secret from the container's logs or environment. |

## Alerts

| Message | Try |
|---|---|
| "Notifications are off for meshDeck in iOS Settings." | **iOS Settings → Notifications → meshDeck**, allow notifications. |
| "The relay no longer knows this device. Turn alerts off and on again." | Switch **Instant alerts** off and on. |
| "Could not reach the relay" | Check your connection and try again. |

## Still stuck?

Email [{{ site.contact_email }}](mailto:{{ site.contact_email }}). Tell us what you were doing, the message you saw, your iOS version, and whether the host is reached over SSH, Portainer or the docker command line. **Never send a password, a key or a token.**
