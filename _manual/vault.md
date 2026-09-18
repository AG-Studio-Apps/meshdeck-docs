---
title: The vault
lede: Keep passwords and keys in your Keychain and refer to them by name.
---
The **vault** holds the secrets your containers need, in your iPhone's Keychain, for this device only. A container or stack refers to a secret by name, and meshDeck puts the value in place at deploy.

<figure class="shot"><img src="{{ '/assets/img/shots/iphone-06-vault.webp' | relative_url }}" alt="The environment editor with a vault secret shown as a blue chip" width="560" height="1217" loading="lazy">&lt;figcaption&gt;A vault secret in the environment editor is a blue chip, not a value.</figcaption></figure>

## Managing secrets

Under **Settings → Vault**:

- **Add secret** opens **New secret**. Give it a **Name** and a **Value**.
- Tap a secret to edit it. Leave **New value** empty to keep the current one.
- Swipe left to delete. A secret that is in use cannot be deleted: you will see "Still used by …". Remove it there, or swipe right for **Forget usage**.

Values are write-only. The list shows names, dates and where each is used, never a value.

## Using a secret

In any environment editor (a container, a stack, a template or the builder), tap the key icon, choose a secret, and the row becomes a blue chip with its name. **Use a value** turns it back into a plain value.

## Where a value goes

This matters, so here it is in full. Your drafts, templates and systems hold only a **reference** to a secret. The value leaves your Keychain **only at deploy time, and only to the host you deploy to**:

| Deploy | What happens to the value |
|---|---|
| Compose stack over SSH | Written into `.env` next to the compose file, on that host, with mode 600 (readable only by your user). |
| Portainer stack | Sent to your Portainer server, which stores the environment. |
| A single container | Becomes part of the container's environment. **Anyone who can inspect the container on the host can read it.** |
| A private Git repository | The username and token you typed go into a mode-600 credentials file beside the clone. The phone does not keep them. |

meshDeck warns you when a redeploy involves vault values. What is on your hosts, and who can read it, depends on how you secure them.

<div class="note note--warn" markdown="1">
**Not the same as never leaving the phone**

A secret is safe in your Keychain, and out of your compose files. But to run a container, the host has to receive the value. The vault keeps secrets out of YAML, drafts and screenshots. It cannot keep them from the host that needs them.
</div>

AI diagnosis never receives a vault value. A variable bound to the vault is replaced by a placeholder naming the entry before anything is sent.
