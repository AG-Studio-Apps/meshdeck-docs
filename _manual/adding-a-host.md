---
title: Adding a host
lede: Connect to a Docker or Podman host over your tailnet, over SSH, or through Portainer.
---
Add a host from the empty Fleet screen (**Add host**), from the **+** menu (**Add host…**), or from the host switcher. meshDeck first asks **How will you connect?** and offers three paths, **Tailscale**, **SSH** and **Portainer**. Pick one and it shows that path's form.

## Tailscale

The simplest path when your host is on your tailnet: meshDeck reaches it over the app's built-in Tailscale and signs in with **Tailscale SSH**, so **no key is stored** and there is nothing to copy to the host, it just needs Tailscale SSH enabled. The Tailscale card appears once the built-in tailnet is connected (sign in under **Settings**).

Give the host a name and its tailnet address and tap **Connect**. The Host section confirms it is **reached over your tailnet, Tailscale SSH, no key**.

## SSH

Choose **SSH** to connect directly with a key or a password. meshDeck opens an SSH session and runs `docker system dial-stdio` (or `podman system dial-stdio`), so it talks to the Engine API through the socket without exposing anything. Your SSH user needs the `docker` command and access to the Docker socket, or Podman, see [Podman hosts]({{ '/manual/podman/' | relative_url }}).

Once the host is added, meshDeck looks for the engines it runs and adds every one that is ready as an **environment** of the host; the rest are listed on the host's page with what to do first. A host with Docker and Podman shows both, and Fleet switches between them.

Fill in the **Host** section:

- **Name (optional).** If you leave it blank the address is used.
- **Address or Tailscale name**
- **Username**
- **Port.** Defaults to 22.

Then choose how to **Sign in with**.

<ol class="steps">
<li><strong>Tailscale</strong>Offered when the address looks like a tailnet address (it ends in <code>.ts.net</code>, is a 100.64.0.0/10 address, or is a single-word MagicDNS name). No key is stored: your tailnet identity signs you in, provided the host has <strong>Tailscale SSH</strong> enabled.</li>
<li><strong>New key</strong>meshDeck makes an Ed25519 key on this phone. The private half never leaves it. Tap <strong>Copy authorized_keys command</strong> and run it once on the host, then connect. The command creates <code>~/.ssh</code> if needed and appends the public key to <code>authorized_keys</code>. meshDeck cannot tell whether you ran it, so a mistake shows up when you connect.</li>
<li><strong>Import key</strong>Paste an OpenSSH private key (<code>-----BEGIN OPENSSH PRIVATE KEY-----</code>), Ed25519 or ECDSA. Keys with a passphrase and RSA keys are not supported.</li>
<li><strong>Password</strong>The password is stored in this phone's Keychain and sent only inside the encrypted SSH session.</li>
</ol>

For a host whose Docker socket the SSH user cannot reach, turn on **Advanced: docker CLI over SSH**, see [Advanced](#advanced) below.

Tap **Connect**. The first time, you will be asked to verify the host's key (see [Trust prompts](#trust-prompts)).

## Portainer

Choose **Portainer** and fill in:

- **Name (optional)**
- **Server URL** (`https://host:9443`). A bare host also works, and the port defaults to 9443.
- **Access token.** In Portainer, open **My account → Access tokens** and create one. It is stored in this phone's Keychain and sent only over TLS.

Tap **Connect**. meshDeck lists the Docker environments on the server. If there is one, it is saved. If there are several, pick one under **Environment** and tap **Save**. An environment that is down is marked "(down)".

The server's certificate is pinned the first time you connect. If it is self-signed you will be asked to trust it.

## Advanced

In the **SSH** path, turn on **Advanced: docker CLI over SSH** for hosts whose Docker socket the SSH user cannot reach. It runs the `docker` command over SSH instead of using the Engine API, or `podman`, if that is what the host has. It has a few limits: statistics update about every two seconds, and a container whose settings cannot be expressed as `docker create` flags cannot be recreated from here.

Turn on sudo if the command needs it, and choose where the sudo password comes from:

- **None.** Passwordless sudo.
- **SSH password.** Reuse the password you signed in with (available only for password sign-in).
- **Enter.** Type a separate sudo password, stored in the Keychain.

Passwordless sudo for just `docker` is the cleaner option. Tap **Copy sudoers line** and run it on the host:

```
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/docker" | sudo tee /etc/sudoers.d/meshdeck
```

**Connect** checks `docker version` first, then `podman version` if there is no docker. If it succeeds you will see the engine and its version. If not, the message says what went wrong: neither is installed or on your PATH, the user cannot use the socket, sudo needs a password, and so on.

## Trust prompts

The first time you connect to a host or a server, meshDeck shows its fingerprint and asks you to verify it.

| Prompt | When | Choices |
|---|---|---|
| **Verify host key** | First SSH connection | **Trust and save**, **Trust once**, **Cancel** |
| **Verify certificate** | First HTTPS connection | **Trust and save**, **Trust once**, **Cancel** |
| **Host key changed** | The key is not the one saved | **Trust the new key** (red), **Trust once**, **Cancel** |
| **Certificate changed** | The certificate is not the one saved | **Trust the new certificate** (red), **Trust once**, **Cancel** |

Compare the fingerprint with the host before you trust it. A changed key can mean the host was reinstalled, **or that something is intercepting the connection**. If you did not reinstall it, choose **Cancel**.

## Adding more hosts

The free plan includes one host (every feature except instant push alerts). Adding a second needs meshDeck Pro. When you reach the limit the sheet shows **Multiple hosts need meshDeck Pro**. See [Free and Pro]({{ '/manual/pro/' | relative_url }}).
