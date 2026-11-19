# abm-news-pulse

**A weekly news radar for your target accounts: funding, acquisitions, new leaders, expansions, launches, layoffs and security incidents, each turned into a scored ABM signal. Free, from the GDELT Project.**

[GDELT](https://www.gdeltproject.org) monitors news in 65+ languages worldwide and offers a free search API. This repo asks it about each account, keeps articles whose headline names the company, removes syndicated copies, and classifies headlines into events you can act on.

## What it finds

| Signal | Headline examples | Default play |
|---|---|---|
| `news_acquisition` | "acquires", "merger", "to buy" | `post_merger_integration` |
| `news_funding` | "raises", "Series B", "valuation" | `growth_budget_window` |
| `news_leadership` | "appoints", "names new CFO", "steps down" | `new_leader_first_90_days` |
| `news_expansion` | "opens", "expands", "new headquarters" | `expansion_support` |
| `news_layoffs` | "layoffs", "restructuring" | `cost_reduction_pitch` |
| `news_security_incident` | "breach", "ransomware", "outage" | `incident_response_support` |
| `news_product_launch`, `news_partnership`, `news_recognition`, `news_legal_regulatory`, `news_earnings` | ... | see config |
| `news_volume` | 20+ new articles in the window = coverage spike | `timely_reference` |

Patterns, weights and plays: [`config/events.yaml`](config/events.yaml). Each signal links the newest matching article.

## Quickstart (no keys)

```bash
git clone https://github.com/Rahul-peacenik159/abm-news-pulse.git
cd abm-news-pulse
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m news_pulse run --accounts sample-data/accounts.csv --timespan 7d
```

GDELT allows one request every 5 seconds, so 10 accounts take about a minute.

**Your accounts:** CSV with `domain` and `company`. For names that are common words (Notion, Harbor, Apple...) add a `news_query` column with a more specific GDELT query, e.g. `"Harbor AI"` or `"Notion" (productivity OR software)`; the headline-name filter is skipped for those rows.

## Run it on GitHub

**Actions > run > Run workflow**, pick the window (24h to 1 month) and the account list. Results table on the Summary page, CSVs in the **results** artifact. Re-runs report only articles not seen before. Uncomment `schedule:` for a weekly run.

> Public repo = public results. Keep real account lists in a **private** copy.

## n8n

[`n8n/news-pulse-weekly.json`](n8n/news-pulse-weekly.json): weekly > accounts > GDELT (6 s between calls) > classify headlines > BigQuery.

## BigQuery (GDELT Global Knowledge Graph)

[`bigquery/10_gkg_org_mentions.sql`](bigquery/10_gkg_org_mentions.sql) counts articles, outlets and average tone per account over the last N days, using GDELT's organization tags instead of headline matching. Negative average tone flags trouble. **Dry-run it and cap bytes first**: the GKG is large.

## Limits

- Headline classification is keyword-based; read the article before quoting it.
- GDELT covers online news, not press-release wires behind paywalls; small private companies may get little coverage.
- Ambiguous company names produce noise; use `news_query`.

## Part of the open ABM bundles

| Repo | What it adds |
|---|---|
| [abm-tech-footprint](https://github.com/Rahul-peacenik159/abm-tech-footprint) | what accounts run on their website, DNS and email; security and email posture |
| [abm-hiring-signals](https://github.com/Rahul-peacenik159/abm-hiring-signals) | who is hiring for what (Greenhouse, Lever, Ashby public job boards) |
| [abm-public-company-triggers](https://github.com/Rahul-peacenik159/abm-public-company-triggers) | SEC filings: exec changes, M&A, restructuring, keyword mentions, revenue trend |
| **abm-news-pulse** (this repo) | news events per account from GDELT (funding, M&A, launches, leadership, layoffs) |
| [abm-tam-builder](https://github.com/Rahul-peacenik159/abm-tam-builder) | build the account universe from Wikidata, OpenStreetMap and US Census data |
| [abm-dev-community-signals](https://github.com/Rahul-peacenik159/abm-dev-community-signals) | which companies' engineers engage with your or competitors' GitHub repos; HN mentions |
| [abm-market-timing](https://github.com/Rahul-peacenik159/abm-market-timing) | topic and region demand: Wikipedia attention, news volume, Google Trends in BigQuery |
| [abm-public-sector-buyers](https://github.com/Rahul-peacenik159/abm-public-sector-buyers) | government buyers: USAspending awards, incumbents, SAM.gov open opportunities |
| [abm-activation-kit](https://github.com/Rahul-peacenik159/abm-activation-kit) | combine all signals, score, and push to HubSpot, LinkedIn audiences and 1:1 pages |

## License

Apache-2.0. News data via the GDELT Project; article content belongs to its publishers.
