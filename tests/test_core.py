import unittest

from radar.collectors import _parse_card_text, parse_compact_number
from radar.scoring import rank


class ParsingTests(unittest.TestCase):
    def test_compact_number(self):
        self.assertEqual(parse_compact_number("2.5K sold"), 2500)
        self.assertEqual(parse_compact_number("1.2M"), 1_200_000)

    def test_card_text(self):
        parsed = _parse_card_text("Useful Product\nRM19.90 RM29.90\n4.8 ★\n2.5K sold")
        self.assertEqual(parsed["price"], 19.90)
        self.assertEqual(parsed["original_price"], 29.90)
        self.assertEqual(parsed["sold"], 2500)
        self.assertEqual(parsed["rating"], 4.8)


class ScoringTests(unittest.TestCase):
    def test_cross_market_grouping(self):
        base = {"marketplace_id": "1", "query": "q", "price_myr": 20.0, "original_price_myr": 30.0, "sold": 1000, "rating": 4.8, "reviews": 100, "seller": "s", "url": "", "image": "", "weekly_sold_change": None, "weekly_review_change": None}
        items = [{**base, "marketplace": m, "title": "Wireless Earbuds Model X"} for m in ("tiktok", "lazada", "shopee")]
        result = rank(items, 20)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["marketplace_count"], 3)


if __name__ == "__main__":
    unittest.main()
