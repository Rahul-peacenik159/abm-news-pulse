import csv
import json
from pathlib import Path

from news_pulse import cli, pulse
from news_pulse.common import load_yaml

ROOT = Path(__file__).resolve().parent.parent
CFG = load_yaml(ROOT / "config" / "events.yaml")
ARTS = json.loads((ROOT / "tests" / "fixtures" / "gdelt_artlist.json").read_text())["articles"]


def test_build_query():
    assert pulse.build_query({"company": "Acme Corp"}, CFG) == "Acme sourcelang:english"
    assert pulse.build_query({"company": "Marriott International Inc."}, CFG) == '"Marriott International" sourcelang:english'
    assert pulse.build_query({"company": "X", "news_query": '"Harbor AI"'}, {"source_language": ""}) == '"Harbor AI"'


def test_classify_events_dedupe_and_name_filter():
    rows, summary, keys = pulse.classify("acme.com", "Acme Corp", ARTS, CFG, None, True)
    types = {r["signal_type"]: r for r in rows}
    assert {"news_funding", "news_leadership", "news_acquisition"} <= set(types)
    assert types["news_funding"]["signal_value"] == "1"           # syndicated copy removed
    assert types["news_acquisition"]["play"] == "post_merger_integration"
    assert summary["articles"] == 3                               # roundup without the name dropped
    assert summary["top_headline"].startswith("Acme names new CFO")
    assert len(keys) == 3


def test_second_run_reports_only_new_articles():
    _, _, keys = pulse.classify("acme.com", "Acme", ARTS, CFG, None, True)
    rows, summary, _ = pulse.classify("acme.com", "Acme", ARTS, CFG, set(keys), True)
    assert summary["new_articles"] == 0 and [r["signal_type"] for r in rows] == ["news_volume"]


def test_cli(monkeypatch, tmp_path):
    monkeypatch.setattr(pulse, "client", lambda: None)
    calls = []

    def fake_fetch(http, query, timespan, n):
        calls.append(query)
        if "Broken" in query:
            raise RuntimeError("GDELT: Please limit requests to one every 5 seconds")
        return ARTS

    monkeypatch.setattr(pulse, "fetch_articles", fake_fetch)
    acc = tmp_path / "a.csv"
    acc.write_text("domain,company\nacme.com,Acme Corp\nbroken.com,Broken Inc\n")
    cli.main(["run", "--accounts", str(acc), "--out", str(tmp_path / "out")])
    rows = {r["account_domain"]: r for r in csv.DictReader(open(tmp_path / "out" / "accounts_summary.csv"))}
    assert int(rows["acme.com"]["score"]) >= 65 and rows["acme.com"]["top_play"] == "post_merger_integration"
    assert "limit requests" in rows["broken.com"]["errors"]
    assert calls[0] == "Acme sourcelang:english"
