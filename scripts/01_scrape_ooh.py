#!/usr/bin/env python3
"""
Step 1: Scrape all occupation pages from BLS Occupational Outlook Handbook.
Uses Playwright in non-headless mode (BLS blocks headless browsers).
Saves raw HTML files to data/raw_html/
"""

import os
import re
import json
import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

DATA_DIR = Path(__file__).parent.parent / "data"
HTML_DIR = DATA_DIR / "raw_html"
HTML_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.bls.gov/ooh/"


def get_occupation_links(page):
    """Get all occupation page links from the OOH home page and group pages."""
    print("Fetching OOH home page...")
    page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
    time.sleep(2)

    # Get all links from the main page
    links = page.eval_on_selector_all(
        "a[href]",
        """els => els.map(el => ({
            href: el.href,
            text: el.textContent.trim()
        }))"""
    )

    # Find occupation group pages (e.g., /ooh/management/home.htm)
    group_pattern = re.compile(r"^https://www\.bls\.gov/ooh/[a-z\-]+/home\.htm$", re.IGNORECASE)
    group_urls = set()
    for link in links:
        if group_pattern.match(link["href"]):
            group_urls.add(link["href"])

    print(f"Found {len(group_urls)} occupation groups")

    # Also collect individual occupation links directly from the home page
    occupation_urls = {}
    occ_pattern = re.compile(
        r"^https://www\.bls\.gov/ooh/[a-z\-]+/[a-z\-]+\.htm$", re.IGNORECASE
    )

    # First pass: grab any occupation links already visible on the home page
    for link in links:
        href = link["href"]
        if occ_pattern.match(href) and "home.htm" not in href and "ooh-site-map" not in href and "a-z-index" not in href and "occupation-finder" not in href:
            occupation_urls[href] = link["text"]

    # Visit each group page to find more individual occupation links
    for group_url in sorted(group_urls):
        print(f"  Scanning group: {group_url}")
        try:
            page.goto(group_url, wait_until="networkidle", timeout=30000)
            time.sleep(1)
            group_links = page.eval_on_selector_all(
                "a[href]",
                """els => els.map(el => ({
                    href: el.href,
                    text: el.textContent.trim()
                }))"""
            )
            for link in group_links:
                href = link["href"]
                if occ_pattern.match(href) and "home.htm" not in href:
                    occupation_urls[href] = link["text"]
        except Exception as e:
            print(f"    Error scanning {group_url}: {e}")

    print(f"\nFound {len(occupation_urls)} occupation pages")
    return occupation_urls


def scrape_occupation_page(page, url, name):
    """Scrape a single occupation page and save raw HTML."""
    # Create filename from URL
    parts = url.replace(BASE_URL, "").replace(".htm", "").split("/")
    filename = "__".join(parts) + ".html"
    filepath = HTML_DIR / filename

    if filepath.exists():
        print(f"  [SKIP] {name} (already scraped)")
        return True

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(1)

        # Get the main content area
        html = page.content()
        filepath.write_text(html, encoding="utf-8")
        print(f"  [OK] {name}")
        return True
    except Exception as e:
        print(f"  [ERROR] {name}: {e}")
        return False


def main():
    headless = "--headless" in sys.argv

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Step 1: Get all occupation links
        index_file = DATA_DIR / "occupation_index.json"
        if index_file.exists():
            print("Loading cached occupation index...")
            occupation_urls = json.loads(index_file.read_text())
        else:
            occupation_urls = get_occupation_links(page)
            index_file.write_text(json.dumps(occupation_urls, indent=2))

        # Step 2: Scrape each occupation page
        print(f"\nScraping {len(occupation_urls)} occupation pages...")
        success = 0
        failed = 0
        for url, name in sorted(occupation_urls.items()):
            if scrape_occupation_page(page, url, name):
                success += 1
            else:
                failed += 1
            time.sleep(0.5)  # Be polite

        print(f"\nDone: {success} scraped, {failed} failed")
        browser.close()


if __name__ == "__main__":
    main()
