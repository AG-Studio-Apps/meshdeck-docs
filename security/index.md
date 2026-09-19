---
title: Security
eyebrow: How it is built
lede: What meshDeck protects, how, and where its protection stops.
description: How meshDeck connects to your hosts, where it keeps your secrets, what AI diagnosis and Instant alerts send, and what it does not protect against.
---
meshDeck manages the machines that run your things, so it is built to hold as little as possible and to be plain about what it cannot do. This page is the technical version of the [Privacy Policy]({{ '/privacy/' | relative_url }}).

## Connecting to your hosts

- **Nothing exposed.** meshDeck reaches Docker through an SSH session (running `docker system dial-stdio`, or the `docker` command line), or through Portainer's HTTPS API with a token. It never asks you to open Docker's API on the network, and never asks for TCP 2375.
- **No middleman.** The connection goes from your phone to your host. There is no meshDeck server in between, and no account.
- **Host keys are pinned on first use.** The first time you connect, you compare the fingerprint and choose whether to trust it. If it later changes, meshDeck stops and asks: **Host key changed**, with the saved and presented fingerprints side by side. A changed key can mean a reinstall or an interception, and the prompt says so.
- **Certificates are pinned too.** For Portainer and other HTTPS endpoints, the system's trust store is tried first, and a self-signed certificate is pinned when you accept it. A changed certificate stops the connection until you decide. There is no "trust anything" switch.
- **Tailscale.** The built-in node speaks WireGuard through Tailscale's own library, and sign-in happens on Tailscale's or your identity provider's page.
- **Keys.** Keys made by the app are Ed25519 and generated on the phone; the private half never leaves it. Imported keys must be Ed25519 or ECDSA without a passphrase.

## Secrets on your phone

- SSH keys and passwords, Portainer tokens, sudo passwords, vault values, your AI key and a Tailscale auth key are stored in the **iOS Keychain**, for this device only. They are not synchronised through iCloud Keychain.
- Most are readable only while the phone is unlocked. The few items the notification extension needs are readable after the first unlock since a restart, so an alert can be decoded on a locked phone.
- The **vault** is write-only: values are never displayed, and drafts, templates and systems refer to them by name.

## What reaches your hosts

A vault value leaves the Keychain **only at deploy, and only to the host you deploy to**: written to a mode-600 `.env` beside the compose file over SSH, stored by your Portainer server for a Portainer stack, or placed in a container's environment where **anyone who can inspect the container can read it**. Nothing here can keep a secret from the machine that has to use it. The [vault page]({{ '/manual/vault/' | relative_url }}) has the full table.

## AI diagnosis

- **Off by default, and never automatic.** It needs your own key and your explicit consent, and sends one request each time you tap.
- **Only what is listed.** The request carries the container's state, command, environment, a slice of logs (200 lines, 8 KB), a minute of statistics, its linked containers and recent events. It carries no vault value, no host address, no port bindings or mounts, and nothing about other containers.
- **Masking.** Variables whose names look secret are replaced; token-shaped strings, credentials in URLs and the value after a secret flag are masked; a vault-bound variable becomes a placeholder naming the entry. **If anything that still looks like a secret remains, nothing is sent.**
- **The limit of masking.** It works on patterns. It cannot recognise a secret that looks like ordinary text: a random password in a variable with an innocent name, or one printed in a log line. Values that are not secret at all, such as a hostname or a port, are sent as they are. If that matters, leave diagnosis off.
- **The model can only suggest.** The reply is a summary, causes, and actions chosen from a fixed list the app already implements; anything else is dropped. There is no chat and no shell. Every action needs your tap, and some (a restart) run the moment you tap. **Stop**, **Kill** and **Remove** are never offered.
- **Your provider.** What the provider keeps is governed by its terms and your account. An `http://` model server is not encrypted in transit.

## Instant alerts

Alerts are opt-in, and today only the enrolment and a test alert exist.

- **Encrypted on the host, decrypted on your phone.** Each alert is sealed with ChaCha20-Poly1305 using a 256-bit key made on your phone when you enrol a host. Only your phone and that host have it. The relay never sees it. The alert is bound to its host, so one host's alert cannot be replayed as another's.
- **What the relay stores.** Your Apple push token; random identifiers and the secrets it issued to your phone and to each host, kept as SHA-256 hashes; your per-kind preferences; and for each enrolled host, which of your phones are attached and when it last checked in. No names, no addresses, no alert text.
- **Your push token is stored as it is**, because the relay has to hand it to Apple to deliver a notification. An internal audit in September 2026 found that the relay would also accept a push token on its own as proof of identity when an app re-registers, which means someone who obtained your token could take over your registration, mute your alerts or remove your hosts. **They could not read any alert**, because the key that decrypts one never leaves your phone and the host. We are changing re-registration so a token alone is not enough, and this page will say so when it ships.
- **What it can still infer.** How many phones and hosts exist; which push token belongs to which opaque host; when hosts check in or go quiet; the time and kind of alerts and a stable but meaningless label per container; and the network address of a request while it is handled. It cannot tell what a host or container is.
- **Hardening.** The relay runs as a sandboxed system service with a restricted set of privileges, listens only on the loopback interface behind a TLS proxy, limits request rates per address and per credential, caps every table an anonymous caller could grow, and logs failures only, with no tokens, identifiers or content.

## What we do not protect against

We would rather say it than have you find it.

- **A phone that someone else can unlock.** meshDeck has no lock of its own. Anyone who can use your unlocked phone can use your hosts.
- **Whoever can reach your hosts.** A vault value on a host is only as safe as that host.
- **Plain values in drafts.** Environment values you typed in plain, rather than from the vault, are stored as you typed them in your drafts and systems on the phone, and are included in device backups. Use the vault for anything sensitive.
- **Backups.** A device backup includes the non-secret app data (your host list, drafts, settings). Keychain secrets are marked this-device-only and are not restored elsewhere.
- **Container logs.** Logs are shown and shared as the container wrote them.
- **Tailscale and your providers.** We do not control what Tailscale, your Headscale, Portainer or your AI provider log or keep.

## Reporting a problem

If you think you have found a security problem in meshDeck or the relay, please email [{{ site.contact_email }}](mailto:{{ site.contact_email }}) with what you found and how to reproduce it, and give us a reasonable chance to fix it before you tell anyone else. Please do not include real credentials. No independent penetration test of meshDeck has been carried out.
