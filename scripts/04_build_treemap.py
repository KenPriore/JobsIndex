#!/usr/bin/env python3
"""
Step 4: Generate interactive treemap HTML visualization from scored data.
Reads data/occupations_scored.csv, produces index.html
"""

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_CSV = DATA_DIR / "occupations_scored.csv"
OUTPUT_HTML = Path(__file__).parent.parent / "index.html"


def score_to_color(score):
    """Convert 0-10 score to green-to-red color."""
    if score is None:
        return "#666666"
    t = score / 10.0
    if t <= 0.5:
        # Green to Yellow
        r = int(50 + 180 * (t * 2))
        g = int(160 - 40 * (t * 2))
        b = int(50 - 20 * (t * 2))
    else:
        # Yellow to Red
        r = int(230 - 30 * ((t - 0.5) * 2))
        g = int(120 - 100 * ((t - 0.5) * 2))
        b = int(30)
    return f"rgb({r},{g},{b})"


def compute_stats(records):
    """Compute all sidebar statistics."""
    total_jobs = 0
    weighted_score_sum = 0

    # By pay bracket
    pay_brackets = {
        "<$35K": {"scores": [], "jobs": 0},
        "$35-50K": {"scores": [], "jobs": 0},
        "$50-75K": {"scores": [], "jobs": 0},
        "$75-100K": {"scores": [], "jobs": 0},
        "$100K+": {"scores": [], "jobs": 0},
    }

    # By education
    edu_map = {
        "No formal educational credential": "No degree/HS",
        "High school diploma or equivalent": "No degree/HS",
        "Some college, no degree": "Postsec/Assoc",
        "Postsecondary nondegree award": "Postsec/Assoc",
        "Associate's degree": "Postsec/Assoc",
        "Bachelor's degree": "Bachelor's",
        "Master's degree": "Master's",
        "Doctoral or professional degree": "Doctoral/Prof",
    }
    edu_brackets = {
        "No degree/HS": {"scores": [], "jobs": 0},
        "Postsec/Assoc": {"scores": [], "jobs": 0},
        "Bachelor's": {"scores": [], "jobs": 0},
        "Master's": {"scores": [], "jobs": 0},
        "Doctoral/Prof": {"scores": [], "jobs": 0},
    }

    # Exposure breakdown
    exposure_levels = {
        "Minimal (0-1)": {"jobs": 0, "count": 0},
        "Low (2-3)": {"jobs": 0, "count": 0},
        "Moderate (4-5)": {"jobs": 0, "count": 0},
        "High (6-7)": {"jobs": 0, "count": 0},
        "Very high (8-10)": {"jobs": 0, "count": 0},
    }

    for r in records:
        score = r.get("score")
        jobs = r.get("jobs", 0)
        pay = r.get("pay")
        edu = r.get("education", "")

        if score is None:
            continue

        total_jobs += jobs
        weighted_score_sum += score * jobs

        # Pay bracket
        if pay:
            if pay < 35000:
                bracket = "<$35K"
            elif pay < 50000:
                bracket = "$35-50K"
            elif pay < 75000:
                bracket = "$50-75K"
            elif pay < 100000:
                bracket = "$75-100K"
            else:
                bracket = "$100K+"
            pay_brackets[bracket]["scores"].append((score, jobs))
            pay_brackets[bracket]["jobs"] += jobs

        # Education bracket
        edu_key = edu_map.get(edu, "")
        if edu_key and edu_key in edu_brackets:
            edu_brackets[edu_key]["scores"].append((score, jobs))
            edu_brackets[edu_key]["jobs"] += jobs

        # Exposure level
        if score <= 1:
            level = "Minimal (0-1)"
        elif score <= 3:
            level = "Low (2-3)"
        elif score <= 5:
            level = "Moderate (4-5)"
        elif score <= 7:
            level = "High (6-7)"
        else:
            level = "Very high (8-10)"
        exposure_levels[level]["jobs"] += jobs
        exposure_levels[level]["count"] += 1

    weighted_avg = weighted_score_sum / total_jobs if total_jobs > 0 else 0

    # Compute weighted averages for each bracket
    def weighted_avg_bracket(bracket_data):
        total_w = sum(j for _, j in bracket_data["scores"])
        if total_w == 0:
            return 0
        return sum(s * j for s, j in bracket_data["scores"]) / total_w

    pay_stats = {k: round(weighted_avg_bracket(v), 1) for k, v in pay_brackets.items()}
    edu_stats = {k: round(weighted_avg_bracket(v), 1) for k, v in edu_brackets.items()}

    # Legal occupations spotlight
    legal_occs = []
    for r in records:
        if r.get("category") == "Legal":
            legal_occs.append({
                "name": r["name"],
                "score": r["score"],
                "jobs": r["jobs"],
                "pay": r.get("pay"),
            })
    legal_occs.sort(key=lambda x: x["score"], reverse=True)

    return {
        "total_jobs": total_jobs,
        "weighted_avg": round(weighted_avg, 1),
        "pay_stats": pay_stats,
        "edu_stats": edu_stats,
        "exposure_levels": {
            k: {"jobs": v["jobs"], "count": v["count"]}
            for k, v in exposure_levels.items()
        },
        "legal": legal_occs,
    }


