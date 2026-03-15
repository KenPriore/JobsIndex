#!/usr/bin/env python3
"""
Step 3: Score each occupation for AI exposure using Claude Haiku.
Reads data/occupations.csv, scores each 0-10, writes data/occupations_scored.csv
"""

import csv
import json
import os
import sys
import time
from pathlib import Path
from anthropic import Anthropic

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_CSV = DATA_DIR / "occupations.csv"
OUTPUT_CSV = DATA_DIR / "occupations_scored.csv"
MD_DIR = DATA_DIR / "markdown"

MODEL = "claude-haiku-4-5-20251001"

SCORING_PROMPT = """You are an expert labor economist analyzing AI's impact on occupations.

Score the following occupation on a 0-10 scale for AI EXPOSURE — meaning how much AI and automation will reshape this occupation, accounting for both:
1. Direct task automation (AI performing tasks currently done by humans)
2. Productivity-driven workforce reduction (AI making each worker so productive that fewer are needed)

SCORING ANCHORS:
- 0: Zero AI impact. Purely physical, unpredictable environments. Example: Roofers.
- 1: Minimal AI impact. Physical labor with negligible digital component. Example: Janitors, construction laborers.
- 2: Very low. Mostly physical with minor administrative tasks. Example: Plumbers, firefighters.
- 3: Low. Manual work with some digital reporting. Example: Electricians, dental hygienists.
- 4: Below moderate. Mix of physical and digital, but physical dominates. Example: Registered nurses.
- 5: Moderate. Balanced physical/digital or mixed task profile. Example: Physicians, retail workers.
- 6: Above moderate. Significant digital work with some in-person requirements. Example: Teachers, managers.
- 7: High. Primarily knowledge work with some interpersonal/physical component. Example: Accountants, engineers.
- 8: Very high. Almost entirely screen-based digital work. Example: Software developers, data analysts.
- 9: Extremely high. Fully digital output, highly automatable. Example: Paralegals, editors, graphic designers.
- 10: Maximum exposure. Completely automatable by current AI models. Example: Medical transcriptionists.

IMPORTANT: Score based on the CORE duties of the occupation, not edge cases. Consider what percentage of the work can be augmented or replaced by AI.

Respond with ONLY a JSON object:
{
  "score": <integer 0-10>,
  "reasoning": "<2-3 sentence explanation of why this score>"
}"""


def load_markdown(occupation_file):
    """Try to load the markdown description for richer context."""
    for md_file in MD_DIR.glob("*.md"):
        return md_file.read_text(encoding="utf-8")[:3000]
    return ""


def score_occupation(client, occupation, description, category, education, median_pay):
    """Score a single occupation using Claude Haiku."""
    context = f"""OCCUPATION: {occupation}
CATEGORY: {category}
TYPICAL EDUCATION: {education or 'Not specified'}
MEDIAN PAY: ${median_pay:,}/year""" if median_pay else f"""OCCUPATION: {occupation}
CATEGORY: {category}
TYPICAL EDUCATION: {education or 'Not specified'}
MEDIAN PAY: Not available"""

    if description:
        context += f"\n\nDESCRIPTION: {description[:1500]}"

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[
                {"role": "user", "content": f"{SCORING_PROMPT}\n\n{context}"}
            ],
        )
        text = response.content[0].text.strip()
        # Parse JSON from response (handle markdown code blocks)
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)
        return int(result["score"]), result["reasoning"]
    except Exception as e:
        print(f"    Error scoring {occupation}: {e}")
        return None, str(e)


def main():
    if not INPUT_CSV.exists():
        print(f"Input file not found: {INPUT_CSV}")
        print("Run 02_extract_data.py first.")
        return

    client = Anthropic()

    # Read input CSV
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    print(f"Scoring {len(records)} occupations with {MODEL}...")

    # Check for existing progress
    scored = {}
    if OUTPUT_CSV.exists():
        with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("ai_score"):
                    scored[row["occupation"]] = row
        print(f"  Found {len(scored)} already scored, resuming...")

    # Score each occupation
    fieldnames = [
        "occupation", "category", "median_pay", "num_jobs", "outlook_pct",
        "education", "work_experience", "training", "description", "url",
        "ai_score", "ai_reasoning"
    ]

    results = []
    for i, record in enumerate(records):
        occupation = record["occupation"]

        if occupation in scored:
            results.append(scored[occupation])
            continue

        median_pay = int(record["median_pay"]) if record.get("median_pay") else None
        score, reasoning = score_occupation(
            client,
            occupation,
            record.get("description", ""),
            record.get("category", ""),
            record.get("education", ""),
            median_pay,
        )

        record["ai_score"] = score if score is not None else ""
        record["ai_reasoning"] = reasoning
        results.append(record)

        status = f"[{score}/10]" if score is not None else "[FAIL]"
        print(f"  {i+1}/{len(records)} {status} {occupation}")

        # Save progress every 10 records
        if (i + 1) % 10 == 0:
            with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(results)

        # Rate limiting
        time.sleep(0.2)

    # Final save
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    # Print summary stats
    scores = [int(r["ai_score"]) for r in results if r.get("ai_score")]
    if scores:
        avg = sum(scores) / len(scores)
        print(f"\nScoring complete!")
        print(f"  Total scored: {len(scores)}")
        print(f"  Average score: {avg:.1f}")
        print(f"  Min: {min(scores)}, Max: {max(scores)}")

        # Weighted average by employment
        weighted_num = 0
        weighted_den = 0
        for r in results:
            if r.get("ai_score") and r.get("num_jobs"):
                try:
                    s = int(r["ai_score"])
                    j = int(r["num_jobs"])
                    weighted_num += s * j
                    weighted_den += j
                except (ValueError, TypeError):
                    pass
        if weighted_den > 0:
            print(f"  Weighted avg (by employment): {weighted_num/weighted_den:.1f}")
            print(f"  Total jobs covered: {weighted_den:,}")


if __name__ == "__main__":
    main()
