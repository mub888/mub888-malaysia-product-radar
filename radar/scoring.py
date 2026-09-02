from __future__ import annotations

import math
import re
from collections import defaultdict


STOP = {"official", "original", "ready", "stock", "malaysia", "free", "shipping", "new"}


def fingerprint(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", title.lower())
    useful = sorted({w for w in words if len(w) > 2 and w not in STOP})
    return " ".join(useful[:10]) or title.lower().strip()


def rank(items: list[dict], top_n: int) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        groups[fingerprint(item["title"])].append(item)
    sold_max = max((x["sold"] for x in items), default=1)
    reviews_max = max((x["reviews"] for x in items), default=1)
    output = []
    for fp, rows in groups.items():
        best = max(rows, key=lambda x: (x["sold"], x["rating"] or 0))
        prices = [x["price_myr"] for x in rows if x["price_myr"] and x["price_myr"] > 0]
        markets = sorted({x["marketplace"] for x in rows})
        sold_score = math.log1p(max(x["sold"] for x in rows)) / math.log1p(sold_max)
        review_score = math.log1p(max(x["reviews"] for x in rows)) / math.log1p(reviews_max)
        rating_score = max(((x["rating"] or 0) / 5 for x in rows), default=0)
        coverage_score = len(markets) / 3
        price_score = 1.0 if len(prices) > 1 else 0.5
        discounts = [(x["original_price_myr"] - x["price_myr"]) / x["original_price_myr"] for x in rows if x["original_price_myr"] and x["price_myr"] and x["original_price_myr"] > x["price_myr"]]
        discount_score = min(max(discounts, default=0), 0.6) / 0.6
        score = 100 * (.30*sold_score + .20*rating_score + .15*review_score + .15*coverage_score + .10*price_score + .10*discount_score)
        output.append({
            "product_key": fp,
            "representative_title": best["title"],
            "trend_score": round(score, 2),
            "marketplaces": ",".join(markets),
            "marketplace_count": len(markets),
            "min_price_myr": min(prices) if prices else None,
            "max_price_myr": max(prices) if prices else None,
            "price_spread_pct": round((max(prices)-min(prices))/min(prices)*100, 2) if len(prices) > 1 else None,
            "max_visible_sold": max(x["sold"] for x in rows),
            "best_rating": max((x["rating"] or 0 for x in rows), default=0),
            "total_reviews": sum(x["reviews"] for x in rows),
            "offers": rows,
        })
    return sorted(output, key=lambda x: x["trend_score"], reverse=True)[:top_n]

