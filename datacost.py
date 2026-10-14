#!/usr/bin/env python3
"""
datacost - how much mobile data (and how many shillings) does one visit
to a web page really cost?

Usage:
    python datacost.py https://example.com
    python datacost.py https://site1.com https://site2.com https://site3.com
    python datacost.py https://example.com --bundle-mb 1000 --bundle-ugx 5000

Give it ONE link for a detailed breakdown, or SEVERAL links to get a
ranked table (most expensive first).

No extra libraries needed - only Python's standard library.
"""

import argparse
import gzip
import zlib
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen

# Change these to match YOUR bundle (the defaults are just an example).
DEFAULT_BUNDLE_MB = 1000   # size of the bundle in MB (1000 MB ~ 1 GB)
DEFAULT_BUNDLE_UGX = 5000  # price of that bundle in UGX

MAX_RESOURCES = 80         # safety limit so the script never runs forever
TIMEOUT = 30               # seconds to wait per request (slow sites need time)

# Some sites refuse anything that doesn't look like a normal web browser,
# so we introduce ourselves the way a browser does.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}


class ResourceFinder(HTMLParser):
    """Collects the files a page loads: images, scripts, stylesheets, media."""

    def __init__(self):
        super().__init__()
        self.found = []  # list of (kind, url)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "img" and a.get("src"):
            self.found.append(("image", a["src"]))
        elif tag == "script" and a.get("src"):
            self.found.append(("script", a["src"]))
        elif tag == "link" and a.get("href"):
            rel = (a.get("rel") or "").lower()
            if "stylesheet" in rel:
                self.found.append(("style", a["href"]))
        elif tag in ("video", "audio", "source") and a.get("src"):
            self.found.append(("media", a["src"]))


def fetch(url):
    """Download a URL. Returns (bytes_transferred, decoded_body)."""
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        encoding = (resp.headers.get("Content-Encoding") or "").lower()
    body = raw
    try:
        if encoding == "gzip":
            body = gzip.decompress(raw)
        elif encoding == "deflate":
            body = zlib.decompress(raw)
    except Exception:
        body = raw
    return len(raw), body


def human(nbytes):
    if nbytes >= 1024 * 1024:
        return f"{nbytes / (1024 * 1024):.2f} MB"
    return f"{nbytes / 1024:.1f} KB"


def clean_url(url):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def analyze(url):
    """Download a page and its linked files. Returns a dict of results.

    Raises URLError/HTTPError if the page itself cannot be opened.
    """
    html_size, html_body = fetch(url)

    finder = ResourceFinder()
    finder.feed(html_body.decode("utf-8", errors="ignore"))

    # Remove duplicates but keep order
    seen, resources = set(), []
    for kind, link in finder.found:
        full = urljoin(url, link)
        if full.startswith(("http://", "https://")) and full not in seen:
            seen.add(full)
            resources.append((kind, full))

    totals = {"page (html)": html_size}
    failed = 0
    results = []

    for kind, full in resources[:MAX_RESOURCES]:
        try:
            size, _ = fetch(full)
            totals[kind] = totals.get(kind, 0) + size
            results.append((size, kind, full))
        except Exception:
            failed += 1

    return {
        "url": url,
        "totals": totals,
        "total_bytes": sum(totals.values()),
        "results": results,
        "failed": failed,
    }


def show_detail(info, bundle_mb, bundle_ugx):
    """Detailed breakdown for a single page."""
    total_bytes = info["total_bytes"]
    total_mb = total_bytes / (1024 * 1024)
    cost_per_mb = bundle_ugx / bundle_mb
    cost_one_visit = total_mb * cost_per_mb

    print("What this page downloads")
    print("-" * 40)
    for kind, size in sorted(info["totals"].items(), key=lambda x: -x[1]):
        print(f"  {kind:<14}{human(size):>12}")
    print("-" * 40)
    print(f"  {'TOTAL':<14}{human(total_bytes):>12}\n")

    if info["results"]:
        print("Heaviest files")
        for size, kind, full in sorted(info["results"], reverse=True)[:3]:
            short = full if len(full) <= 60 else full[:57] + "..."
            print(f"  {human(size):>10}  {short}")
        print()

    print(f"Your bundle: {bundle_mb:g} MB for {bundle_ugx:,.0f} UGX "
          f"({cost_per_mb:.2f} UGX per MB)\n")
    print(f"  One visit costs about   {cost_one_visit:,.1f} UGX")
    print(f"  10 visits a day, a month ({10 * 30} visits): "
          f"{cost_one_visit * 300:,.0f} UGX")
    if total_mb > 0:
        print(f"  One bundle gives you only {bundle_mb / total_mb:,.0f} visits")
    if info["failed"]:
        print(f"\n({info['failed']} file(s) could not be downloaded and were skipped.)")


def show_ranking(infos, bundle_mb, bundle_ugx):
    """Ranked table for several pages, most expensive first."""
    cost_per_mb = bundle_ugx / bundle_mb
    rows = sorted(infos, key=lambda i: -i["total_bytes"])

    print("Ranked: most expensive page first")
    print("-" * 70)
    print(f"  {'#':<3}{'Page':<38}{'Size':>10}{'Cost/visit':>13}")
    print("-" * 70)
    for n, info in enumerate(rows, start=1):
        name = info["url"].replace("https://", "").replace("http://", "")
        name = name if len(name) <= 36 else name[:33] + "..."
        mb = info["total_bytes"] / (1024 * 1024)
        print(f"  {n:<3}{name:<38}{human(info['total_bytes']):>10}"
              f"{mb * cost_per_mb:>9,.1f} UGX")
    print("-" * 70)

    if len(rows) > 1 and rows[-1]["total_bytes"] > 0:
        ratio = rows[0]["total_bytes"] / rows[-1]["total_bytes"]
        print(f"\nThe heaviest page costs {ratio:,.1f}x more than the lightest.")
    print(f"Your bundle: {bundle_mb:g} MB for {bundle_ugx:,.0f} UGX "
          f"({cost_per_mb:.2f} UGX per MB)")


def main():
    parser = argparse.ArgumentParser(description="What does one visit to a page cost in UGX?")
    parser.add_argument("urls", nargs="+",
                        help="one or more page addresses, e.g. https://example.com")
    parser.add_argument("--bundle-mb", type=float, default=DEFAULT_BUNDLE_MB,
                        help="your data bundle size in MB")
    parser.add_argument("--bundle-ugx", type=float, default=DEFAULT_BUNDLE_UGX,
                        help="what that bundle costs in UGX")
    args = parser.parse_args()

    urls = [clean_url(u) for u in args.urls]
    infos = []

    for url in urls:
        print(f"Checking {url} ...")
        try:
            infos.append(analyze(url))
        except (OSError, ValueError) as err:
            # OSError covers: site refused (403), not found (404), too slow
            # (timeout), no internet, and security-certificate problems.
            print(f"  Could not open this page, skipping: {err}")

    print()
    if not infos:
        print("No pages could be checked.")
        raise SystemExit(1)

    if len(infos) == 1:
        show_detail(infos[0], args.bundle_mb, args.bundle_ugx)
    else:
        show_ranking(infos, args.bundle_mb, args.bundle_ugx)

    print("\nNote: this counts each page and the files it links directly.")
    print("Content loaded later by JavaScript (feeds, video, ads) is NOT counted,")
    print("so the real cost is usually higher than shown.\n")


if __name__ == "__main__":
    main()
