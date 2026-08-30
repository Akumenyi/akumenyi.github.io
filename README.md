# akumenyi.github.io

Personal academic site of **Kwesi A. Quagraine, PhD** — Chief Scientist of the Climate Vulnerable
Forum and V20 (CVF-V20), and Visiting Scientist at the NSF National Center for Atmospheric Research
(NSF-NCAR), Boulder, Colorado.

Live at **[akumenyi.github.io](https://akumenyi.github.io)**.

## What is here

A static Jekyll site with three things that keep themselves up to date:

- **Publications** — regenerated daily from ORCID-matched records on OpenAlex, with citation
  counts from Google Scholar where a SerpAPI key is configured. Searchable and filterable.
- **LinkedIn activity** — mirrored from a feed URL into `/updates/` and the home page.
- **Blog** — plain Markdown in `_posts/`, with tag filtering and an RSS feed.

Everything else — research, projects, CV — is hand-written content in Markdown.

## Stack

Jekyll on GitHub Pages (no custom build step), a self-contained theme in `_layouts/`,
`_includes/` and `assets/css/main.css`, and two Python fetchers in `scripts/` driven by a
scheduled GitHub Action. No JavaScript framework; the site works with JS disabled, minus the
filters and the animated hero.

## Maintaining it

See **[SETUP.md](SETUP.md)** — how to publish a post, how to add a paper the automation
cannot see, and how to connect the LinkedIn feed.

```bash
bundle install
bundle exec jekyll serve
```

## Licence

Site content © Kwesi A. Quagraine. The theme code descends from
[contrast](https://github.com/niklasbuschmann/contrast) (public domain) but has been
rewritten; see `UNLICENSE.txt`.
