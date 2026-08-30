# Running and maintaining this site

Everything here is a static Jekyll site built by GitHub Pages. Day-to-day you only
touch three things: `_posts/` for writing, `_data/publications_manual.yml` for papers
the automation cannot see yet, and `_data/linkedin_manual.yml` for pinned posts.

---

## 1. Writing a blog post

1. Copy `_drafts/TEMPLATE.md` into `_posts/`.
2. Rename it `YYYY-MM-DD-a-short-slug.md`. The date sets the publication date and the URL
   (`2026-09-14-harmattan-and-aerosols.md` → `/blog/harmattan-and-aerosols/`).
3. Fill in the front matter — `title`, `summary`, `tags`, and optionally `image`.
4. Write in Markdown, commit, push. GitHub Pages rebuilds within a minute or two.

Tags become filter pills on `/blog/` automatically; reuse the same words and they group.
Posts also flow into the RSS feed at `/feed.xml` and onto the home page.

Keep something unfinished in `_drafts/` (no date in the filename) and it will not publish.
Preview drafts locally with `bundle exec jekyll serve --drafts`.

> The post currently in `_posts/` was written as a starting point when the site was rebuilt.
> Edit it, replace it, or delete the file.

---

## 2. Publications — automatic

`.github/workflows/refresh-research-data.yml` runs every day at 05:20 UTC and regenerates
`_data/publications.json`, which the publications page renders. It merges, in order of trust:

1. `_data/publications_manual.yml` — your curated record. **Always wins.**
2. **OpenAlex**, filtered on ORCID `0000-0002-7887-6040` — picks up new papers and citation counts.
3. **Google Scholar** via SerpAPI — optional, see below.
4. The previous `publications.json` — so a failed fetch never deletes anything.

### Why ORCID and not your name

Surname matching is not precise enough here: several researchers publish under
"Quagraine", including co-authors on your own papers. Every candidate that does not
arrive with your ORCID attached must pass an explicit initials check in
`scripts/update_publications.py`, so only your work enters the record. Do not relax
that check — loosening it to a surname match will silently pull in other people's papers.

**The single most useful thing you can do is claim your ORCID record on every new paper.**
That is what makes the automation work.

### What the harvest filters out

OpenAlex indexes more than journal papers, so the sync drops:

- **works published before 2005** — ORCID records occasionally carry work mis-linked from an
  author-name collision, and the first run pulled in two 1960 soil-science papers this way.
  Change the floor with the `PUBLICATIONS_MIN_YEAR` environment variable;
- **peer-review comments, errata, corrections and supplementary material** — artefacts of the
  publishing process rather than publications;
- **duplicate repository deposits** — a Zenodo or Research Square copy carries its own DOI, so
  entries are keyed on title and the journal version of record always wins on venue, while the
  highest citation count of the set is kept.

Anything dropped for the year rule is named in the workflow log.

### Adding something the automation cannot see

Under-review manuscripts, book chapters, anything without a DOI: add a block to
`_data/publications_manual.yml`. Pushing to `master` re-runs the workflow immediately, so it
appears without waiting for the next cron.

### Optional: real Google Scholar numbers

Google Scholar has no public API and blocks datacentre traffic, so the workflow reads it
through [SerpAPI](https://serpapi.com/google-scholar-author-api) when a key is available.
Without a key the site uses OpenAlex citation counts, which track Scholar closely — the
publications page states which source it used.

To enable it: **Settings → Secrets and variables → Actions → New repository secret**,
name `SERPAPI_API_KEY`, paste the key. Nothing else changes.

---

## 3. LinkedIn posts — automatic

LinkedIn does not offer a public read API for a member's own posts (the Posts API is behind
partner review), so the sync reads a feed URL that you control.

### Setting it up

