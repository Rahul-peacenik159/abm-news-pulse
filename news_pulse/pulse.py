"""GDELT DOC 2.0 API client and pure classification logic.

API: https://api.gdeltproject.org/api/v2/doc/doc  (free, no key)
GDELT asks for at most one request every 5 seconds; the client waits 5.5 s.
"""
from __future__ import annotations

import re

from .common import Http, parse_dt, signal

DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
PACK = "news-pulse"
_SUFFIX = re.compile(r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|llc|holdings?|group|technologies|labs)\b\.?", re.I)


def client() -> Http:
    return Http("abm-news-pulse/0.1 (+https://github.com/Rahul-peacenik159/abm-news-pulse)", min_interval=5.5, timeout=45)


def short_name(company: str) -> str:
    return re.sub(r"\s+", " ", _SUFFIX.sub(" ", company or "")).strip(" ,.")


def build_query(account: dict, cfg: dict) -> str:
    if account.get("news_query"):
        q = account["news_query"]
    else:
        name = short_name(account.get("company") or account.get("domain", "").split(".")[0])
        q = f'"{name}"' if " " in name else name
    lang = cfg.get("source_language")
    return f"{q} sourcelang:{lang}" if lang else q


def fetch_articles(http: Http, query: str, timespan: str, max_records: int) -> list[dict]:
    r = http.request("GET", DOC_API, params={"query": query, "mode": "artlist", "format": "json",
                                             "maxrecords": max_records, "timespan": timespan, "sort": "datedesc"})
    r.raise_for_status()
    try:
        return r.json().get("articles", []) or []
    except ValueError:  # GDELT answers plain text for bad queries / rate limits
        raise RuntimeError(f"GDELT: {r.text.strip()[:150]}") from None


def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (t or "").lower())[:90]


def classify(domain: str, company: str, articles: list[dict], cfg: dict, seen_before: set | None,
             name_required: bool) -> tuple[list[dict], dict, list[str]]:
    """Returns (signal rows, summary, snapshot keys)."""
    name = short_name(company).lower()
    events = [(k, re.compile(v["regex"], re.I), v) for k, v in cfg["events"].items()]
    kept, titles = [], set()
    for a in articles:
        t = a.get("title") or ""
        if name_required and name and name not in t.lower():
            continue
        nt = _norm_title(t)
        if nt in titles:  # syndicated copies
            continue
        titles.add(nt)
        kept.append(a)
    new = [a for a in kept if seen_before is None or a.get("url") not in seen_before]
    by_type: dict[str, list[dict]] = {}
    for a in new:
        for key, rx, _ in events:
            if rx.search(a.get("title") or ""):
                by_type.setdefault(key, []).append(a)
    rows = []
    for key, rx, ev in events:
        arts = by_type.get(key)
        if not arts:
            continue
        arts = sorted(arts, key=lambda a: a.get("seendate", ""), reverse=True)
        top = arts[0]
        when = parse_dt(top.get("seendate"))
        rows.append(signal(domain, f"news_{key}", str(len(arts)), pack=PACK, category="news", role="trigger",
                           weight=ev.get("weight", 0), play=ev.get("play", ""), source=top.get("domain", "gdelt"),
                           evidence=f"{top.get('title', '')[:180]} ({when.date() if when else ''}, {len(arts)} article(s))",
                           evidence_url=top.get("url", ""), tool_name=company))
    spike = len(new) >= cfg.get("volume_spike_articles", 20)
    rows.append(signal(domain, "news_volume", str(len(new)), pack=PACK, category="news",
                       role="trigger" if spike else "neutral", weight=cfg.get("volume_spike_weight", 10) if spike else 0,
                       play="timely_reference" if spike else "", source="gdelt",
                       evidence=f"{len(new)} new article(s), {len(kept)} matching in window", tool_name=company))
    summary = {"articles": len(kept), "new_articles": len(new),
               "events": "; ".join(f"{k} ({len(v)})" for k, v in sorted(by_type.items(), key=lambda kv: -len(kv[1]))),
               "top_headline": (sorted(new, key=lambda a: a.get("seendate", ""), reverse=True)[0].get("title", "")
                                if new else ""),
               "top_url": (sorted(new, key=lambda a: a.get("seendate", ""), reverse=True)[0].get("url", "")
                           if new else "")}
    return rows, summary, [a.get("url", "") for a in kept]
