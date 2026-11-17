#!/usr/bin/python3
"""
    Report Generator — Builds the morning markdown report and HTML dashboard.
    Reads applied_jobs.json and calculates all metrics.
    Generates reports/report_YYYYMMDD_HHMM.md
    Generates dashboard/dashboard.html
    Author: Fortune Nwohiri
"""
import json
import os
from datetime import datetime
from pathlib import Path
from collections import Counter
from logging_config.logger import get_logger

logger = get_logger("ReportGenerator")

REPORTS_DIR = "./reports"
DASHBOARD_DIR = "./dashboard"
STATE_PATH = "./state/applied_jobs.json"


def load_state(state_path: str = STATE_PATH) -> dict:
    if not os.path.exists(state_path):
        return {"applied": [], "skipped": [], "failed": [], "manual_queue": []}
    with open(state_path, "r") as f:
        return json.load(f)


def calculate_metrics(state: dict) -> dict:
    applied = state.get("applied", [])
    skipped = state.get("skipped", [])
    failed = state.get("failed", [])
    manual = state.get("manual_queue", [])

    total_processed = len(applied) + len(skipped) + len(failed) + len(manual)

    # Score distribution
    scores = [a.get("score", 0) for a in applied]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    high_score = max(scores) if scores else 0
    low_score = min(scores) if scores else 0

    # Platform breakdown
    platform_counts = Counter(a.get("platform", "Unknown") for a in applied)

    # Role type breakdown
    role_type_counts = Counter(a.get("role_type", "other") for a in applied)

    # Apply method breakdown
    method_counts = Counter(a.get("apply_method", "unknown") for a in applied)

    # Failure reasons
    failure_reasons = Counter(
        f.get("failure_reason") or f.get("skip_reason") or "unknown"
        for f in failed
    )

    # Skip reasons
    skip_reasons = Counter(
        s.get("skip_reason") or "unknown"
        for s in skipped
    )

    # Cover letter and custom question stats
    had_cover_letter = sum(1 for a in applied if a.get("had_cover_letter"))
    had_custom_questions = sum(1 for a in applied if a.get("had_custom_questions"))

    # Honeypots detected across all applications
    total_honeypots = sum(
        a.get("honeypots_detected", 0)
        for a in applied + failed
    )

    # Applications by date
    by_date = Counter(a.get("date", "unknown") for a in applied)

    # Must haves gap analysis
    all_gaps = []
    for a in applied:
        gap = a.get("cv_gap_report", "")
        if gap and gap.lower() not in ["none", ""]:
            all_gaps.append(gap)

    # Manual queue — failed applications with links
    manual_with_links = [
        {
            "title": m.get("title", "Unknown"),
            "company": m.get("company", "Unknown"),
            "url": m.get("url", ""),
            "reason": m.get("reason", ""),
            "score": m.get("score", 0),
            "timestamp": m.get("timestamp", ""),
        }
        for m in manual
    ]

    # Failed with links for reapplication
    failed_with_links = [
        {
            "title": f.get("title", "Unknown"),
            "company": f.get("company", "Unknown"),
            "url": f.get("url", ""),
            "reason": f.get("failure_reason") or f.get("skip_reason") or "unknown",
            "score": f.get("score", 0),
            "timestamp": f.get("timestamp", ""),
        }
        for f in failed
        if f.get("url")
    ]

    return {
        "total_applied": len(applied),
        "total_skipped": len(skipped),
        "total_failed": len(failed),
        "total_manual_queue": len(manual),
        "total_processed": total_processed,
        "avg_score": avg_score,
        "high_score": high_score,
        "low_score": low_score,
        "platform_counts": dict(platform_counts),
        "role_type_counts": dict(role_type_counts),
        "method_counts": dict(method_counts),
        "failure_reasons": dict(failure_reasons),
        "skip_reasons": dict(skip_reasons),
        "had_cover_letter": had_cover_letter,
        "had_custom_questions": had_custom_questions,
        "total_honeypots": total_honeypots,
        "by_date": dict(by_date),
        "manual_with_links": manual_with_links,
        "failed_with_links": failed_with_links,
        "all_gaps": all_gaps,
        "applied_list": applied,
        "failed_list": failed,
    }