def build_treemap_data(records):
    """Build hierarchical data for treemap."""
    # Group by category
    categories = {}
    for r in records:
        cat = r.get("category", "Other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    return categories


def main():
    if not INPUT_CSV.exists():
        print(f"Input file not found: {INPUT_CSV}")
        print("Run 03_score_occupations.py first.")
        return

    # Read scored data
    records = []
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                score = int(row["ai_score"]) if row.get("ai_score") else None
            except (ValueError, TypeError):
                score = None

            try:
                jobs = int(row["num_jobs"]) if row.get("num_jobs") else 0
            except (ValueError, TypeError):
                jobs = 0

            try:
                pay = int(row["median_pay"]) if row.get("median_pay") else None
            except (ValueError, TypeError):
                pay = None

            try:
                outlook = int(row["outlook_pct"]) if row.get("outlook_pct") else None
            except (ValueError, TypeError):
                outlook = None

            records.append({
                "name": row.get("occupation", "Unknown"),
                "category": row.get("category", "Other"),
                "score": score,
                "jobs": jobs,
                "pay": pay,
                "outlook": outlook,
                "education": row.get("education", ""),
                "reasoning": row.get("ai_reasoning", ""),
                "url": row.get("url", ""),
            })

    # Filter out records without scores
    scored_records = [r for r in records if r["score"] is not None]
    print(f"Loaded {len(scored_records)} scored occupations")

    # Compute stats
    stats = compute_stats(scored_records)
    print(f"Total jobs: {stats['total_jobs']:,}")
    print(f"Weighted avg exposure: {stats['weighted_avg']}")
    print(f"Pay stats: {stats['pay_stats']}")
    print(f"Edu stats: {stats['edu_stats']}")

    # Build treemap data grouped by category
    categories = build_treemap_data(scored_records)

    # Prepare JSON data for the frontend
    treemap_children = []
    for cat_name, cat_records in sorted(categories.items()):
        children = []
        for r in sorted(cat_records, key=lambda x: x["jobs"], reverse=True):
            children.append({
                "name": r["name"],
                "value": max(r["jobs"], 1000),  # minimum size for visibility
                "score": r["score"],
                "jobs": r["jobs"],
                "pay": r["pay"],
                "outlook": r["outlook"],
                "education": r["education"],
                "reasoning": r["reasoning"],
                "url": r["url"],
                "color": score_to_color(r["score"]),
            })
        treemap_children.append({
            "name": cat_name,
            "children": children,
        })

    treemap_data = {"name": "US Jobs", "children": treemap_children}

    # Generate HTML
    html = generate_html(treemap_data, stats, len(scored_records))
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"\nTreemap written to {OUTPUT_HTML}")


def generate_html(treemap_data, stats, num_occupations):
    """Generate the complete interactive HTML page."""
    data_json = json.dumps(treemap_data)
    stats_json = json.dumps(stats)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Exposure of the US Job Market</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #1a1a1a;
  color: #e0e0e0;
  display: flex;
  height: 100vh;
  overflow: hidden;
}}

#sidebar {{
  width: 260px;
  min-width: 260px;
  padding: 20px;
  background: #222;
  overflow-y: auto;
  border-right: 1px solid #333;
}}

#sidebar h1 {{
  font-size: 18px;
  margin-bottom: 4px;
  color: #fff;
}}

#sidebar .subtitle {{
  font-size: 11px;
  color: #888;
  margin-bottom: 16px;
  line-height: 1.4;
}}

#sidebar .subtitle a {{
  color: #6af;
  text-decoration: none;
}}

.stat-section {{
  margin-bottom: 18px;
}}

.stat-label {{
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #888;
  margin-bottom: 4px;
}}

.stat-value {{
  font-size: 36px;
  font-weight: 700;
  color: #fff;
}}

.stat-unit {{
  font-size: 12px;
  color: #888;
  font-weight: 400;
}}

