---
title: Tailscale
lede: Reach hosts on your tailnet with the node built into meshDeck, or with the Tailscale app.
---
meshDeck can run its own private Tailscale node inside the app, so a host on your tailnet stays reachable without the Tailscale app. Nothing else on the phone uses it. The node is set up under **Settings → Built-in Tailscale**.

You do not have to use it. If you already run the Tailscale app, meshDeck reaches tailnet hosts through the phone's normal network. The built-in node is for when you would rather not.

## Signing in

Under **Built-in Tailscale** you will see a status line, and, until you sign in:

- **Device name.** The name this node uses in your tailnet. It defaults to "meshDeck on" followed by your phone's name.
- **Control server (optional, Headscale).** Leave it empty for Tailscale. Enter your server's address if you run Headscale.

Then choose **Sign in with browser**, or **Use an auth key instead**. An auth key is generated in the Tailscale admin console under **Settings → Keys**, and starts `tskey-auth-`. It is stored in this phone's Keychain.

If your tailnet requires device approval, the status reads **Waiting for approval**. Approve the device in the admin console and meshDeck connects as soon as it is allowed.

| Status | What it means |
|---|---|
| **Not set up** | No profile yet. |
| **Starting…** / **Connecting…** | The node is coming up. |
| **Sign-in required** | The node's identity expired or was never created. |
| **Waiting for approval** | Approve this device in the Tailscale admin console. |
| **Connected** | Shows the node's tailnet address and who is signed in. |
| **Failed** | The reason is shown under the status. |

## Using the node for a host

For each host there is a switch, **Via built-in Tailscale** (in **Settings → Hosts**, and **Reach via built-in Tailscale** when you add one). It routes that host through the node instead of the phone's network. It turns on for you when you add a host with a tailnet address while the node is connected.

If the phone cannot resolve a tailnet name and the node is up, the Fleet screen offers **Use built-in**.

## Signing out

**Sign out and forget this node** stops the node, removes its key and state from the phone, and clears the profile. It does not ask for confirmation. You may also want to remove the device from your Tailscale admin console.

<div class="note" markdown="1">
**Tailscale SSH**

For a tailnet host the easiest sign-in is **Tailscale**, which needs no key at all, provided the host has Tailscale SSH enabled. See [Adding a host]({{ '/manual/adding-a-host/' | relative_url }}).
</div>
