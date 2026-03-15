#!/bin/bash
# Run the full pipeline: scrape → extract → score → visualize
set -e

echo "=== Step 1: Scrape BLS OOH ==="
python3 scripts/01_scrape_ooh.py

echo ""
echo "=== Step 2: Extract structured data ==="
python3 scripts/02_extract_data.py

echo ""
echo "=== Step 3: Score occupations with Claude Haiku ==="
python3 scripts/03_score_occupations.py

echo ""
echo "=== Step 4: Build treemap visualization ==="
python3 scripts/04_build_treemap.py

echo ""
echo "=== Done! Open index.html in a browser ==="
