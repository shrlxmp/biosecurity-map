# The Biosecurity Defence Chain

An interactive map of the biosecurity field: **every organisation in the
[biosecurity.world](https://biosecurity.world/) dataset, arranged as the layers of defence a
pandemic threat has to get through.**

**→ [View the map](https://shrlxmp.github.io/biosecurity-map/)**

Feedback very welcome — please open an issue, or comment on anything that looks wrong,
misplaced or missing.

## What it is

Biosecurity is built as *defence in depth*: a series of barriers, each catching what the
last one missed. The map draws that literally. A threat has to cross three barriers to reach
the people at the centre:

| Ring | |
|---|---|
| **Prevention** | outer barrier — stop a dangerous agent being made or released at all |
| **Detection** | middle barrier — spot an outbreak while containing it is still cheap |
| **Response** | inner barrier — blunt an outbreak already spreading |
| **Foundation** | dashed outermost ring, not a barrier: the funders, educators, coordinators and reporters the other three stand on |

Across the three barriers, radius carries meaning: the further out an organisation sits, the
earlier in the chain it acts. Each organisation sits on one ring only, the one for its main
mission. By that count Detection has the fewest organisations of the three barriers, but many
more organisations on other rings work on detection topics such as pathogen surveillance. The
page shows both numbers, worked out from the data on every build, so the counts and the
claims stay true after each refresh.

Four views:

- **The map** — the rings, with every organisation as a clickable logo
- **Chain view** — the same four groups as labelled columns, easier to read down a list
- **Where the gaps are** — organisations per topic, plus the full topic-by-work-type grid
  where empty cells show combinations nobody covers
- **How topics connect** — which topics are worked on by the same organisations

## Data

All organisation data comes from **[biosecurity.world](https://biosecurity.world/)**, which
publishes it openly ([entries.csv](https://biosecurity.world/data/entries.csv),
[source](https://github.com/biosecurity-world/biosecurity.world)). That site is the
maintained, authoritative version of this landscape and is updated weekly; this repo is a
visualisation layer over it, not a replacement or a fork of the dataset.

Snapshot in this repo: `build/entries.csv`, refreshed weekly by the workflow below.

Newsletters and podcasts listed in the dataset (entries named `Newsletter - …` or
`Podcast - …`) are left off the map: they are publications rather than organisations, and
most repeat an organisation that is already on it. `build.py` drops them at build time;
`entries.csv` keeps them.

Logos are each organisation's own favicon, fetched once and inlined, used for
identification only.

### Reading caveats

- The rings are a **diagram, not geography**. Where a dot sits *within* a ring means
  nothing — only which ring it is in.
- Each organisation is placed **once**, at its primary classification in the dataset, so
  ring counts here run lower than the counts on biosecurity.world, which lists an
  organisation under every stage it touches. A thin ring means few organisations whose
  *main* mission is that stage, not that little work happens there.
- Counts reflect who is **catalogued** — not budget, headcount or output. A sparse ring may
  mean a genuine gap, a gap in the dataset's coverage, or a layer where a few very large
  institutions do most of the work.

## Staying current

The map **refreshes itself weekly**. A scheduled GitHub Actions workflow
(`.github/workflows/refresh.yml`) runs every Monday: it pulls the latest `entries.csv` from
biosecurity.world, fetches logos for any newly listed organisations, rebuilds `index.html`,
and commits only if something actually changed. GitHub Pages redeploys automatically.

It can also be run on demand from the **Actions** tab → *Refresh map from biosecurity.world*
→ *Run workflow*.

Downloads are validated for schema and row count before `entries.csv` is overwritten, so a
moved URL or an error page fails the run loudly rather than quietly publishing an empty map.

## Rebuilding by hand

The published page is a single self-contained `index.html` with the data and all logos
inlined. No build step is needed to host it; GitHub Pages serves the file directly.

To regenerate it locally:

```bash
python build/fetch_logos.py          # refresh cached favicons -> build/logos.json
python build/build.py                # rebuild index.html from build/entries.csv
python build/build.py --refresh      # re-download entries.csv from biosecurity.world first
```

`build/template.html` is the page with `__ORGS__` / `__LOGOS__` / `__COUNT__` placeholders where the data
is injected. Edit the template, not `index.html` — `index.html` is generated and will be
overwritten.

Requires Python 3 only; no dependencies.

## Licence

Code in this repository: MIT (see `LICENSE`).

Organisation data belongs to biosecurity.world and its contributors — please credit them,
not this repo, as the source. Logos are the property of the respective organisations.