/* Histogram */
.histogram {{
  margin: 8px 0;
}}

.hist-row {{
  display: flex;
  align-items: center;
  margin: 3px 0;
  font-size: 11px;
}}

.hist-bar-container {{
  flex: 1;
  height: 14px;
  background: #333;
  margin: 0 8px;
  border-radius: 2px;
  overflow: hidden;
}}

.hist-bar {{
  height: 100%;
  border-radius: 2px;
}}

.hist-label {{
  width: 80px;
  flex-shrink: 0;
}}

.hist-value {{
  width: 50px;
  text-align: right;
  flex-shrink: 0;
  color: #aaa;
}}

.hist-pct {{
  width: 30px;
  text-align: right;
  flex-shrink: 0;
  color: #666;
  font-size: 10px;
}}

/* Exposure by pay/edu */
.bracket-row {{
  display: flex;
  align-items: center;
  margin: 3px 0;
  font-size: 11px;
}}

.bracket-label {{
  width: 90px;
  flex-shrink: 0;
}}

.bracket-bar-container {{
  flex: 1;
  height: 10px;
  background: #333;
  margin: 0 8px;
  border-radius: 2px;
  overflow: hidden;
}}

.bracket-bar {{
  height: 100%;
  border-radius: 2px;
}}

.bracket-value {{
  width: 30px;
  text-align: right;
  flex-shrink: 0;
  font-weight: 600;
}}

/* Treemap */
#treemap-container {{
  flex: 1;
  position: relative;
  overflow: hidden;
}}

.treemap-cell {{
  position: absolute;
  overflow: hidden;
  border: 1px solid rgba(0,0,0,0.3);
  cursor: pointer;
  transition: opacity 0.15s;
}}

.treemap-cell:hover {{
  opacity: 0.85;
  border-color: #fff;
  z-index: 10;
}}

.cell-label {{
  padding: 4px 6px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0,0,0,0.8);
  pointer-events: none;
  line-height: 1.2;
}}

.cell-sublabel {{
  font-size: 9px;
  font-weight: 400;
  opacity: 0.8;
  display: block;
}}

.category-label {{
  position: absolute;
  font-size: 10px;
  font-weight: 700;
  color: rgba(255,255,255,0.15);
  text-transform: uppercase;
  letter-spacing: 1px;
  pointer-events: none;
  z-index: 5;
}}

/* Tooltip */
#tooltip {{
  display: none;
  position: fixed;
  background: #2a2a2a;
  border: 1px solid #555;
  border-radius: 8px;
  padding: 16px;
  max-width: 400px;
  min-width: 280px;
  z-index: 100;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  font-size: 13px;
  pointer-events: none;
}}

#tooltip h3 {{
  font-size: 16px;
  margin-bottom: 8px;
  color: #fff;
}}

#tooltip .score-badge {{
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 10px;
}}

#tooltip .detail-grid {{
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  margin-bottom: 10px;
}}

#tooltip .detail-label {{
  color: #888;
}}

#tooltip .detail-value {{
  color: #ddd;
  text-align: right;
}}

#tooltip .reasoning {{
  font-size: 12px;
  color: #aaa;
  line-height: 1.5;
  border-top: 1px solid #444;
  padding-top: 8px;
  margin-top: 4px;
}}
</style>
</head>
<body>

<div id="sidebar">
  <h1>AI Exposure of the US Job Market</h1>
  <div class="subtitle">
    {num_occupations} occupations &middot; color = AI exposure<br>
    Data from <a href="https://www.bls.gov/ooh/" target="_blank">BLS</a>, scored by Claude Haiku
  </div>

  <div class="stat-section">
    <div class="stat-label">Total Jobs</div>
    <div class="stat-value" id="total-jobs"></div>
  </div>

  <div class="stat-section">
    <div class="stat-label">Weighted Avg. Exposure</div>
    <div class="stat-value" id="avg-exposure"></div>
    <div class="stat-unit">job-weighted, 0&ndash;10 scale</div>
  </div>

  <div class="stat-section">
    <div class="stat-label">Jobs by Exposure (Weighted by Employment)</div>
    <div class="histogram" id="histogram"></div>
  </div>

  <div class="stat-section">
    <div class="stat-label">Exposure by Pay</div>
    <div id="pay-stats"></div>
  </div>

  <div class="stat-section">
    <div class="stat-label">Exposure by Education</div>
    <div id="edu-stats"></div>
  </div>

  <div class="stat-section">
    <div class="stat-label">Legal Occupations</div>
    <div id="legal-stats"></div>
  </div>
</div>

<div id="treemap-container"></div>
<div id="tooltip"></div>

