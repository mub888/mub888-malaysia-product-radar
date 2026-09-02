from __future__ import annotations

import hashlib
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from urllib.request import Request, urlopen


ALIASES = {
    "id": ("id", "item_id", "product_id"),
    "title": ("title", "name", "product_name"),
    "price": ("price", "sale_price", "current_price"),
    "original_price": ("original_price", "list_price", "before_discount_price"),
    "sold": ("sold", "sold_count", "item_sold_count", "historical_sold"),
    "rating": ("rating", "rating_star", "shop_rating"),
    "reviews": ("reviews", "review_count", "rating_count"),
    "seller": ("seller", "seller_name", "shop_name"),
    "url": ("url", "product_url", "item_url"),
    "image": ("image", "image_url", "thumbnail"),
}


def _pick(item: dict[str, Any], name: str, default: Any = None) -> Any:
    for key in ALIASES[name]:
        if item.get(key) not in (None, ""):
            return item[key]
    return default


def normalize(item: dict[str, Any], marketplace: str, query: str) -> dict[str, Any]:
    title = str(_pick(item, "title", "Untitled")).strip()
    raw_id = str(_pick(item, "id", ""))
    stable_id = raw_id or hashlib.sha256(f"{marketplace}|{title}|{_pick(item, 'seller', '')}".encode()).hexdigest()[:20]
    return {
        "marketplace": marketplace,
        "marketplace_id": stable_id,
        "query": query,
        "title": title,
        "price_myr": _number(_pick(item, "price")),
        "original_price_myr": _number(_pick(item, "original_price")),
        "sold": int(_number(_pick(item, "sold")) or 0),
        "rating": _number(_pick(item, "rating")),
        "reviews": int(_number(_pick(item, "reviews")) or 0),
        "seller": str(_pick(item, "seller", "")),
        "url": str(_pick(item, "url", "")),
        "image": str(_pick(item, "image", "")),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def _number(value: Any) -> float | None:
    if value is None:
        return None
    cleaned = "".join(c for c in str(value).replace(",", "") if c.isdigit() or c in ".-")
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def fetch(marketplace: str, query: str, limit: int, mode: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if mode == "demo":
        return _demo(marketplace, query, limit), {"mode": "demo"}
    endpoint = os.environ.get("PROVIDER_ENDPOINT", "").strip()
    if not endpoint:
        raise RuntimeError("PROVIDER_ENDPOINT is required when RADAR_MODE=provider")
    headers = {"Accept": "application/json", "User-Agent": "MalaysiaProductRadar/0.1"}
    if token := os.environ.get("PROVIDER_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    payload = {"marketplace": marketplace, "country": "MY", "query": query, "limit": limit}
    headers["Content-Type"] = "application/json"
    request = Request(endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urlopen(request, timeout=90) as response:
        status = response.status
        body = json.loads(response.read().decode("utf-8"))
    items = body.get("items", []) if isinstance(body, dict) else body
    if not isinstance(items, list):
        raise ValueError("Provider response must be an array or an object containing items[]")
    return [normalize(x, marketplace, query) for x in items], {"mode": "provider", "status": status}


def _demo(marketplace: str, query: str, limit: int) -> list[dict[str, Any]]:
    rng = random.Random(f"{marketplace}|{query}")
    products = []
    for i in range(min(limit, 8)):
        base = 18 + i * 7 + rng.random() * 15
        title = f"{query.title()} Model {i + 1}"
        products.append(normalize({
            "id": f"demo-{marketplace}-{hashlib.md5(title.encode()).hexdigest()[:8]}",
            "title": title,
            "price": round(base * (0.9 + rng.random() * 0.2), 2),
            "original_price": round(base * 1.25, 2),
            "sold": rng.randint(30, 18000),
            "rating": round(rng.uniform(4.0, 5.0), 1),
            "reviews": rng.randint(5, 4000),
            "seller": f"Demo {marketplace.title()} Seller",
            "url": "",
        }, marketplace, query))
    return products


def save_raw(path: Path, marketplace: str, query: str, items: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    slug = hashlib.sha1(query.encode()).hexdigest()[:10]
    (path / f"{marketplace}-{slug}.json").write_text(json.dumps({"query": query, "meta": meta, "items": items}, indent=2), encoding="utf-8")
