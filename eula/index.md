---
title: Licence Agreement
eyebrow: Legal
lede: The terms on which you may use meshDeck.
description: The End User Licence Agreement for meshDeck, the iPhone and iPad app for Docker and Portainer hosts.
---
<div class="legal" markdown="1">

<div class="note legal-note" markdown="1">
**Not legal advice**

This agreement has not been reviewed by a solicitor. It is provided in good faith and in plain language. If you need legal advice, please consult a qualified solicitor.
</div>

<p class="meta"><span>{{ site.company }} · company number {{ site.company_number }}</span><span>Effective {{ site.legal_effective }}</span><span>Version {{ site.legal_version }}</span></p>

<p class="short" markdown="1">**Short version:** meshDeck is licensed to you, not sold. You may use it on your own devices to manage hosts you are allowed to manage. You are responsible for what you do to those hosts. The app is provided as it is, and our liability is limited as far as the law allows. Apple's minimum terms apply as well.</p>

This End User Licence Agreement ("Agreement") is between you ("you") and **{{ site.company }}**, company number {{ site.company_number }} ("we", "us", "our"), for your use of **meshDeck** (the "App"), an application for iPhone and iPad. By downloading, installing or using the App you agree to this Agreement. If you do not agree, do not download, install or use the App.

<div class="toc" markdown="1">
<p>Contents</p>

