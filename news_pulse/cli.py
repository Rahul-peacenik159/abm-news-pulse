"""python -m news_pulse run --accounts sample-data/accounts.csv
python -m news_pulse summary out"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import pulse
from .common import Snapshots, load_yaml, read_accounts, score_rows, summary_or_note, write_outputs

ROOT = Path(__file__).resolve().parent.parent
SUMMARY_FIELDS = ["account_domain", "company", "score", "top_play", "events", "new_articles", "articles",
                  "top_headline", "top_url", "query", "errors"]


def cmd_run(args) -> None:
    cfg = load_yaml(args.config)
    accounts = read_accounts(args.accounts, args.domains)
    if not accounts:
        sys.exit("No accounts: pass --accounts file.csv (domain, company, optional news_query)")
    http = pulse.client()
    timespan = args.timespan or cfg.get("timespan", "7d")
    snaps = Snapshots(args.out, "articles")
    all_rows, summaries, errors = [], [], 0
    print(f"Checking news ({timespan}) for {len(accounts)} accounts (GDELT allows 1 request / 5 s)")
    for i, acc in enumerate(accounts, 1):
        domain = acc["domain"] or acc.get("company", "")
        company = acc.get("company") or domain.split(".")[0]
        query = pulse.build_query(acc, cfg)
        try:
            arts = pulse.fetch_articles(http, query, timespan, cfg.get("max_articles", 75))
            name_req = cfg.get("require_name_in_title", True) and not acc.get("news_query")
            rows, summary, keys = pulse.classify(domain, company, arts, cfg, snaps.seen_before(domain), name_req)
            snaps.record(domain, keys)
            score, play = score_rows(rows)
            summaries.append({"account_domain": domain, "company": company, "score": score, "top_play": play,
                              "query": query, "errors": "", **summary})
            all_rows += rows
            print(f"  [{i}/{len(accounts)}] ok  {domain:<28} articles={summary['articles']:<3} {summary['events'][:60]}")
        except Exception as exc:
            errors += 1
            summaries.append({"account_domain": domain, "company": company, "score": 0, "query": query,
                              "errors": f"{type(exc).__name__}: {exc}"[:200]})
            print(f"  [{i}/{len(accounts)}] ERR {domain}: {exc}")
    stamp = snaps.save()
    out = write_outputs(args.out, all_rows, summaries, SUMMARY_FIELDS, {
        "repo": "abm-news-pulse", "run_at": stamp, "timespan": timespan, "accounts": len(accounts),
        "errors": errors, "previous_run": snaps.previous_name,
        "new_items": sum(int(s.get("new_articles") or 0) for s in summaries)})
    print(f"\nWrote {len(all_rows)} signals to {out}/")


def cmd_summary(args) -> None:
    cols = [("account_domain", "Account"), ("score", "Score"), ("top_play", "Top play"), ("events", "Events"),
            ("new_articles", "New articles"), ("top_headline", "Latest headline"), ("errors", "Errors")]
    print(summary_or_note(Path(args.out) / "accounts_summary.csv", cols, "News pulse (GDELT)"))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="news_pulse", description="News events per account from GDELT")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--accounts", help="CSV with domain, company and optional news_query columns")
    r.add_argument("--domains", nargs="*")
    r.add_argument("--config", default=str(ROOT / "config" / "events.yaml"))
    r.add_argument("--timespan", help="24h, 3d, 7d, 2w, 1m ... (default from config)")
    r.add_argument("--out", default="out")
    r.set_defaults(func=cmd_run)
    s = sub.add_parser("summary")
    s.add_argument("out", nargs="?", default="out")
    s.set_defaults(func=cmd_summary)
    args = ap.parse_args(argv)
    args.func(args)