<script>
const DATA = {data_json};
const STATS = {stats_json};

// Populate sidebar
document.getElementById('total-jobs').textContent =
  (STATS.total_jobs / 1e6).toFixed(0) + 'M';
document.getElementById('avg-exposure').textContent = STATS.weighted_avg.toFixed(1);

// Histogram of exposure levels
const histEl = document.getElementById('histogram');
const maxJobs = Math.max(...Object.values(STATS.exposure_levels).map(v => v.jobs));
const levelColors = {{
  "Minimal (0-1)": "#327832",
  "Low (2-3)": "#5a9832",
  "Moderate (4-5)": "#b8a030",
  "High (6-7)": "#c87828",
  "Very high (8-10)": "#c83828",
}};

// Build histogram
let histHTML = '';
for (const [level, data] of Object.entries(STATS.exposure_levels)) {{
  const pct = STATS.total_jobs > 0 ? Math.round(data.jobs / STATS.total_jobs * 100) : 0;
  const barWidth = maxJobs > 0 ? (data.jobs / maxJobs * 100) : 0;
  const jobsStr = (data.jobs / 1e6).toFixed(1) + 'M';
  histHTML += `
    <div class="hist-row">
      <span class="hist-label">${{level}}</span>
      <div class="hist-bar-container">
        <div class="hist-bar" style="width:${{barWidth}}%;background:${{levelColors[level] || '#666'}}"></div>
      </div>
      <span class="hist-value">${{jobsStr}}</span>
      <span class="hist-pct">${{pct}}%</span>
    </div>`;
}}
histEl.innerHTML = histHTML;

// Pay stats
function renderBracketStats(containerId, statsObj) {{
  const el = document.getElementById(containerId);
  let html = '';
  for (const [label, val] of Object.entries(statsObj)) {{
    const barWidth = (val / 10) * 100;
    const t = val / 10;
    let r, g, b;
    if (t <= 0.5) {{
      r = Math.round(50 + 180 * (t * 2));
      g = Math.round(160 - 40 * (t * 2));
      b = Math.round(50 - 20 * (t * 2));
    }} else {{
      r = Math.round(230 - 30 * ((t - 0.5) * 2));
      g = Math.round(120 - 100 * ((t - 0.5) * 2));
      b = 30;
    }}
    const color = `rgb(${{r}},${{g}},${{b}})`;
    html += `<div class="bracket-row">
      <span class="bracket-label">${{label}}</span>
      <div class="bracket-bar-container">
        <div class="bracket-bar" style="width:${{barWidth}}%;background:${{color}}"></div>
      </div>
      <span class="bracket-value">${{val}}</span>
    </div>`;
  }}
  el.innerHTML = html;
}}

renderBracketStats('pay-stats', STATS.pay_stats);
renderBracketStats('edu-stats', STATS.edu_stats);

// Legal occupations spotlight
const legalEl = document.getElementById('legal-stats');
let legalHTML = '';
if (STATS.legal && STATS.legal.length > 0) {{
  STATS.legal.forEach(occ => {{
    const t = occ.score / 10;
    let r, g, b;
    if (t <= 0.5) {{
      r = Math.round(50 + 180 * (t * 2));
      g = Math.round(160 - 40 * (t * 2));
      b = Math.round(50 - 20 * (t * 2));
    }} else {{
      r = Math.round(230 - 30 * ((t - 0.5) * 2));
      g = Math.round(120 - 100 * ((t - 0.5) * 2));
      b = 30;
    }}
    const color = `rgb(${{r}},${{g}},${{b}})`;
    const jobsStr = occ.jobs >= 1e6 ? (occ.jobs / 1e6).toFixed(1) + 'M' : Math.round(occ.jobs / 1e3) + 'K';
    const payStr = occ.pay ? '$' + Math.round(occ.pay / 1000) + 'K' : '';
    legalHTML += `<div class="bracket-row" style="margin:4px 0">
      <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${{color}};margin-right:6px;flex-shrink:0"></span>
      <span style="flex:1;font-size:11px;line-height:1.3">${{occ.name}}</span>
      <span style="width:35px;text-align:right;flex-shrink:0;font-weight:600;font-size:11px">${{occ.score}}/10</span>
    </div>
    <div style="font-size:10px;color:#777;margin-left:16px;margin-bottom:4px">${{jobsStr}} jobs${{payStr ? ' · ' + payStr : ''}}</div>`;
  }});
  const totalLegalJobs = STATS.legal.reduce((a, o) => a + o.jobs, 0);
  const weightedLegalScore = STATS.legal.reduce((a, o) => a + o.score * o.jobs, 0) / totalLegalJobs;
  legalHTML += `<div style="border-top:1px solid #444;margin-top:8px;padding-top:6px;font-size:11px;color:#aaa">
    Weighted avg: <strong style="color:#fff">${{weightedLegalScore.toFixed(1)}}</strong> · ${{(totalLegalJobs / 1e6).toFixed(1)}}M jobs
  </div>`;
}}
legalEl.innerHTML = legalHTML;

