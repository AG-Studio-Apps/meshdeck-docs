---
title: Get started
eyebrow: Five minutes
lede: From install to seeing your first container.
description: Install meshDeck, add a Docker or Portainer host over Tailscale or SSH, and see your containers in a few minutes.
---
<ol class="steps">
<li><strong>Install and open meshDeck</strong>There is no account to create. The app opens on an empty Fleet screen with an <strong>Add host</strong> button.</li>
<li><strong>Pick how you will connect</strong>Choose the one that fits your host:
<ul>
<li><strong>Tailscale SSH.</strong> The easiest, if the host is on your tailnet with Tailscale SSH enabled. No key at all.</li>
<li><strong>SSH with a new key.</strong> meshDeck makes a key on your phone. You paste one command on the host, once.</li>
<li><strong>Portainer.</strong> Paste your server's address and an access token.</li>
</ul></li>
<li><strong>Add the host</strong>Tap <strong>Add host</strong>, fill in the address and username, choose how to sign in, and tap <strong>Connect</strong>. The first time, compare the fingerprint it shows with the host's and tap <strong>Trust and save</strong>. The full walk-through is in <a href="{{ '/manual/adding-a-host/' | relative_url }}">Adding a host</a>.</li>
<li><strong>Look around</strong>Your containers appear as live cards, worst first. The card at the top counts what needs attention. Tap a container for its stats and actions, or open the <strong>Topology</strong> tab for the map.</li>
<li><strong>Go further</strong>Deploy a stack from a <a href="{{ '/manual/stacks/' | relative_url }}">template</a>, draw one in the <a href="{{ '/manual/builder/' | relative_url }}">builder</a>, or set up <a href="{{ '/manual/diagnosis/' | relative_url }}">AI diagnosis</a> for the next time something breaks.</li>
</ol>

## If you use Tailscale

You do not need the Tailscale app. Under **Settings → Built-in Tailscale**, sign in with your browser, and meshDeck can reach any host on your tailnet. See [Tailscale]({{ '/manual/tailscale/' | relative_url }}).

## If you use Portainer

In Portainer, open **My account → Access tokens** and create a token. In meshDeck choose **Add host → Portainer**, enter the server URL (for example `https://portainer.example.com:9443`) and the token, and pick the Docker environment you want.

## Before you start

<div class="note" markdown="1">
**What you need**

An iPhone or iPad on iOS 26 or later, and a host running Docker that you can reach by SSH (with access to the Docker socket), or a Portainer server. The free plan covers one host with every feature.
</div>

<div class="note note--tip" markdown="1">
**Nothing to open on the host**

You do not open a port, and you never expose Docker's API. meshDeck goes in through SSH, Tailscale or Portainer's HTTPS.
</div>
