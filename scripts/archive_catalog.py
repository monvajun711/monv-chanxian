#!/usr/bin/env python3
"""Create a metadata-only catalog of posts listed on the public archive page.

The script stores titles, URLs, archive indices and access dates, not article
bodies. It does not bypass access controls or reuse copyrighted full text.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import html
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

ARCHIVE_URL = "https://chzhshch.org/archive/"
ALLOWED_HOSTS = {"chzhshch.org", "www.chzhshch.org"}


class ArchiveParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.entries = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            attr = dict(attrs)
            if attr.get("href"):
                self.current = {"href": attr["href"], "text": []}

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"].append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current is not None:
            title = " ".join("".join(self.current["text"]).split())
            self.entries.append((self.current["href"], html.unescape(title)))
            self.current = None


def parse_archive(markup: str, base_url: str = ARCHIVE_URL) -> list[dict[str, str]]:
    parser = ArchiveParser()
    parser.feed(markup)
    seen, posts = set(), []
    for href, title in parser.entries:
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or not title:
            continue
        # The source page also has two navigation links. Canonical posts use
        # year/month/day permalinks; keep only those rather than silently
        # inflating the site's 1,139-post count.
        if not re.search(r"/\d{4}/\d{2}/\d{2}/", parsed.path):
            continue
        if full in seen:
            continue
        seen.add(full)
        decoded_path = unquote(parsed.path)
        match = re.search(r"教你炒股票\s*0*(\d{1,3})", title + " " + decoded_path)
        post_date = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", parsed.path)
        posts.append({"archive_index": str(len(posts) + 1), "title": title, "url": full,
                      "course_number": match.group(1).zfill(3) if match else "",
                      "permalink_date": "-".join(post_date.groups()) if post_date else ""})
    return posts


def normalize_existing_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    markup = "".join(f'<a href="{html.escape(row.get("url", ""), quote=True)}">{html.escape(row.get("title", ""))}</a>' for row in rows)
    return parse_archive(markup)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "mowna-thread-catalog/0.6 (metadata indexing; contact via source site)", "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"archive returned HTTP {response.status}")
        data = response.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise RuntimeError("archive page exceeds 20 MiB limit")
    return data.decode("utf-8", errors="replace")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--expected-count", type=int, default=1139, help="Current count displayed on archive; override only after recording the source snapshot")
    p.add_argument("--allow-count-change", action="store_true", help="Write the observed catalog even if the site count has changed")
    p.add_argument("--html", type=Path, help="Use a previously saved archive HTML snapshot instead of making a network request")
    p.add_argument("--input-csv", type=Path, help="Normalize a previously captured metadata CSV")
    p.add_argument("--course-out", type=Path, help="Optional separate index of course-numbered posts")
    a = p.parse_args()
    try:
        if a.html and a.input_csv:
            p.error("use only one of --html or --input-csv")
        if a.input_csv:
            posts = normalize_existing_csv(a.input_csv)
        else:
            source_html = a.html.read_text(encoding="utf-8") if a.html else fetch(ARCHIVE_URL)
            posts = parse_archive(source_html)
        if not posts:
            raise RuntimeError("no archive post links found; inspect source layout before accepting catalog")
        if a.expected_count and len(posts) != a.expected_count and not a.allow_count_change:
            raise RuntimeError(f"catalog contains {len(posts)} posts; archive currently expected {a.expected_count}. Recheck parser and archive count; use --allow-count-change only after review")
        a.out.parent.mkdir(parents=True, exist_ok=True)
        fields = ["archive_index", "title", "url", "permalink_date", "course_number", "content_type", "digest_status", "rights_status", "accessed_on"]
        with a.out.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for post in posts:
                is_course = "教你炒股票" in post["title"]
                w.writerow({**post, "content_type": "original_blog_post", "digest_status": "metadata_only", "rights_status": "link_only_no_body_republished", "accessed_on": dt.date.today().isoformat()})
        if a.course_out:
            courses = [x for x in posts if x["course_number"]]
            numbers = [int(x["course_number"]) for x in courses]
            if len(courses) != 108 or sorted(numbers) != list(range(1, 109)):
                raise RuntimeError(f"108-course index check failed: rows={len(courses)}, unique={len(set(numbers))}; inspect omissions/duplicates before accepting")
            a.course_out.parent.mkdir(parents=True, exist_ok=True)
            with a.course_out.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["course_number", "title", "original_url", "permalink_date", "digest_status"])
                w.writeheader()
                for post in sorted(courses, key=lambda x: int(x["course_number"])):
                    w.writerow({"course_number": post["course_number"], "title": post["title"], "original_url": post["url"], "permalink_date": post["permalink_date"], "digest_status": "metadata_only_not_distilled"})
        course_count = len({x["course_number"] for x in posts if x["course_number"]})
        print(f"catalog_rows={len(posts)} course_numbers={course_count} file={a.out}")
        return 0
    except (OSError, UnicodeError, RuntimeError, urllib.error.URLError) as exc:
        print(f"archive catalog failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
