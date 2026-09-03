from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, quote_plus, urljoin

from .providers import normalize


MARKETS = {
    "shopee": {
        "home": "https://shopee.com.my/",
        "search": "https://shopee.com.my/search?keyword={query}",
        "cards": [
            "li.shopee-search-item-result__item",
            "div.shopee-search-item-result__item",
            "[data-sqe='item']",
            "a[href*='-i.']",
        ],
    },
    "lazada": {
        "home": "https://www.lazada.com.my/",
        "search": "https://www.lazada.com.my/catalog/?q={query}",
        "cards": [
            "[data-qa-locator='product-item']",
            "[data-tracking='product-card']",
            "div.Bm3ON",
            "a[href*='/products/']",
        ],
    },
    "tiktok": {
        "home": "https://shop.tiktok.com/",
        "search": "https://shop.tiktok.com/view/search?q={query}&region=MY",
        "cards": [
            "[data-e2e*='product-card']",
            "[data-testid*='product-card']",
            "a[href*='/view/product/']",
            "a[href*='/product/']",
        ],
    },
}

CHALLENGE_MARKERS = (
    "verify you are human",
    "security verification",
    "unusual traffic",
    "captcha",
    "access denied",
    "log in to continue",
)


def default_profile_dir() -> Path:
    configured = os.getenv("RADAR_BROWSER_PROFILE", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[1] / "MarketWeb" / "chrome-profile"


def _encode_query(marketplace: str, query: str) -> str:
    if marketplace == "shopee":
        return quote(query, safe="")
    return quote_plus(query)


def _launch_persistent_context(playwright: Any, profile: Path, headless: bool) -> Any:
    """Use installed Google Chrome; never read or export browser passwords/cookies."""
    explicit_executable = os.getenv("RADAR_BROWSER_EXECUTABLE", "").strip()
    options: dict[str, Any] = {
        "headless": headless,
        "locale": "en-MY",
        "timezone_id": "Asia/Kuala_Lumpur",
        "viewport": {"width": 1440, "height": 1100},
    }
    if explicit_executable:
        candidate = Path(explicit_executable)
        if not candidate.is_file():
            raise RuntimeError(f"RADAR_BROWSER_EXECUTABLE was not found: {candidate}")
        options["executable_path"] = str(candidate)
    else:
        # Playwright's Chrome channel targets the user's installed Google Chrome,
        # not the downloaded Chromium-for-Testing binary.
        options["channel"] = "chrome"
    try:
        return playwright.chromium.launch_persistent_context(str(profile), **options)
    except Exception as exc:
        raise RuntimeError(
            "Could not start regular Google Chrome. Install Google Chrome or set "
            "RADAR_BROWSER_EXECUTABLE to the full path of chrome.exe."
        ) from exc


def parse_compact_number(value: str | None) -> int:
    if not value:
        return 0
    match = re.search(r"([\d,.]+)\s*([kKmM]?)", value)
    if not match:
        return 0
    number = float(match.group(1).replace(",", ""))
    multiplier = {"k": 1_000, "m": 1_000_000}.get(match.group(2).lower(), 1)
    return int(number * multiplier)


def _parse_card_text(text: str) -> dict[str, Any]:
    prices = [float(x.replace(",", "")) for x in re.findall(r"RM\s*([\d,]+(?:\.\d{1,2})?)", text, re.I)]
    sold_match = re.search(r"([\d,.]+\s*[kKmM]?)\s*(?:sold|terjual)", text, re.I)
    reviews_match = re.search(r"\(([\d,.]+\s*[kKmM]?)\)", text)
    rating_match = re.search(r"([0-5](?:\.\d)?)\s*(?:/\s*5|out of 5|rating|★)", text, re.I)
    discount_match = re.search(r"(\d{1,2})%\s*(?:off)?", text, re.I)
    return {
        "price": prices[0] if prices else None,
        "original_price": max(prices) if len(prices) > 1 and max(prices) > prices[0] else None,
        "sold": parse_compact_number(sold_match.group(1)) if sold_match else 0,
        "reviews": parse_compact_number(reviews_match.group(1)) if reviews_match else 0,
        "rating": float(rating_match.group(1)) if rating_match else None,
        "discount_pct": int(discount_match.group(1)) if discount_match else None,
    }


def _first_attr(card: Any, selectors: list[str], attribute: str) -> str:
    for selector in selectors:
        try:
            node = card.locator(selector).first
            if node.count():
                value = node.get_attribute(attribute, timeout=1_000)
                if value:
                    return value.strip()
        except Exception:
            continue
    return ""


def _title(card: Any, text: str) -> str:
    title = _first_attr(card, ["[title]", "a[title]", "img[alt]"], "title")
    if not title:
        title = _first_attr(card, ["img[alt]"], "alt")
    if title:
        return title
    ignored = re.compile(r"^(RM\s*|\d+(?:\.\d+)?(?:k|m)?\s*(?:sold|terjual)|\d+%|free shipping)", re.I)
    lines = [x.strip() for x in text.splitlines() if len(x.strip()) >= 8 and not ignored.search(x.strip())]
    return max(lines, key=len, default="Untitled product")[:300]


def _extract_cards(page: Any, marketplace: str, query: str, limit: int) -> tuple[list[dict[str, Any]], str]:
    selected = ""
    locator = None
    for selector in MARKETS[marketplace]["cards"]:
        candidate = page.locator(selector)
        try:
            if candidate.count() >= 2:
                selected, locator = selector, candidate
                break
        except Exception:
            continue
    if locator is None:
        return [], selected
    items: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for index in range(min(locator.count(), limit)):
        card = locator.nth(index)
        try:
            text = card.inner_text(timeout=2_000).strip()
            href = card.get_attribute("href") or _first_attr(card, ["a[href]"], "href")
            href = urljoin(page.url, href) if href else ""
            if href and href in seen_urls:
                continue
            parsed = _parse_card_text(text)
            title = _title(card, text)
            if title == "Untitled product" or parsed["price"] is None:
                continue
            image = _first_attr(card, ["img"], "src") or _first_attr(card, ["img"], "data-src")
            raw = {
                "title": title,
                "price": parsed["price"],
                "original_price": parsed["original_price"],
                "sold": parsed["sold"],
                "reviews": parsed["reviews"],
                "rating": parsed["rating"],
                "url": href,
                "image": image,
            }
            items.append(normalize(raw, marketplace, query))
            if href:
                seen_urls.add(href)
        except Exception:
            continue
    return items, selected


def _extract_json_ld(page: Any, marketplace: str, query: str, limit: int) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if len(found) >= limit:
            return
        if isinstance(value, list):
            for child in value:
                walk(child)
            return
        if not isinstance(value, dict):
            return
        entity = value.get("item") if isinstance(value.get("item"), dict) else value
        entity_type = entity.get("@type")
        types = entity_type if isinstance(entity_type, list) else [entity_type]
        offers = entity.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            offers = {}
        if "Product" in types and entity.get("name") and (offers.get("price") or offers.get("lowPrice")):
            aggregate = entity.get("aggregateRating") if isinstance(entity.get("aggregateRating"), dict) else {}
            found.append(normalize({
                "id": entity.get("sku") or entity.get("productID"),
                "title": entity.get("name"),
                "price": offers.get("price") or offers.get("lowPrice"),
                "rating": aggregate.get("ratingValue"),
                "reviews": aggregate.get("reviewCount") or aggregate.get("ratingCount"),
                "url": entity.get("url"),
                "image": entity.get("image", [""])[0] if isinstance(entity.get("image"), list) else entity.get("image"),
            }, marketplace, query))
        for child in value.values():
            if child is not entity:
                walk(child)

    scripts = page.locator("script[type='application/ld+json']")
    for index in range(min(scripts.count(), 30)):
        try:
            walk(json.loads(scripts.nth(index).text_content(timeout=1_000) or "null"))
        except Exception:
            continue
    return found[:limit]


def collect_direct(config: dict[str, Any], limit: int, evidence_dir: Path) -> tuple[list[dict], list[dict], list[dict]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Install Playwright with: pip install -r requirements.txt") from exc

    headless = os.getenv("RADAR_HEADLESS", "true").lower() not in {"0", "false", "no"}
    delay_ms = max(1_500, int(os.getenv("RADAR_PAGE_DELAY_MS", "2500")))
    max_scrolls = int(config.get("max_scrolls", 6))
    profile = default_profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    all_items: list[dict] = []
    failures: list[dict] = []
    runs: list[dict] = []

    with sync_playwright() as playwright:
        context = _launch_persistent_context(playwright, profile, headless)
        page = context.pages[0] if context.pages else context.new_page()
        for marketplace in config["marketplaces"]:
            if marketplace not in MARKETS:
                failures.append({"marketplace": marketplace, "query": "*", "error": "Unsupported marketplace"})
                continue
            for query in config["queries"]:
                started = datetime.now(timezone.utc).isoformat()
                slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:50]
                screenshot = evidence_dir / f"{marketplace}-{slug}.png"
                url = MARKETS[marketplace]["search"].format(query=_encode_query(marketplace, query))
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=75_000)
                    page.wait_for_timeout(delay_ms)
                    body_text = page.locator("body").inner_text(timeout=10_000).lower()
                    marker = next((x for x in CHALLENGE_MARKERS if x in body_text), None)
                    if marker:
                        page.screenshot(path=str(screenshot), full_page=False)
                        raise RuntimeError(f"Manual browser verification required: {marker}")
                    for _ in range(max_scrolls):
                        page.mouse.wheel(0, 1_600)
                        page.wait_for_timeout(650)
                    items, selector = _extract_cards(page, marketplace, query, limit)
                    if not items:
                        items = _extract_json_ld(page, marketplace, query, limit)
                        selector = "application/ld+json" if items else selector
                    page.screenshot(path=str(screenshot), full_page=False)
                    if not items:
                        raise RuntimeError("No product cards found; page layout, region, or login may require attention")
                    meta = {"mode": "direct", "url": page.url, "selector": selector, "count": len(items), "started_at": started, "screenshot": screenshot.name}
                    all_items.extend(items)
                    runs.append({"marketplace": marketplace, "query": query, "items": items, "meta": meta})
                except Exception as exc:
                    try:
                        page.screenshot(path=str(screenshot), full_page=False)
                    except Exception:
                        pass
                    failure = {"marketplace": marketplace, "query": query, "url": url, "error": str(exc), "screenshot": screenshot.name}
                    failures.append(failure)
                    runs.append({"marketplace": marketplace, "query": query, "items": [], "meta": {"mode": "direct", **failure}})
                time.sleep(1.0)
        context.close()
    (evidence_dir / "collection-summary.json").write_text(json.dumps({"failures": failures, "runs": [{"marketplace": r["marketplace"], "query": r["query"], "meta": r["meta"]} for r in runs]}, indent=2), encoding="utf-8")
    return all_items, failures, runs


def open_login_session() -> None:
    from playwright.sync_api import sync_playwright

    profile = default_profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context = _launch_persistent_context(playwright, profile, headless=False)
        pages = context.pages
        for index, market in enumerate(MARKETS.values()):
            page = pages[0] if index == 0 and pages else context.new_page()
            page.goto(market["home"], wait_until="domcontentloaded", timeout=75_000)
        input("Complete any normal login or region prompts in the browser, then press Enter here to save the session...")
        context.close()
