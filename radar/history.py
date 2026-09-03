from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
  run_date TEXT NOT NULL,
  marketplace TEXT NOT NULL,
  marketplace_id TEXT NOT NULL,
  title TEXT NOT NULL,
  sold INTEGER NOT NULL,
  reviews INTEGER NOT NULL,
  price_myr REAL,
  rating REAL,
  PRIMARY KEY (run_date, marketplace, marketplace_id)
);
CREATE INDEX IF NOT EXISTS idx_observation_lookup
ON observations(marketplace, marketplace_id, run_date);
"""


def enrich_and_store(items: list[dict], database: Path) -> list[dict]:
    database.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA)
        for item in items:
            previous = connection.execute(
                """SELECT sold, reviews, price_myr, run_date FROM observations
                   WHERE marketplace=? AND marketplace_id=? AND run_date < ?
                   ORDER BY run_date DESC LIMIT 1""",
                (item["marketplace"], item["marketplace_id"], today),
            ).fetchone()
            item["previous_date"] = previous[3] if previous else None
            item["weekly_sold_change"] = max(0, item["sold"] - previous[0]) if previous else None
            item["weekly_review_change"] = max(0, item["reviews"] - previous[1]) if previous else None
            item["weekly_price_change_pct"] = (
                round((item["price_myr"] - previous[2]) / previous[2] * 100, 2)
                if previous and item["price_myr"] is not None and previous[2]
                else None
            )
            connection.execute(
                """INSERT OR REPLACE INTO observations
                   (run_date, marketplace, marketplace_id, title, sold, reviews, price_myr, rating)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (today, item["marketplace"], item["marketplace_id"], item["title"], item["sold"], item["reviews"], item["price_myr"], item["rating"]),
            )
        connection.commit()
    return items

