---
layout: page
title: "Updates"
permalink: /updates/
wide: true
eyebrow: "Field notes"
lede: "Talks, papers, fieldwork and the occasional argument about governance — posted on LinkedIn and mirrored here automatically."
description: "Latest LinkedIn posts and research updates from Kwesi A. Quagraine, Chief Scientist of the CVF-V20 and Visiting Scientist at NSF NCAR."
---

<div class="updates-feed">
  {% include linkedin-feed.html limit=12 %}
</div>

## How this feed works

Posts appear here on their own. A scheduled GitHub Action reads a feed of my LinkedIn activity once a
day and writes it into `_data/linkedin.json`, which this page renders — so what you see is whatever I
last posted, not a snapshot someone remembered to update.

LinkedIn does not offer a public read API for a member's own posts, so the sync runs through a feed
URL rather than LinkedIn's own API. If a post is missing, it is almost certainly waiting on the next
daily run. The [full profile](https://www.linkedin.com/in/kwesi-a-quagraine-12855153/){:target="_blank"}
is always the definitive version.

## Elsewhere

New papers land on the [publications page]({{ '/publications/' | relative_url }}) through the same
mechanism, matched on [ORCID {{ site.profile.orcid }}](https://orcid.org/{{ site.profile.orcid }}){:target="_blank"}
so that only my own work is listed. Code and analysis notebooks are on
[GitHub](https://github.com/Akumenyi){:target="_blank"}.