def generate_markdown_report(metrics: dict, session_summary: dict = None) -> str:
    """Generate the morning markdown report."""
    Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    filename = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.md"
    filepath = os.path.join(REPORTS_DIR, filename)

    lines = [
        "# Job Application Agent — Session Report",
        f"**Generated:** {now}",
        "",
        "## Summary",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total Applied | {metrics['total_applied']} |",
        f"| Total Skipped | {metrics['total_skipped']} |",
        f"| Total Failed | {metrics['total_failed']} |",
        f"| Manual Queue | {metrics['total_manual_queue']} |",
        f"| Total Processed | {metrics['total_processed']} |",
        f"| Avg Score | {metrics['avg_score']}/100 |",
        f"| Honeypots Avoided | {metrics['total_honeypots']} |",
        "",
    ]

    if session_summary:
        lines += [
            "## This Session",
            f"- Applied: {session_summary.get('applied_count', 0)}",
            f"- Skipped: {session_summary.get('skipped_count', 0)}",
            f"- Failed: {session_summary.get('failed_count', 0)}",
            f"- Manual Queue: {session_summary.get('manual_queue_count', 0)}",
            "",
        ]

    if metrics["platform_counts"]:
        lines += ["## Applications by Platform", ""]
        for platform, count in sorted(
            metrics["platform_counts"].items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"- {platform}: {count}")
        lines.append("")

    if metrics["applied_list"]:
        lines += ["## Applied", ""]
        for job in metrics["applied_list"]:
            lines.append(
                f"- **{job.get('title', 'Unknown')}** @ {job.get('company', 'Unknown')} "
                f"| {job.get('platform', '')} | Score: {job.get('score', 0)}/100 "
                f"| Method: {job.get('apply_method', '')} "
                f"| Cover letter: {'Yes' if job.get('had_cover_letter') else 'No'}"
            )
            lines.append(f"  {job.get('url', '')}")
            if job.get("cv_gap_report") and job["cv_gap_report"].lower() not in ["none", ""]:
                lines.append(f"  Gaps: {job['cv_gap_report']}")
            lines.append("")

    if metrics["failed_with_links"]:
        lines += ["## Failed — Reapply Manually", ""]
        for job in metrics["failed_with_links"]:
            lines.append(
                f"- **{job['title']}** @ {job['company']} "
                f"| Score: {job['score']}/100 "
                f"| Reason: {job['reason']}"
            )
            lines.append(f"  {job['url']}")
            lines.append("")

    if metrics["manual_with_links"]:
        lines += ["## Manual Queue — Bot Could Not Apply", ""]
        for job in metrics["manual_with_links"]:
            lines.append(
                f"- **{job['title']}** @ {job['company']} "
                f"| Score: {job['score']}/100 "
                f"| Reason: {job['reason']}"
            )
            lines.append(f"  {job['url']}")
            lines.append("")

    if metrics["failure_reasons"]:
        lines += ["## Failure Reasons", ""]
        for reason, count in sorted(
            metrics["failure_reasons"].items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"- {reason}: {count}")
        lines.append("")

    content = "\n".join(lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Markdown report saved: {filepath}")
    return filepath


def generate_html_dashboard(metrics: dict) -> str:
    """
    Generate the HTML dashboard file.
    Saved to dashboard/dashboard.html.
    Launch with: python dashboard.py
    """
    Path(DASHBOARD_DIR).mkdir(parents=True, exist_ok=True)
    filepath = os.path.join(DASHBOARD_DIR, "dashboard.html")

    platform_labels = list(metrics["platform_counts"].keys()) or ["None"]
    platform_values = list(metrics["platform_counts"].values()) or [0]

    role_labels = list(metrics["role_type_counts"].keys()) or ["None"]
    role_values = list(metrics["role_type_counts"].values()) or [0]

    date_labels = sorted(k for k in metrics["by_date"].keys() if k and k != "None") or ["None"]
    date_values = [metrics["by_date"][d] for d in date_labels] or [0]

    failure_rows = ""
    for job in metrics["failed_with_links"]:
        failure_rows += f"""
        <tr>
            <td>{job['title']}</td>
            <td>{job['company']}</td>
            <td>{job['score']}</td>
            <td><span class="badge badge-fail">{job['reason']}</span></td>
            <td><a href="{job['url']}" target="_blank" class="reapply-btn">Reapply</a></td>
            <td>{job['timestamp'][:10] if job.get('timestamp') else ''}</td>
        </tr>
        """

    manual_rows = ""
    for job in metrics["manual_with_links"]:
        manual_rows += f"""
        <tr>
            <td>{job['title']}</td>
            <td>{job['company']}</td>
            <td>{job['score']}</td>
            <td><span class="badge badge-manual">{job['reason']}</span></td>
            <td><a href="{job['url']}" target="_blank" class="reapply-btn">Apply</a></td>
            <td>{job['timestamp'][:10] if job.get('timestamp') else ''}</td>
        </tr>
        """

    applied_rows = ""
    for job in metrics["applied_list"]:
        gap = job.get("cv_gap_report", "None") or "None"
        gap_display = gap if gap.lower() != "none" else ""
        applied_rows += f"""
        <tr>
            <td>{job.get('title', 'Unknown')}</td>
            <td>{job.get('company', 'Unknown')}</td>
            <td>{job.get('platform', '')}</td>
            <td>{job.get('score', 0)}</td>
            <td>{job.get('apply_method', '')}</td>
            <td>{'Yes' if job.get('had_cover_letter') else 'No'}</td>
            <td>{'Yes' if job.get('had_custom_questions') else 'No'}</td>
            <td class="gap-text">{gap_display}</td>
            <td><a href="{job.get('url', '')}" target="_blank">View</a></td>
            <td>{job.get('date', '')}</td>
        </tr>
        """

    skip_reason_rows = ""
    for reason, count in sorted(
        metrics["skip_reasons"].items(), key=lambda x: x[1], reverse=True
    ):
        skip_reason_rows += f"""
        <tr>
            <td>{reason}</td>
            <td>{count}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Application Dashboard — Fortune Nwohiri</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {{
            --bg: #0f1117;
            --surface: #1a1d27;
            --surface2: #22263a;
            --border: #2e3250;
            --text: #e8eaf0;
            --text-muted: #8b92b8;
            --accent: #6c63ff;
            --accent2: #00d4aa;
            --success: #22c55e;
            --fail: #ef4444;
            --warn: #f59e0b;
            --manual: #8b5cf6;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 14px;
            line-height: 1.6;
        }}

        .header {{
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 20px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .header h1 {{
            font-size: 20px;
            font-weight: 700;
            color: var(--text);
        }}

        .header .subtitle {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
        }}

        .generated-at {{
            font-size: 12px;
            color: var(--text-muted);
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}

        .stat-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}

        .stat-card .value {{
            font-size: 36px;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 6px;
        }}

        .stat-card .label {{
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .stat-applied {{ border-top: 3px solid var(--success); }}
        .stat-applied .value {{ color: var(--success); }}
        .stat-failed {{ border-top: 3px solid var(--fail); }}
        .stat-failed .value {{ color: var(--fail); }}
        .stat-skipped {{ border-top: 3px solid var(--warn); }}
        .stat-skipped .value {{ color: var(--warn); }}
        .stat-manual {{ border-top: 3px solid var(--manual); }}
        .stat-manual .value {{ color: var(--manual); }}
        .stat-processed {{ border-top: 3px solid var(--accent); }}
        .stat-processed .value {{ color: var(--accent); }}
        .stat-score {{ border-top: 3px solid var(--accent2); }}
        .stat-score .value {{ color: var(--accent2); }}
        .stat-honeypot {{ border-top: 3px solid #ec4899; }}
        .stat-honeypot .value {{ color: #ec4899; }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }}

        .chart-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
        }}

        .chart-card h3 {{
            font-size: 14px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 20px;
        }}

        .chart-wrapper {{
            position: relative;
            height: 220px;
        }}

        .section {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }}

        .section h2 {{
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .section-badge {{
            background: var(--surface2);
            border-radius: 20px;
            padding: 2px 10px;
            font-size: 12px;
            color: var(--text-muted);
        }}

        .table-wrapper {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}

        th {{
            text-align: left;
            padding: 10px 12px;
            color: var(--text-muted);
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
        }}

        td {{
            padding: 12px;
            border-bottom: 1px solid var(--border);
            vertical-align: top;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background: var(--surface2);
        }}

        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }}

        .badge-fail {{ background: rgba(239,68,68,0.15); color: var(--fail); }}
        .badge-manual {{ background: rgba(139,92,246,0.15); color: var(--manual); }}
        .badge-success {{ background: rgba(34,197,94,0.15); color: var(--success); }}

        .reapply-btn {{
            display: inline-block;
            background: var(--accent);
            color: white;
            padding: 4px 12px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }}

        .reapply-btn:hover {{
            background: #5a52e0;
        }}

        a {{
            color: var(--accent);
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        .gap-text {{
            color: var(--warn);
            font-size: 12px;
            max-width: 200px;
        }}

        .empty-state {{
            text-align: center;
            padding: 40px;
            color: var(--text-muted);
            font-size: 13px;
        }}

        .tabs {{
            display: flex;
            gap: 4px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0;
        }}

        .tab {{
            padding: 8px 16px;
            border-radius: 6px 6px 0 0;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            color: var(--text-muted);
            border: 1px solid transparent;
            border-bottom: none;
            margin-bottom: -1px;
            background: none;
        }}

        .tab.active {{
            color: var(--text);
            background: var(--surface);
            border-color: var(--border);
            border-bottom-color: var(--surface);
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        @media (max-width: 768px) {{
            .container {{ padding: 16px; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .charts-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>

<div class="header">
    <div>
        <h1>Job Application Dashboard</h1>
        <div class="subtitle">Fortune Nwohiri — Agent Overview</div>
    </div>
    <div class="generated-at">Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</div>
</div>

<div class="container">

    <!-- Stats Grid -->
    <div class="stats-grid">
        <div class="stat-card stat-applied">
            <div class="value">{metrics['total_applied']}</div>
            <div class="label">Applied</div>
        </div>
        <div class="stat-card stat-failed">
            <div class="value">{metrics['total_failed']}</div>
            <div class="label">Failed</div>
        </div>
        <div class="stat-card stat-skipped">
            <div class="value">{metrics['total_skipped']}</div>
            <div class="label">Skipped</div>
        </div>
        <div class="stat-card stat-manual">
            <div class="value">{metrics['total_manual_queue']}</div>
            <div class="label">Manual Queue</div>
        </div>
        <div class="stat-card stat-processed">
            <div class="value">{metrics['total_processed']}</div>
            <div class="label">Total Processed</div>
        </div>
        <div class="stat-card stat-score">
            <div class="value">{metrics['avg_score']}</div>
            <div class="label">Avg Score</div>
        </div>
        <div class="stat-card stat-honeypot">
            <div class="value">{metrics['total_honeypots']}</div>
            <div class="label">Honeypots Avoided</div>
        </div>
    </div>

    <!-- Charts -->
    <div class="charts-grid">
        <div class="chart-card">
            <h3>Applications by Platform</h3>
            <div class="chart-wrapper">
                <canvas id="platformChart"></canvas>
            </div>
        </div>
        <div class="chart-card">
            <h3>Role Types Applied</h3>
            <div class="chart-wrapper">
                <canvas id="roleChart"></canvas>
            </div>
        </div>
        <div class="chart-card">
            <h3>Applications Over Time</h3>
            <div class="chart-wrapper">
                <canvas id="timelineChart"></canvas>
            </div>
        </div>
        <div class="chart-card">
            <h3>Application Status Breakdown</h3>
            <div class="chart-wrapper">
                <canvas id="statusChart"></canvas>
            </div>
        </div>
    </div>

    <!-- Tabs -->
    <div class="section">
        <div class="tabs">
            <button class="tab active" onclick="showTab('applied')">
                Applied <span class="section-badge">{metrics['total_applied']}</span>
            </button>
            <button class="tab" onclick="showTab('failed')">
                Failed <span class="section-badge">{metrics['total_failed']}</span>
            </button>
            <button class="tab" onclick="showTab('manual')">
                Manual Queue <span class="section-badge">{metrics['total_manual_queue']}</span>
            </button>
            <button class="tab" onclick="showTab('skips')">
                Skip Reasons
            </button>
        </div>

        <!-- Applied Tab -->
        <div id="tab-applied" class="tab-content active">
            {'<div class="table-wrapper"><table><thead><tr><th>Title</th><th>Company</th><th>Platform</th><th>Score</th><th>Method</th><th>Cover Letter</th><th>Custom Q</th><th>Gaps</th><th>Link</th><th>Date</th></tr></thead><tbody>' + applied_rows + '</tbody></table></div>' if applied_rows else '<div class="empty-state">No applications yet.</div>'}
        </div>

        <!-- Failed Tab -->
        <div id="tab-failed" class="tab-content">
            {'<div class="table-wrapper"><table><thead><tr><th>Title</th><th>Company</th><th>Score</th><th>Reason</th><th>Reapply</th><th>Date</th></tr></thead><tbody>' + failure_rows + '</tbody></table></div>' if failure_rows else '<div class="empty-state">No failed applications.</div>'}
        </div>

        <!-- Manual Queue Tab -->
        <div id="tab-manual" class="tab-content">
            {'<div class="table-wrapper"><table><thead><tr><th>Title</th><th>Company</th><th>Score</th><th>Reason</th><th>Apply</th><th>Date</th></tr></thead><tbody>' + manual_rows + '</tbody></table></div>' if manual_rows else '<div class="empty-state">No manual queue items.</div>'}
        </div>

        <!-- Skip Reasons Tab -->
        <div id="tab-skips" class="tab-content">
            {'<div class="table-wrapper"><table><thead><tr><th>Reason</th><th>Count</th></tr></thead><tbody>' + skip_reason_rows + '</tbody></table></div>' if skip_reason_rows else '<div class="empty-state">No skips recorded.</div>'}
        </div>
    </div>

</div>

<script>
    // Tab switching
    function showTab(name) {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        document.getElementById('tab-' + name).classList.add('active');
        event.target.classList.add('active');
    }}

    const chartDefaults = {{
        plugins: {{
            legend: {{
                labels: {{ color: '#8b92b8', font: {{ size: 12 }} }}
            }}
        }},
        scales: {{
            x: {{ ticks: {{ color: '#8b92b8' }}, grid: {{ color: '#2e3250' }} }},
            y: {{ ticks: {{ color: '#8b92b8' }}, grid: {{ color: '#2e3250' }} }}
        }}
    }};

    // Platform chart
    new Chart(document.getElementById('platformChart'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(platform_labels)},
            datasets: [{{
                label: 'Applications',
                data: {json.dumps(platform_values)},
                backgroundColor: '#6c63ff',
                borderRadius: 6,
            }}]
        }},
        options: {{ ...chartDefaults, responsive: true, maintainAspectRatio: false }}
    }});

    // Role type chart
    new Chart(document.getElementById('roleChart'), {{
        type: 'doughnut',
        data: {{
            labels: {json.dumps(role_labels)},
            datasets: [{{
                data: {json.dumps(role_values)},
                backgroundColor: ['#6c63ff','#00d4aa','#f59e0b','#ef4444','#8b5cf6','#22c55e','#ec4899','#3b82f6'],
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ labels: {{ color: '#8b92b8', font: {{ size: 11 }} }} }}
            }}
        }}
    }});

    // Timeline chart
    new Chart(document.getElementById('timelineChart'), {{
        type: 'line',
        data: {{
            labels: {json.dumps(date_labels)},
            datasets: [{{
                label: 'Applications',
                data: {json.dumps(date_values)},
                borderColor: '#00d4aa',
                backgroundColor: 'rgba(0,212,170,0.1)',
                borderWidth: 2,
                pointRadius: 4,
                fill: true,
                tension: 0.4,
            }}]
        }},
        options: {{ ...chartDefaults, responsive: true, maintainAspectRatio: false }}
    }});

    // Status breakdown chart
    new Chart(document.getElementById('statusChart'), {{
        type: 'doughnut',
        data: {{
            labels: ['Applied', 'Skipped', 'Failed', 'Manual Queue'],
            datasets: [{{
                data: [{metrics['total_applied']}, {metrics['total_skipped']}, {metrics['total_failed']}, {metrics['total_manual_queue']}],
                backgroundColor: ['#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'],
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ labels: {{ color: '#8b92b8', font: {{ size: 12 }} }} }}
            }}
        }}
    }});
</script>

</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Dashboard saved: {filepath}")
    return filepath


def generate(session_summary: dict = None) -> dict:
    """
    Master function. Called at the end of every agent run.
    Loads state, calculates metrics, generates markdown report
    and HTML dashboard.

    Returns dict with paths to both files.
    """
    state = load_state()
    metrics = calculate_metrics(state)

    report_path = generate_markdown_report(metrics, session_summary)
    dashboard_path = generate_html_dashboard(metrics)

    logger.info(f"Report: {report_path}")
    logger.info(f"Dashboard: {dashboard_path}")

    return {
        "report_path": report_path,
        "dashboard_path": dashboard_path,
        "metrics": metrics,
    }