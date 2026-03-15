#!/usr/bin/env python3
"""
Step 2: Extract structured data from scraped BLS OOH HTML files.
Produces data/occupations.csv with columns:
  - occupation, category, median_pay, num_jobs, job_outlook,
    education, work_experience, on_job_training, description, url
"""

import csv
import re
import os
from pathlib import Path
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent / "data"
HTML_DIR = DATA_DIR / "raw_html"
OUTPUT_CSV = DATA_DIR / "occupations.csv"
OUTPUT_MD_DIR = DATA_DIR / "markdown"
OUTPUT_MD_DIR.mkdir(parents=True, exist_ok=True)


def parse_pay(text):
    """Parse median pay string to annual number."""
    if not text:
        return None
    text = text.strip()
    # Look for annual salary pattern: $XX,XXX per year
    annual = re.search(r'\$([0-9,]+)\s*per\s*year', text, re.IGNORECASE)
    if annual:
        return int(annual.group(1).replace(",", ""))
    # Look for hourly: $XX.XX per hour -> approximate annual
    hourly = re.search(r'\$([\d.]+)\s*per\s*hour', text, re.IGNORECASE)
    if hourly:
        return int(float(hourly.group(1)) * 2080)
    # Look for just a dollar amount
    amount = re.search(r'\$([\d,]+)', text)
    if amount:
        return int(amount.group(1).replace(",", ""))
    return None


def parse_jobs_count(text):
    """Parse number of jobs string to integer."""
    if not text:
        return None
    # Match patterns like "1,847,900" or "2.1 million"
    millions = re.search(r'([\d.]+)\s*million', text, re.IGNORECASE)
    if millions:
        return int(float(millions.group(1)) * 1_000_000)
    number = re.search(r'([\d,]+)', text)
    if number:
        return int(number.group(1).replace(",", ""))
    return None


def parse_outlook(text):
    """Parse job outlook percentage."""
    if not text:
        return None
    match = re.search(r'(-?\d+)\s*%', text)
    if match:
        return int(match.group(1))
    return None


def extract_quick_facts(soup):
    """Extract data from the Quick Facts / Summary table."""
    facts = {}

    # Look for the summary/quick facts table
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)

                if "median pay" in label or "median annual wage" in label or "wage" in label:
                    facts["median_pay_raw"] = value
                    facts["median_pay"] = parse_pay(value)
                elif "number of jobs" in label:
                    facts["num_jobs_raw"] = value
                    facts["num_jobs"] = parse_jobs_count(value)
                elif "employment change" in label:
                    facts["employment_change_raw"] = value
                    facts["employment_change"] = parse_jobs_count(value)
                elif "outlook" in label or "growth" in label:
                    facts["outlook_raw"] = value
                    facts["outlook_pct"] = parse_outlook(value)
                elif "education" in label or "entry-level" in label:
                    facts["education"] = value
                elif "work experience" in label:
                    facts["work_experience"] = value
                elif "on-the-job training" in label or "training" in label:
                    facts["training"] = value

    # Also try to extract from div-based layouts (BLS uses both)
    for div in soup.find_all("div", class_=re.compile("summary|quickfacts|quick-facts", re.I)):
        text = div.get_text()
        if "median" in text.lower() and "median_pay" not in facts:
            pay = parse_pay(text)
            if pay:
                facts["median_pay"] = pay

    return facts


def extract_description(soup):
    """Extract the occupation description/summary text."""
    # Try various selectors for the main description
    for selector in [
        "div#TextContent1",
        "div.ooh-what-they-do",
        "div[id*='summary']",
        "div[id*='what-they-do']",
        "article",
        "div.content",
    ]:
        el = soup.select_one(selector)
        if el:
            # Get first few paragraphs
            paragraphs = el.find_all("p")
            if paragraphs:
                desc = " ".join(p.get_text(strip=True) for p in paragraphs[:3])
                if len(desc) > 50:
                    return desc

    # Fallback: get all paragraph text from main content
    main = soup.find("main") or soup.find("body")
    if main:
        paragraphs = main.find_all("p")
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 100 and "bureau of labor" not in text.lower():
                return text
    return ""


def extract_full_text(soup):
    """Extract full page text for markdown conversion."""
    main = soup.find("main") or soup.find("article") or soup.find("body")
    if not main:
        return ""

    # Remove nav, footer, scripts
    for tag in main.find_all(["nav", "footer", "script", "style", "header"]):
        tag.decompose()

    text = main.get_text(separator="\n", strip=True)
    # Clean up excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def process_file(filepath):
    """Process a single HTML file and return structured data."""
    html = filepath.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    # Get occupation name from title
    title_el = soup.find("title")
    title = title_el.get_text(strip=True) if title_el else ""
    # Clean title - remove " : Occupational Outlook Handbook" suffix
    occupation = re.sub(
        r'\s*[:|\-]\s*(U\.S\.\s*)?Bureau of Labor Statistics.*$', '', title, flags=re.IGNORECASE
    ).strip()
    occupation = re.sub(
        r'\s*[:|\-]\s*Occupational Outlook Handbook.*$', '', occupation, flags=re.IGNORECASE
    ).strip()

    if not occupation or len(occupation) < 3:
        occupation = filepath.stem.replace("__", " > ").replace("-", " ").title()

    # Get category from filename (first part before __)
    parts = filepath.stem.split("__")
    category = parts[0].replace("-", " ").title() if parts else "Unknown"

    # Extract structured data
    facts = extract_quick_facts(soup)
    description = extract_description(soup)
    full_text = extract_full_text(soup)

    # Reconstruct URL
    url_path = filepath.stem.replace("__", "/") + ".htm"
    url = f"https://www.bls.gov/ooh/{url_path}"

    # Save markdown
    md_filename = filepath.stem + ".md"
    md_path = OUTPUT_MD_DIR / md_filename
    md_content = f"# {occupation}\n\n{full_text}"
    md_path.write_text(md_content, encoding="utf-8")

    return {
        "occupation": occupation,
        "category": category,
        "median_pay": facts.get("median_pay", ""),
        "num_jobs": facts.get("num_jobs", ""),
        "outlook_pct": facts.get("outlook_pct", ""),
        "education": facts.get("education", ""),
        "work_experience": facts.get("work_experience", ""),
        "training": facts.get("training", ""),
        "description": description[:2000],  # Truncate for CSV
        "url": url,
    }


def main():
    html_files = sorted(HTML_DIR.glob("*.html"))
    if not html_files:
        print("No HTML files found in data/raw_html/")
        print("Run 01_scrape_ooh.py first.")
        return

    print(f"Processing {len(html_files)} HTML files...")

    records = []
    for filepath in html_files:
        try:
            record = process_file(filepath)
            records.append(record)
            pay_str = f"${record['median_pay']:,}" if record['median_pay'] else "N/A"
            jobs_str = f"{record['num_jobs']:,}" if record['num_jobs'] else "N/A"
            print(f"  [OK] {record['occupation']} | Pay: {pay_str} | Jobs: {jobs_str}")
        except Exception as e:
            print(f"  [ERROR] {filepath.name}: {e}")

    # Write CSV
    if records:
        fieldnames = [
            "occupation", "category", "median_pay", "num_jobs", "outlook_pct",
            "education", "work_experience", "training", "description", "url"
        ]
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        print(f"\nWrote {len(records)} records to {OUTPUT_CSV}")
    else:
        print("No records extracted!")


if __name__ == "__main__":
    main()
