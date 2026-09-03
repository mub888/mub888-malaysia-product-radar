from __future__ import annotations

import csv
import json
import os
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from .providers import fetch, save_raw
from .scoring import rank
from .history import enrich_and_store


ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def run() -> None:
    _load_dotenv(ROOT / ".env")
    config = json.loads((ROOT / "config/queries.json").read_text(encoding="utf-8"))
    mode = os.getenv("RADAR_MODE", "demo").lower()
    limit = int(os.getenv("RESULTS_PER_QUERY", "50"))
    top_n = int(os.getenv("TOP_N", "20"))
    out = ROOT / "output" / date.today().isoformat()
    raw = out / "raw"
    all_items, failures = [], []
    if mode == "direct":
        from .collectors import collect_direct

        all_items, failures, runs = collect_direct(config, limit, out / "evidence")
        for collected in runs:
            save_raw(raw, collected["marketplace"], collected["query"], collected["items"], collected["meta"])
    else:
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
    deduplicated = {}
    for item in all_items:
        key = (item["marketplace"], item["marketplace_id"])
        current = deduplicated.get(key)
        if current is None or (item["sold"], item["reviews"]) > (current["sold"], current["reviews"]):
            deduplicated[key] = item
    all_items = enrich_and_store(list(deduplicated.values()), ROOT / "history" / "radar.sqlite3")
    ranked = rank(all_items, top_n)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "country": config["country"],
        "currency": config["currency"],
        "mode": mode,
        "source_records": len(all_items),
        "ranked": ranked,
        "failures": failures,
    }
    latest_json = out / "top20.json"
    latest_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    fields = ["rank", "representative_title", "trend_score", "marketplaces", "marketplace_count", "min_price_myr", "max_price_myr", "price_spread_pct", "max_visible_sold", "weekly_sold_change", "best_rating", "total_reviews", "weekly_review_change"]
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
        lines += ["", "> DEMO DATA — complete the Windows browser setup and use direct mode before making decisions."]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    docs_data = ROOT / "docs" / "data"
    docs_data.mkdir(parents=True, exist_ok=True)
    shutil.copy2(latest_json, docs_data / "latest.json")
    print(out)
