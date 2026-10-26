# Who Funds Biosecurity

**Who funds the biosecurity field, and who goes without.** Grants from philanthropic funders
and government awards, matched to every organisation in the
[biosecurity.world](https://biosecurity.world/) dataset and laid out as the layers of defence a
pandemic threat has to get through.

**→ [View the map](https://shrlxmp.github.io/biosecurity-map/)**

Feedback is very welcome. Please open an issue about anything that looks wrong, misplaced or
missing.

## What it is

Biosecurity is built as *defence in depth*: a series of barriers, each catching what the
last one missed. The map draws that literally. A threat has to cross three barriers to reach
the people at the centre.

| Ring | What it does |
|---|---|
| **Prevention** | Outer barrier. Stops a dangerous agent being made or released at all. |
| **Detection** | Middle barrier. Spots an outbreak while containing it is still cheap. |
| **Response** | Inner barrier. Slows an outbreak that is already spreading. |
| **Foundation** | Dashed outermost ring, not a barrier. The funders, educators, coordinators and reporters the other three rely on. |

Across the three barriers, radius carries meaning: the further out an organisation sits, the
earlier in the chain it acts. Each organisation sits on one ring only, the one for its main
mission. By that count Detection has the fewest organisations of the three barriers, but many
more organisations on other rings work on detection topics such as pathogen surveillance. The
page shows both numbers and works them out from the data on every build, so the counts and
the claims stay true after each refresh.

There are five views. The page opens on the first:

- **Where the money goes.** Biosecurity grants from seven philanthropic funders and four
  government sources, set against the map: each ring's share of the organisations next to its
  share of the funding, grants by year, the largest recipients, organisations with no grant
  found, and funded organisations the map does not list. Gavi and CEPI are left out by default,
  because a few vaccine grants to them (62% of the philanthropic money matched to the map)
  would outweigh everything else; a toggle adds them back. The same grants appear in each
  organisation's detail panel and, with *Show funding*, as discs on the map.
- **The map.** The rings, with every organisation as a clickable logo.
- **Chain view.** The same four groups as columns of names, easier to read down.
- **Where the gaps are.** Organisations per topic, plus the full grid of topics against types
  of work, where empty cells show combinations nobody covers.
- **How topics connect.** Which topics are worked on by the same organisations.

## Data

All organisation data comes from **[biosecurity.world](https://biosecurity.world/)**, which
publishes it openly ([entries.csv](https://biosecurity.world/data/entries.csv),
[source](https://github.com/biosecurity-world/biosecurity.world)). That site is the
maintained, authoritative version of this landscape and is updated weekly. This repo is a
visualisation built on top of it, not a replacement or a fork of the dataset.

The snapshot in this repo is `build/entries.csv`, refreshed weekly by the workflow below.

Newsletters and podcasts listed in the dataset (entries named `Newsletter - …` or
`Podcast - …`) are left off the map. They are publications rather than organisations, and
most repeat an organisation that is already on it. `build.py` drops them at build time, and
`entries.csv` keeps them.

### Organisations added here

`build/extra_entries.csv` adds organisations that biosecurity.world does not list yet, in the
same columns as its dataset (ids start at 900001 so they never clash). They are drawn like
any other organisation, and each one's detail panel says it was added by this map, so its
classification is ours rather than biosecurity.world's. The six there now were picked
because they receive Coefficient Giving biosecurity grants and meet biosecurity.world's own
[inclusion criteria](https://docs.google.com/document/d/12JhGqx5PaA_jD0UKPDfWX4dfDp1gBoxdVM5tDTykPCA/edit).

When biosecurity.world adds one of them (same website, or a matching name), the build leaves
our row out and prints a notice to delete it, so an organisation never appears twice. The
better fix is always to suggest the organisation to biosecurity.world through
[their form](https://biosecurityworld.notion.site/33a4061a75b7806fad1dee0fcd2e921a).

Logos are each organisation's own favicon, fetched once and inlined, and used for
identification only.

### Funding

Grants come from seven philanthropic funders. Each funder has a rule for what counts as a
biosecurity grant, and the rule decides which recipients its grants are counted for:

| Funder | What counts | Counted for |
|---|---|---|
| Coefficient Giving (formerly Open Philanthropy) | Its own two biosecurity focus areas | Everyone |
| Sentinel Bio | All its grants (it funds biosecurity only) | Everyone |
| OpenAI Foundation | Grants Trace tags as biosecurity | Everyone |
| Longview Philanthropy | Its biosecurity programme, or grants whose description names biosecurity work | Everyone |
| Gates Foundation | Our rule: grants from its health, development and policy divisions whose purpose names pandemic or epidemic threats, leaving out routine diseases (polio, HIV, malaria) unless the purpose is pandemic preparedness | Organisations on the map only |
| Wellcome | Our rule: grants whose title names pandemic or epidemic threats, or whose description is plainly about pandemic preparedness or biosecurity, leaving out routine diseases; pounds converted to dollars at each year's average rate | Organisations on the map only |
| Survival and Flourishing Fund | Our rule: it has no labels, so only grants to four organisations whose main work is biosecurity (SecureBio, SecureDNA, Amodo Design, Blueprint Biosecurity) | Those four only |

Where a funder labels its own biosecurity grants, its label is used, so the funder decides what
counts. Where it doesn't, the rule is ours, and the grants are counted only for organisations on
the map, because a keyword rule is too loose to trust for everyone else.

Sources: Coefficient Giving's grants come from the full export kept in the open repository of
[Trace](https://trace.manifund.org/) ([source](https://github.com/manifund/trace)), Manifund's
funding database, as do the OpenAI Foundation's and Longview's. Trace's own website lists only
grants with an AI-safety angle; its repository files are what this repo uses. Gates comes from
its [committed grants database](https://www.gatesfoundation.org/about/committed-grants),
Wellcome from its grants spreadsheet, published as
[360Giving](https://www.threesixtygiving.org/) open data under CC BY 4.0 (the build finds the
current file through the 360Giving registry, because its name changes with every release),
Sentinel Bio from its [grants page](https://sentinelbio.org/research-and-projects/), and SFF
from its [recommendations table](https://survivalandflourishing.fund/recommendations).

`build/fetch_funding.py` writes one file per funder to `build/funding/`, each with its rule
written out. It refreshes each funder separately, so if one site is down the others still
update. `build.py` matches recipients to organisations on the map by name. Where the names
differ, it uses `build/funding_aliases.json`, a short list of links checked by hand against the
grant titles (for example *GAVI Alliance* for Gavi, or *Blue Ribbon Study Panel on Biodefense*,
the former name of the Bipartisan Commission on Biodefense). The build prints, for each funder,
the largest recipients it could not match.

### Government funding

Government awards are shown as a separate layer and never added to the philanthropic totals.
The money picker has each source on its own and an *All government sources* view. There are
four sources, and `build/government_recipients.json` says which names count for each.

| Source | Who | What counts |
|---|---|---|
| US federal ([USAspending](https://www.usaspending.gov/)) | Exact recipient names, companies included | See below |
| US NIH, for university centres ([RePORTER](https://reporter.nih.gov/)) | Grants led by the researchers who lead a centre (Lipsitch for CCDD, Osterholm for CIDRAP, Bedford for Nextstrain, Esvelt), at that university | Title names pandemic or outbreak work, influenza, coronaviruses or biodefence; routine diseases left out |
| EU research ([CORDIS](https://cordis.europa.eu/)) | Named partners in Horizon 2020 and Horizon Europe projects, counting only that partner's own share | A call dedicated to epidemics or preparedness, or a title or summary plainly about it; euros converted at each year's average rate |
| UK Research and Innovation ([Gateway to Research](https://gtr.ukri.org/)) | Projects the organisation leads | UKRI's COVID-19 rapid response, or a title or abstract about pandemic or biodefence work; pounds converted |

US federal awards cover contracts, grants and cooperative agreements across federal agencies:

- **Who:** a hand-checked list in `build/government_recipients.json` of the exact names
  organisations on the map appear under (*MODERNATX, INC.*, *TRIAD NATIONAL SECURITY, LLC* for
  Los Alamos). University-based centres such as Johns Hopkins CHS or CIDRAP are left out,
  because their awards go to the university and can't be told apart.
- **From whom:** Health and Human Services (including NIH and CDC), Defense, Homeland
  Security, USAID and State. Energy and Veterans Affairs are left out, because their awards to
  these organisations are national-lab operating contracts and routine drug purchases.
- **What counts:** the award description has to name pandemic or biodefence work, or a named
  product such as Paxlovid or the Ervebo Ebola vaccine, and routine diseases are left out.
  Every award from HHS's preparedness office (ASPR, which runs BARDA) counts, because
  preparedness is its whole remit, except its chemical, radiological and nuclear work.
- **What's missing:** awards made through contracting consortia, which USAspending lists under
  the consortium. Much of Operation Warp Speed went this way, including Novavax's main
  COVID-19 award.

Amounts are total obligations. Contracts that buy finished products (COVID-19 vaccine doses,
treatment courses, stockpiled drugs) are marked as purchases: a contract counts as one when
its description says it buys ("doses", "procurement", "donation") or names only a product,
with no research words. That is 16 contracts and $44B, 93% of the US federal money. The page
leaves purchases out by default and has a toggle to add them back, because they pay for
products rather than biosecurity work. The rule only reads descriptions, so a contract that
mixes development and supply counts as research when that's how it's described, as Moderna's
$1.75B "development of mRNA vaccine to licensure" contract is. The fetch takes a few minutes: it pages through each organisation's US
awards and downloads the CORDIS project files (about 90MB).

Known gaps: Johns Hopkins CHS, the Pandemic Center and Georgetown CGHSS have no NIH grants
under their leaders, so they show none. UKRI money mostly goes to universities, which the
lead-organisation rule can't tie to a centre, so that source is small. Other national
governments are not covered.

What the funding numbers are not:

- **Not the size of the field.** These are seven philanthropic funders. Governments and industry
  spend far more and are not counted. A handful of very large grants (Gates and Wellcome to Gavi and CEPI)
  carry most of the total, so the page lets you look at one funder at a time.
- **Not money spent.** Amounts are as awarded, and a multi-year grant counts in the year it
  was made.
- **Not always the final recipient.** Some grants pay for the recipient's own grantmaking, or go
  to a funder that is itself in this data, so the money may be counted again when it is given
  on, or end up with organisations the page cannot see. The page says how much.
- **Not complete matching.** A grant to a name the map does not use counts as not on the map,
  even if it went to an organisation that is.

### Reading caveats

- The rings are a **diagram, not geography**. Where a dot sits *within* a ring means
  nothing, only which ring it is in.
- Each organisation is placed **once**, at its primary classification in the dataset, so
  ring counts here run lower than the counts on biosecurity.world, which lists an
  organisation under every stage it touches. A thin ring means few organisations whose
  *main* mission is that stage, not that little work happens there.
- Counts show who is **catalogued**, not budget, headcount or output. A sparse ring may be a
  real gap, a gap in the dataset's coverage, or a layer where a few very large institutions
  do most of the work.

## Staying current

The map **refreshes itself weekly**. A scheduled GitHub Actions workflow
(`.github/workflows/refresh.yml`) runs every Monday. It pulls the latest `entries.csv` from
biosecurity.world, refreshes the funders' grants, fetches logos for any newly listed
organisations, rebuilds `index.html`, and commits only if something changed. If the grants
can't be fetched, the map still refreshes using the last saved grants. GitHub Pages then redeploys on its own.

You can also run it on demand from the **Actions** tab → *Refresh map from biosecurity.world*
→ *Run workflow*.

Downloads are checked for the expected columns and row count before `entries.csv` is
overwritten, so a moved URL or an error page makes the run fail instead of publishing an
empty map.

## Rebuilding by hand

The published page is a single self-contained `index.html` with the data and all logos
inlined. Hosting it needs no build step, because GitHub Pages serves the file directly.

To regenerate it locally:

```bash
python build/fetch_logos.py          # refresh cached favicons -> build/logos.json
python build/build.py                # rebuild index.html from build/entries.csv
python build/build.py --refresh      # re-download entries.csv from biosecurity.world first
python build/fetch_funding.py        # refresh funders' grants -> build/funding/*.json
python build/fetch_funding.py us_federal   # just one funder (keys are the file names)
```

`build/template.html` is the page with `__ORGS__`, `__LOGOS__`, `__FUNDING__` and `__COUNT__`
placeholders where the data goes. Edit the template, not `index.html`, which is generated and gets
overwritten.

The build needs Python 3 only, with no dependencies.

## Licence

Code in this repository: MIT (see `LICENSE`).

Organisation data belongs to biosecurity.world and its contributors. Please credit them, not
this repo, as the source. Grant records belong to the funders that published them; Trace's compilation is released
under CC0 and its code is MIT-licensed. Logos are the property of the respective organisations.