1. Create an RSS/Atom/JSON feed of your LinkedIn activity. Any of these work:
   - **[RSS.app](https://rss.app/)** — paste your LinkedIn profile URL, it returns a feed URL. Easiest.
   - **[RSSHub](https://docs.rsshub.app/)** — self-hostable, no third party holding your data.
   - **Zapier / Make / n8n** — trigger on a new LinkedIn post, write a JSON Feed to a GitHub gist,
     and point at the gist's raw URL.
2. Add the URL as a repository secret named `LINKEDIN_FEED_URL`
   (**Settings → Secrets and variables → Actions**).
3. Done. Posts appear on `/updates/` and the home page within a day.

The parser understands RSS 2.0, Atom and JSON Feed, and pulls the activity URN out of post
URLs so posts can also render as native LinkedIn embeds.

### Without a feed

The section stays useful: it shows anything pinned in `_data/linkedin_manual.yml` plus a
"Follow on LinkedIn" card. To pin a post, paste its "Copy link to post" URL into that file.

### Native embeds

Set `linkedin_embed: true` in `_config.yml` to render each post as LinkedIn's own embed
iframe rather than a text card. Embeds are heavier and only work for public posts, which is
why they are off by default.

---

## 4. Warming stripes

Every page header carries a faint warming-stripes backdrop and a saturated stripe rule
along its bottom edge, and the home page shows a grid of member-state stripes. All of it
is real data — annual temperature anomalies from **Berkeley Earth**, the same source behind
Ed Hawkins' [#ShowYourStripes](https://showyourstripes.info/).

### Changing which countries appear

Edit `_data/cvf_members.yml`. Each entry needs a `slug` (Berkeley Earth's own country
slug, lowercase and hyphenated) and a `name`; `feature: true` puts it in the home-page grid.
The next workflow run fetches it and writes `assets/img/stripes/<slug>.svg`.

**Please check the membership list.** It was seeded from widely reported CVF membership and
has not been verified against the Forum's roster.

Not every country has a Berkeley record — the Maldives does not, for instance, because there
is too little land area to average. A country that cannot be fetched is simply left out; it
is never drawn from invented numbers.

### Changing which country a page uses

Set `stripes: ghana` in a page's front matter. Unknown or not-yet-rendered slugs fall back to
`stripes_default` in `_config.yml`. Current assignments:

| Page | Country |
|---|---|
| Home | Ghana |
| Research | Bangladesh |
| Publications | Philippines |
| Blog | Kenya |
| Projects | Malawi |
| Updates | Fiji |
| Footer rule, 404 | Global land |

### Adding the organisation logos

The header brand mark and the affiliation strip both show a text wordmark until a real logo
file exists. To swap in the mark:

1. Save the file as `assets/img/cvf-v20-logo.svg` — `.png`, `.jpg` and `.webp` also work, and
   the site picks up whichever it finds, so no config change is needed. The NSF NCAR slot uses
   `assets/img/nsf-ncar-logo.*` the same way.
2. Commit it. On GitHub: **Add file → Upload files**, drag it into `assets/img/`, commit.

That is the whole job — both slots fill in on the next build.

The logo is never recoloured, cropped or redrawn. Because these marks carry dark text that
would disappear against the dark theme, the site presents them on a white plate with padding
and a hairline border, which is why a transparent background is fine and preferred.

### Using a photograph instead

Set `hero_image: /assets/img/your-photo.jpg` in a page's front matter and it replaces the
stripes wash in that page's header, dimmed and faded so the headline still leads. The stripe
rule along the bottom edge stays.

### Method

Annual value = the mean of that year's twelve monthly anomalies, so a partial current year is
dropped rather than biased. Anomalies are re-centred on 1971–2000, and the colour scale spans
±2.6 standard deviations of the 1901–2000 values, mapped onto ColorBrewer RdBu reversed —
the #ShowYourStripes convention. Records start in 1850 or when the country's record begins.

The script reads the region name out of each Berkeley file and refuses to render a country
whose file reports a different region, so a renamed slug cannot silently mislabel a chart.

```bash
python scripts/warming_stripes.py              # all countries
python scripts/warming_stripes.py --only ghana # one
```

## 5. Running the site locally

```bash
bundle install
bundle exec jekyll serve      # http://localhost:4000
bundle exec jekyll serve --drafts
```

To test the data scripts without waiting for the workflow:

```bash
pip install -r scripts/requirements.txt

python scripts/update_publications.py            # hits OpenAlex
python scripts/update_publications.py --offline  # rebuild from local files only
python scripts/update_linkedin.py --feed-url "https://…"
```

Both scripts leave the JSON untouched when nothing substantive changed, so they do not
generate empty commits.

---

## 6. Where things live

| Path | What it is |
|---|---|
| `_config.yml` | Site identity, navigation, profile links, the name-disambiguation text |
| `_data/publications_manual.yml` | **Curated publication record — edit this one** |
| `_data/publications.json` | Generated. Do not edit; the workflow overwrites it |
| `_data/linkedin_manual.yml` | Pinned LinkedIn posts |
| `_data/linkedin.json` | Generated |
| `_data/cvf_members.yml` | **Countries whose warming stripes are drawn** |
| `_data/warming_stripes.json` | Generated |
| `assets/img/stripes/` | Generated SVGs, one per country |
| `_posts/` | Blog posts |
| `_drafts/TEMPLATE.md` | Starting point for a new post |
| `_layouts/`, `_includes/` | Page templates |
| `assets/css/main.css` | All styling. Colours are CSS variables at the top |
| `assets/js/site.js` | Theme toggle, nav, hero animation, filters |
| `scripts/` | The data fetchers and the social-card generator |
| `.github/workflows/` | The daily refresh |
| `_archive/` | Superseded publication pages, kept for reference. Not published |

### Changing the look

The palette is the block of CSS variables at the top of `assets/css/main.css` — `--teal`,
`--azure`, `--violet` drive every gradient and accent on the site, in both light and dark
mode. Change those three and the whole site follows.