1. [Licence](#1-licence)
2. [Your hosts and your responsibility](#2-your-hosts-and-your-responsibility)
3. [AI diagnosis](#3-ai-diagnosis)
4. [Subscriptions and billing](#4-subscriptions-and-billing)
5. [Third-party services and trademarks](#5-third-party-services-and-trademarks)
6. [Intellectual property and open source](#6-intellectual-property-and-open-source)
7. [Privacy](#7-privacy)
8. [Disclaimer of warranties](#8-disclaimer-of-warranties)
9. [Limitation of liability](#9-limitation-of-liability)
10. [Apple's additional terms](#10-apples-additional-terms)
11. [Changes and termination](#11-changes-and-termination)
12. [Governing law](#12-governing-law)
13. [Contact](#13-contact)
</div>

## 1. Licence

Subject to this Agreement, we grant you a limited, non-exclusive, non-transferable, revocable licence to download, install and use the App on Apple-branded devices that you own or control, and as the Usage Rules in Apple's Media Services Terms and Conditions permit. This includes use by other accounts in your Family Sharing group, where Apple allows it.

You may not:

- copy, modify, translate or create derivative works of the App;
- reverse engineer, decompile or disassemble the App, or try to derive its source code, except to the extent the law allows despite this restriction;
- rent, lease, lend, sell, sublicense or transfer the App to anyone else;
- remove or hide any proprietary notice in the App;
- use the App to gain, or to try to gain, unauthorised access to any system, network or data;
- interfere with, disable or get around any security or access control in the App.

The App may be downloaded and used free of charge for one host. Some features are available through a subscription (section 4). We may change which features are free with reasonable notice.

## 2. Your hosts and your responsibility

meshDeck lets you view and change the state of hosts you connect it to: start, stop, restart, pause, recreate and remove containers, deploy and remove stacks, open a shell in a container, and change environment variables and files the App manages on the host.

You agree that:

- you will only connect meshDeck to systems you own or are authorised to administer;
- you are responsible for every action taken through the App on your hosts, including actions that stop services, remove containers, images, volumes or networks, or change configuration;
- you are responsible for the security of your hosts, your credentials, your SSH keys and access tokens, and your Tailscale and Portainer accounts;
- you will keep backups of anything you cannot afford to lose. Removing a container or a volume can destroy the data in it, and meshDeck cannot bring it back.

The App asks before some of its riskier actions, such as stopping, killing or removing a container or removing a stack, and pins host keys and certificates on first use. It does not ask before others, such as a restart. These are aids, not guarantees, and they do not make you any less responsible for what you choose to do.

## 3. AI diagnosis

AI diagnosis is optional and is off until you add your own API key for a provider you choose and agree to send it evidence. Please read the section of the [Privacy Policy]({{ '/privacy/' | relative_url }}) on what is sent.

The output of an AI model can be wrong, incomplete or out of date. A diagnosis is a suggestion. It is not advice, and it does not replace your own judgement. The App will only offer actions it already knows how to perform, and each one needs your tap, but you decide whether to run it. Some, such as a restart, run as soon as you tap them. Your use of a provider is governed by that provider's own terms, and any charges from a provider are between you and them.

## 4. Subscriptions and billing

"meshDeck Pro" is an auto-renewing annual subscription that lifts the free tier's limit of one host. The price is shown in the App before you subscribe and is the price that applies when you confirm the purchase.

- Payment is charged to your Apple Account when you confirm the purchase.
- The subscription renews automatically unless you turn off auto-renewal at least 24 hours before the end of the current period. Your account is charged for renewal within 24 hours before the end of the current period, at the price shown to you.
- You can manage your subscription and turn off auto-renewal in your Apple Account settings after purchase.
- If we offer a free trial, it converts to a paid subscription at the end unless you cancel at least 24 hours before it ends. Any unused part of a trial ends when you buy a subscription.
- Apple processes all payments. We never see your payment details. Refund requests go to Apple, through [reportaproblem.apple.com](https://reportaproblem.apple.com), and are subject to Apple's policies and your statutory rights.
- We may change the price with reasonable advance notice. A change takes effect at your next renewal, and Apple will tell you and, where required, ask for your consent.

## 5. Third-party services and trademarks

The App works with services we do not control, including Tailscale, Portainer, Docker hosts and AI providers you configure. Those services have their own terms and privacy policies, and you must follow them. We are not responsible for them, for their availability, or for charges they make.

Docker, Portainer and Tailscale are trademarks of their respective owners. meshDeck is independent and is not affiliated with, sponsored by or endorsed by them. Apple, iPhone and iPad are trademarks of Apple Inc.

## 6. Intellectual property and open source

The App, its design and its content belong to us or our licensors and are protected by copyright and other laws. This Agreement does not transfer any ownership to you.

The App includes open source software, each under its own licence. Notices for that software are available in the App and on request.

## 7. Privacy

Our [Privacy Policy]({{ '/privacy/' | relative_url }}) explains what the App does and does not collect, and forms part of this Agreement.

## 8. Disclaimer of warranties

To the fullest extent the law allows, the App is provided **"as is" and "as available"**, without warranties of any kind, express or implied, including any implied warranty of satisfactory quality, fitness for a particular purpose or non-infringement. We do not promise that the App will be uninterrupted or error-free, that it will work with every host, version or configuration, or that its diagnoses or suggestions will be correct.

Nothing in this Agreement affects your statutory rights as a consumer.

## 9. Limitation of liability

To the fullest extent the law allows, we are not liable for any indirect or consequential loss, or for loss of profit, data, use, goodwill or business, arising from your use of, or inability to use, the App, including loss caused by an action you or the App took on your hosts.

Our total liability to you for all claims relating to the App or this Agreement is limited to the greater of the amount you paid for the App in the twelve months before the claim, and £10.

Nothing in this Agreement limits or excludes our liability for death or personal injury caused by our negligence, for fraud or fraudulent misrepresentation, or for anything else the law does not allow us to limit or exclude.

## 10. Apple's additional terms

You and we acknowledge that this Agreement is between you and us only, and not with Apple. We, not Apple, are solely responsible for the App and its content. In particular:

- **Scope of licence.** The licence in section 1 is limited to use on Apple-branded products you own or control, as the Usage Rules in the Apple Media Services Terms and Conditions allow.
- **Maintenance and support.** We are solely responsible for maintenance and support. Apple has no obligation to provide any. Contact details are in section 13.
- **Warranty.** If the App fails to conform to an applicable warranty, you may tell Apple, and Apple will refund the purchase price of the App to you. To the maximum extent the law allows, Apple has no other warranty obligation for the App. Any other claim, loss or cost caused by a failure to conform is our responsibility.
- **Product claims.** We, not Apple, are responsible for any claim relating to the App or your possession or use of it, including product liability claims, claims that the App does not meet a legal or regulatory requirement, and claims under consumer protection, privacy or similar law.
- **Intellectual property.** If a third party claims that the App or your use of it infringes their intellectual property rights, we, not Apple, are solely responsible for investigating, defending, settling and discharging the claim.
- **Legal compliance.** You represent that you are not located in a country subject to a US Government embargo or designated a "terrorist supporting" country, and that you are not on any US Government list of prohibited or restricted parties.
- **Third-party terms.** You must comply with any applicable third-party terms when using the App, such as your wireless data service agreement.
- **Third-party beneficiary.** Apple and its subsidiaries are third-party beneficiaries of this Agreement. When you accept it, Apple will have the right, which it is deemed to have accepted, to enforce this Agreement against you as a third-party beneficiary.

## 11. Changes and termination

We may update this Agreement. For a material change we will update the date at the top and, where appropriate, tell you in the App. If you keep using the App after a change takes effect, you accept it.

This Agreement lasts until it is ended. You can end it at any time by deleting the App and cancelling any subscription. We may end it if you break it, and your licence ends automatically when you do. Sections 2, 8, 9, 10 and 12 continue to apply after it ends.

## 12. Governing law

This Agreement is governed by the laws of England and Wales, and the courts of England and Wales have exclusive jurisdiction, except that if you are a consumer you keep any right you have to bring a claim in the courts of the country where you live and the protection of that country's mandatory consumer laws.

## 13. Contact

**{{ site.company }}**, company number {{ site.company_number }}.
{% if site.company_address %}Registered office: {{ site.company_address }}.{% endif %}
Email: [{{ site.contact_email }}](mailto:{{ site.contact_email }})

Questions, complaints and support requests all come to this address.

</div>
