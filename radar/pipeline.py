from __future__ import annotations

import csv
import json
import os
from datetime import date
from pathlib import Path

from .providers import fetch, save_raw
from .scoring import rank


ROOT = Path(__file__).resolve().parents[1]


def run() -> None:
    config = json.loads((ROOT / "config/queries.json").read_text(encoding="utf-8"))
    mode = os.getenv("RADAR_MODE", "demo").lower()
    limit = int(os.getenv("RESULTS_PER_QUERY", "50"))
    top_n = int(os.getenv("TOP_N", "20"))
    out = ROOT / "output" / date.today().isoformat()
    raw = out / "raw"
    all_items, failures = [], []
    for marketplace in config["marketplaces"]:
        for query in config["queries"]:
            try:
                items, meta = fetch(marketplace, query, limit, mode)
                save_raw(raw, marketplace, query, items, meta)
                all_items.extend(items)
            except Exception as exc:
                failures.append({"marketplace": marketplace, "query": query, "error": str(exc)})
    if not all_items:
        raise RuntimeError(f"No records collected. Failures: {failures}")
    ranked = rank(all_items, top_n)
    out.mkdir(parents=True, exist_ok=True)
    (out / "top20.json").write_text(json.dumps({"mode": mode, "ranked": ranked, "failures": failures}, indent=2), encoding="utf-8")
    fields = ["rank", "representative_title", "trend_score", "marketplaces", "marketplace_count", "min_price_myr", "max_price_myr", "price_spread_pct", "max_visible_sold", "best_rating", "total_reviews"]
    with (out / "top20.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for i, row in enumerate(ranked, 1):
            writer.writerow({"rank": i, **{k: row.get(k) for k in fields if k != "rank"}})
    lines = [f"# Malaysia Product Radar — {date.today().isoformat()}", "", f"Mode: **{mode}**", "", "| # | Product | Score | Markets | Price (MYR) | Visible sold |", "|---:|---|---:|---|---:|---:|"]
    for i, row in enumerate(ranked, 1):
        lines.append(f"| {i} | {row['representative_title']} | {row['trend_score']} | {row['marketplaces']} | {row['min_price_myr']}–{row['max_price_myr']} | {row['max_visible_sold']} |")
    if failures:
        lines += ["", f"Coverage warnings: {len(failures)} collection failures. See top20.json."]
    if mode == "demo":
        lines += ["", "> DEMO DATA — configure a live provider before using this report for decisions."]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)