// Build treemap
const container = document.getElementById('treemap-container');
const width = container.clientWidth;
const height = container.clientHeight;

const root = d3.hierarchy(DATA)
  .sum(d => d.value || 0)
  .sort((a, b) => b.value - a.value);

d3.treemap()
  .size([width, height])
  .paddingOuter(3)
  .paddingTop(18)
  .paddingInner(1)
  .round(true)(root);

// Render category labels
root.children.forEach(cat => {{
  const label = document.createElement('div');
  label.className = 'category-label';
  label.style.left = cat.x0 + 4 + 'px';
  label.style.top = cat.y0 + 2 + 'px';
  label.textContent = cat.data.name;
  container.appendChild(label);
}});

// Render cells
const tooltip = document.getElementById('tooltip');
const leaves = root.leaves();

leaves.forEach(leaf => {{
  const d = leaf.data;
  const w = leaf.x1 - leaf.x0;
  const h = leaf.y1 - leaf.y0;

  if (w < 2 || h < 2) return;

  const cell = document.createElement('div');
  cell.className = 'treemap-cell';
  cell.style.left = leaf.x0 + 'px';
  cell.style.top = leaf.y0 + 'px';
  cell.style.width = w + 'px';
  cell.style.height = h + 'px';
  cell.style.background = d.color || '#666';

  // Label
  if (w > 40 && h > 20) {{
    const label = document.createElement('div');
    label.className = 'cell-label';
    let nameText = d.name;
    const maxChars = Math.floor(w / 6.5);
    if (nameText.length > maxChars) {{
      nameText = nameText.substring(0, maxChars - 1) + '\u2026';
    }}
    label.innerHTML = nameText;
    if (w > 60 && h > 35) {{
      const jobsStr = d.jobs >= 1e6 ? (d.jobs / 1e6).toFixed(1) + 'M jobs' : Math.round(d.jobs / 1e3) + 'K jobs';
      label.innerHTML += `<span class="cell-sublabel">${{d.score}}/10 &middot; ${{jobsStr}}</span>`;
    }}
    cell.appendChild(label);
  }}

  // Tooltip
  cell.addEventListener('mouseenter', (e) => {{
    const payStr = d.pay ? '$' + d.pay.toLocaleString() : 'N/A';
    const jobsStr = d.jobs ? d.jobs.toLocaleString() : 'N/A';
    const outlookStr = d.outlook !== null && d.outlook !== undefined ? d.outlook + '% ' + (d.outlook >= 7 ? '(Much faster than average)' : d.outlook >= 4 ? '(Faster than average)' : d.outlook >= 1 ? '(As fast as average)' : d.outlook >= -1 ? '(Little or no change)' : '(Decline)') : 'N/A';

    tooltip.innerHTML = `
      <h3>${{d.name}}</h3>
      <div class="score-badge" style="background:${{d.color}};color:#fff">AI Exposure: ${{d.score}}/10</div>
      <div class="detail-grid">
        <span class="detail-label">Median pay</span><span class="detail-value">${{payStr}}</span>
        <span class="detail-label">Jobs (2024)</span><span class="detail-value">${{jobsStr}}</span>
        <span class="detail-label">Outlook</span><span class="detail-value">${{outlookStr}}</span>
        <span class="detail-label">Education</span><span class="detail-value">${{d.education || 'N/A'}}</span>
      </div>
      ${{d.reasoning ? '<div class="reasoning">' + d.reasoning + '</div>' : ''}}
    `;
    tooltip.style.display = 'block';
  }});

  cell.addEventListener('mousemove', (e) => {{
    let left = e.clientX + 16;
    let top = e.clientY + 16;
    const tw = tooltip.offsetWidth;
    const th = tooltip.offsetHeight;
    if (left + tw > window.innerWidth - 10) left = e.clientX - tw - 16;
    if (top + th > window.innerHeight - 10) top = e.clientY - th - 16;
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
  }});

  cell.addEventListener('mouseleave', () => {{
    tooltip.style.display = 'none';
  }});

  container.appendChild(cell);
}});

// Handle resize
window.addEventListener('resize', () => location.reload());
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
