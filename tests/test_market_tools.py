import csv
import json
import tempfile
import unittest
from pathlib import Path
import sys
import re
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.market_data import DataError, audit_rows, load_csv
from scripts.chan_annotate import annotate
from scripts.learning_tracker import RUBRIC, recommend, record
from scripts.archive_catalog import parse_archive


def sample_rows():
    # Simple oscillating OHLC fixture; no real market prices.
    highs = [10, 12, 15, 13, 11, 9, 7, 9, 12, 14, 13, 11, 8]
    lows = [8, 9, 11, 10, 9, 7, 5, 6, 8, 10, 9, 7, 5]
    return [{"symbol": "TEST", "date": f"2020-01-{i+1:02}", "open": (h+l)/2, "high": h, "low": l, "close": (h+l)/2, "volume": 1000} for i, (h, l) in enumerate(zip(highs, lows))]


class MarketToolTests(unittest.TestCase):
    def test_clean_and_adjusted_history(self):
        rows = sample_rows()
        for row in rows:
            row["adj_factor"] = 1.0
            row["adj_open"] = row["open"]
            row["adj_high"] = row["high"]
            row["adj_low"] = row["low"]
            row["adj_close"] = row["close"]
        report = audit_rows(rows, source="synthetic-fixture", adjustment="backward", authorized=True)
        self.assertTrue(report["passed"])
        self.assertEqual(report["rows"], 13)

    def test_duplicate_date_rejected(self):
        rows = sample_rows()
        rows[1]["date"] = rows[0]["date"]
        result = audit_rows(rows, source="fixture", adjustment="raw", authorized=True)
        self.assertFalse(result["passed"])
        self.assertIn("duplicate_symbol_date", [issue["code"] for issue in result["issues"]])

    def test_bad_adjustment_rejected(self):
        rows = sample_rows()
        for row in rows:
            row["adj_factor"] = 1.0
            for field in ("open", "high", "low", "close"):
                row["adj_" + field] = row[field]
        rows[0]["adj_factor"] = 2.0
        result = audit_rows(rows, source="fixture", adjustment="forward", authorized=True)
        self.assertFalse(result["passed"])
        self.assertIn("adjustment_factor_close_ratio_mismatch", [issue["code"] for issue in result["issues"]])

    def test_adjusted_prices_without_factor_are_not_verified(self):
        rows = sample_rows()
        for row in rows:
            for field in ("open", "high", "low", "close"):
                row["adj_" + field] = row[field]
        result = audit_rows(rows, source="fixture", adjustment="forward", authorized=True)
        self.assertFalse(result["passed"])
        self.assertIn("adjustment_factor_required_by_adjustment_mode", [issue["code"] for issue in result["issues"]])

    def test_annotation_marks_confirmation_and_is_candidate_only(self):
        result = annotate(sample_rows(), source="synthetic-fixture", authorized=True, minimum_stroke_bars=2)
        self.assertEqual(result["status"], "candidate_only")
        self.assertTrue(all(f["confirmed_at"] > f["pivot_date"] for f in result["fractals"]))
        self.assertTrue(all("confirmed_at" in s for s in result["strokes"]))

    def test_annotation_rejects_multiple_symbols(self):
        rows = sample_rows()
        extra = dict(rows[0], symbol="OTHER")
        with self.assertRaises(DataError):
            annotate(rows + [extra], source="fixture", authorized=True)

    def test_learner_recommendation_and_local_record(self):
        scores = dict(zip(RUBRIC, [2, 3, 2, 4]))
        self.assertEqual(recommend([{"scores": scores}])["status"], "practice_needed")
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temp:
            path = Path(temp) / "progress.jsonl"
            record(path, "anon-1", "lesson-1", scores)
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)

    def test_archive_catalog_metadata_parser(self):
        html = '<a href="https://chzhshch.org/2006/06/07/0187-course-1/">教你炒股票1：走势分析</a><a href="/category/test/">分类</a>'
        posts = parse_archive(html)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["title"], "教你炒股票1：走势分析")
        self.assertEqual(posts[0]["course_number"], "001")

    def test_full_archive_and_108_course_index_integrity(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "knowledge-base/archive-catalog-full.csv").open(encoding="utf-8-sig", newline="") as f:
            archive = list(csv.DictReader(f))
        with (root / "knowledge-base/chan108-course-index.csv").open(encoding="utf-8-sig", newline="") as f:
            courses = list(csv.DictReader(f))
        self.assertEqual(len(archive), 1139)
        self.assertEqual([int(r["course_number"]) for r in courses], list(range(1, 109)))
        self.assertEqual(courses[82]["title"], "笔-线段与线段-最小中枢结构的不同心理意义1")

    def test_local_markdown_links_and_provider_example(self):
        root = Path(__file__).resolve().parents[1]
        broken = []
        for md in root.rglob("*.md"):
            content = md.read_text(encoding="utf-8")
            for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", content):
                target = match.group(1).split("#", 1)[0]
                if not target or urlparse(target).scheme in {"http", "https", "mailto"}:
                    continue
                if not (md.parent / unquote(target)).exists():
                    broken.append(f"{md.relative_to(root)} -> {target}")
        self.assertEqual(broken, [])
        json.loads((root / "providers.example.json").read_text(encoding="utf-8"))

    def test_csv_roundtrip(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temp:
            path = Path(temp) / "data.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=sample_rows()[0].keys())
                writer.writeheader()
                writer.writerows(sample_rows())
            self.assertEqual(len(load_csv(path)), 13)


if __name__ == "__main__":
    unittest.main()
