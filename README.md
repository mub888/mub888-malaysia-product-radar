# Malaysia Cross-Market Product Radar

A weekly, evidence-preserving Top 20 trend-opportunity comparison across TikTok Shop Malaysia, Lazada Malaysia, and Shopee Malaysia.

## No-provider edition

The default live mode uses your installed regular Google Chrome on your own Windows PC. It needs no paid scraping endpoint and no scraping API token. A self-hosted GitHub Actions runner schedules the job and receives a temporary repository-scoped `GITHUB_TOKEN` automatically for committing results.

The collector does **not** bypass CAPTCHAs, access controls, or private APIs. It collects product metadata visible in ordinary marketplace search pages and records a screenshot when a page requires manual attention.

## Outputs

- `output/YYYY-MM-DD/top20.csv` — spreadsheet-friendly ranking
- `output/YYYY-MM-DD/top20.json` — full ranking and source offers
- `output/YYYY-MM-DD/report.md` — human-readable weekly report
- `output/YYYY-MM-DD/raw/` — query-level normalized evidence
- `output/YYYY-MM-DD/evidence/` — screenshots and collection diagnostics
- `history/radar.sqlite3` — weekly observations used for velocity scoring
- `docs/` — static Product Radar dashboard for GitHub Pages

## Ranking model

After two successful snapshots, the score combines:

- 25% visible sold-count strength
- 20% weekly sold/review velocity
- 15% rating quality
- 10% review confidence
- 15% cross-market presence
- 5% price-comparison coverage
- 10% discount signal

The first snapshot automatically redistributes the velocity weight because no earlier observation exists. Visible sold counts are marketplace labels, not audited revenue.

## Windows installation

Requirements: Windows 11, Python 3.12+, Git, and Google Chrome.

Open PowerShell inside the cloned repository and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
```

The setup opens TikTok Shop, Lazada and Shopee directly in your installed Google Chrome using the dedicated `MarketWeb\chrome-profile` browser profile. Complete any normal login or Malaysia-region prompt, close that MarketWeb Chrome window, return to PowerShell, and press Enter. The project never reads or exports saved passwords/cookies, and `MarketWeb` is excluded from Git.

Run the first collection visibly:

```powershell
.\scripts\run_now.ps1
```

Review the screenshots, failure list, and Top 20 before enabling unattended runs.

## Self-hosted GitHub runner

In this repository, open **Settings → Actions → Runners → New self-hosted runner**, select Windows x64, and follow GitHub's generated commands. Configure the runner under the same Windows user that completed the browser setup so it can access the saved profile.

The included workflow runs every Monday at 09:00 Malaysia time (01:00 UTC). Your PC must be powered on, connected to the internet, and the runner must be active.

## Publish the dashboard

Open **Settings → Pages**, select **GitHub Actions** as the source, then run the “Publish Product Radar Website” workflow. GitHub Pages on a private repository requires an eligible GitHub plan; otherwise make only this repository public after confirming that no browser profile, cookies, or sensitive files were committed.

## Configuration

Edit `config/queries.json` to change keywords, marketplace coverage, or scroll depth. Start with a small taxonomy, inspect its quality, and expand gradually.

Environment settings:

| Variable | Default | Purpose |
|---|---|---|
| `RADAR_MODE` | `demo` | Set to `direct` for live browser collection |
| `RADAR_HEADLESS` | `true` | Use `false` for visible troubleshooting |
| `RADAR_BROWSER_PROFILE` | `MarketWeb/chrome-profile` | Override the dedicated Chrome profile location |
| `RADAR_BROWSER_EXECUTABLE` | Chrome channel detection | Optional full path to `chrome.exe` |
| `RADAR_PAGE_DELAY_MS` | `2500` | Minimum wait after page navigation |
| `RESULTS_PER_QUERY` | `50` | Maximum offers per marketplace/query |
| `TOP_N` | `20` | Ranked products to publish |

## Test without scraping

```powershell
python -m unittest discover -s tests -v
$env:RADAR_MODE = "demo"
python -m radar
```

Demo outputs are labelled and must never be interpreted as current Malaysia market data.

## Operational limitations

- Marketplace layout changes can require selector maintenance.
- Search results can be personalized by location, account state, advertising, and availability.
- A CAPTCHA or verification page is reported for manual handling, not bypassed.
- Running from GitHub-hosted datacenter IPs is less reliable; the workflow deliberately targets a self-hosted Windows runner.
- Collection must comply with applicable platform terms, Malaysian law, privacy requirements, and reasonable request rates.
