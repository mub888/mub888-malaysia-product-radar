# Malaysia Cross-Market Product Radar

Weekly, evidence-preserving ranking of trend opportunities across TikTok Shop Malaysia, Lazada Malaysia, and Shopee Malaysia.

## What it does

- collects marketplace search/category snapshots through configurable adapters;
- normalizes MYR price, sold count, rating, review count, seller and URL;
- matches equivalent products across marketplaces;
- compares price and marketplace coverage;
- ranks the Top 20 using a transparent trend-opportunity score;
- writes CSV, JSON, Markdown and raw evidence files;
- runs every Monday at 09:00 Asia/Kuala_Lumpur (01:00 UTC) with GitHub Actions.

## Important data-access note

Official seller APIs normally expose authorized shop data, not a complete national bestseller feed. For market-wide discovery, configure a lawful data provider or your own permitted collection endpoint. `demo` mode is included so the entire normalization/ranking pipeline can be tested without pretending sample data is live.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
python -m radar
```

Outputs are written to `output/YYYY-MM-DD/`.

## Live provider contract

Set `RADAR_MODE=provider` and `PROVIDER_ENDPOINT`. The endpoint receives a POST request containing `marketplace`, `country`, `query`, and `limit`. It must return either an array or `{ "items": [...] }`. Supported aliases are documented in `radar/providers.py`.

This deliberately avoids hard-coding fragile private endpoints, bypass logic, CAPTCHA solving, or account-cookie extraction. Review each platform's terms and Malaysia privacy requirements before collection.

## Ranking

The score (0–100) combines:

- 30% log-scaled sold count
- 20% rating quality
- 15% review confidence
- 15% cross-market presence
- 10% price competitiveness
- 10% discount signal

It is an opportunity indicator, not verified revenue or profit. A weekly history database is used to add sales/review velocity once two or more snapshots exist.

## Configuration

Edit `config/queries.json` to choose categories or keywords. Broad Malaysia-wide coverage requires a carefully maintained query/category taxonomy; the starter list is intentionally manageable.

## GitHub Actions secrets

- `PROVIDER_ENDPOINT`
- `PROVIDER_TOKEN` (optional, but recommended)

Run the workflow manually once after secrets are configured. Inspect raw evidence and coverage warnings before relying on rankings.
