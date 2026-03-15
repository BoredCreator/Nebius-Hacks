"""
Generates the final test report from all execution results.
Outputs both JSON and Markdown reports.
"""

import json
import os
from datetime import datetime


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------

def generate_report(execution_results: list[dict], app_name: str,
                    scan_dir: str) -> dict:
    """Aggregate all test results into a final report and save JSON."""
    total = len(execution_results)
    passed = sum(1 for r in execution_results if r["status"] == "PASS")
    failed = sum(1 for r in execution_results if r["status"] == "FAIL")
    errors = sum(1 for r in execution_results if r["status"] == "ERROR")
    skipped = sum(1 for r in execution_results if r["status"] == "SKIPPED")

    # Collect all bugs
    all_bugs: list[dict] = []
    for result in execution_results:
        for step in result.get("step_results", []):
            if "bug" in step:
                bug = dict(step["bug"])
                bug["found_by_persona"] = result.get("persona_name", "Unknown")
                bug["test_id"] = result["test_id"]
                all_bugs.append(bug)

    # Count severities
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for bug in all_bugs:
        sev = bug.get("severity", "medium")
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Per-persona breakdown
    persona_breakdown: dict = {}
    for result in execution_results:
        pid = result.get("persona_id", "unknown")
        if pid not in persona_breakdown:
            persona_breakdown[pid] = {
                "persona_name": result.get("persona_name", pid),
                "tests": 0, "passed": 0, "failed": 0, "errors": 0, "bugs_found": 0,
            }
        persona_breakdown[pid]["tests"] += 1
        if result["status"] == "PASS":
            persona_breakdown[pid]["passed"] += 1
        elif result["status"] == "FAIL":
            persona_breakdown[pid]["failed"] += 1
        elif result["status"] == "ERROR":
            persona_breakdown[pid]["errors"] += 1
        persona_breakdown[pid]["bugs_found"] += len(result.get("bugs_found", []))

    # Total duration
    total_duration = sum(r.get("duration_seconds", 0) for r in execution_results)

    # Recommendations
    recommendations = _generate_recommendations(all_bugs)

    pass_rate = f"{(passed / total * 100):.1f}%" if total > 0 else "N/A"

    report = {
        "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "app_name": app_name,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "pass_rate": pass_rate,
            "total_bugs": len(all_bugs),
            "critical_bugs": severity_counts["critical"],
            "high_bugs": severity_counts["high"],
            "medium_bugs": severity_counts["medium"],
            "low_bugs": severity_counts["low"],
            "total_duration_seconds": round(total_duration, 2),
        },
        "bugs": all_bugs,
        "persona_breakdown": persona_breakdown,
        "test_results": execution_results,
        "recommendations": recommendations,
        # Keep legacy keys so cli.py can read them
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "report_path": os.path.join(scan_dir, "reports", "report.json"),
    }

    # Save JSON
    reports_dir = os.path.join(scan_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    json_path = os.path.join(reports_dir, "report.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    return report


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def generate_markdown_report(report: dict, output_path: str) -> str:
    """Generate a human-readable markdown report."""
    s = report["summary"]
    lines: list[str] = []

    lines.append(f"# AppGhost Test Report: {report['app_name']}")
    lines.append(f"**Generated:** {report['generated_at']}")
    lines.append(f"**Report ID:** {report['report_id']}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Tests | {s['total_tests']} |")
    lines.append(f"| Passed | {s['passed']} ({s['pass_rate']}) |")
    lines.append(f"| Failed | {s['failed']} |")
    lines.append(f"| Errors | {s['errors']} |")
    lines.append(f"| Skipped | {s['skipped']} |")
    lines.append(f"| Total Bugs | {s['total_bugs']} |")
    lines.append(f"| Duration | {s['total_duration_seconds']}s |")
    lines.append("")

    # Bugs section
    bugs = report.get("bugs", [])
    if bugs:
        lines.append(f"## Bugs Found ({len(bugs)})")
        lines.append("")

        for severity in ["critical", "high", "medium", "low"]:
            sev_bugs = [b for b in bugs if b.get("severity") == severity]
            if not sev_bugs:
                continue
            label = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}[severity]
            lines.append(f"### {label}")
            for bug in sev_bugs:
                lines.append(f"- **{bug.get('title', 'Untitled')}**")
                lines.append(f"  - ID: `{bug.get('bug_id', 'N/A')}`")
                lines.append(f"  - Found by: {bug.get('found_by_persona', 'Unknown')}")
                lines.append(f"  - Test: `{bug.get('test_id', 'N/A')}`")
                if bug.get("description"):
                    lines.append(f"  - {bug['description']}")
                if bug.get("reproduction_steps"):
                    lines.append("  - **Reproduction:**")
                    for step in bug["reproduction_steps"]:
                        lines.append(f"    - {step}")
                if bug.get("screenshot"):
                    lines.append(f"  - Screenshot: `{bug['screenshot']}`")
                lines.append("")
    else:
        lines.append("## Bugs Found")
        lines.append("No bugs detected.")
        lines.append("")

    # Persona breakdown
    lines.append("## Persona Breakdown")
    lines.append("| Persona | Tests | Passed | Failed | Errors | Bugs |")
    lines.append("|---------|-------|--------|--------|--------|------|")
    for pid, info in report.get("persona_breakdown", {}).items():
        lines.append(
            f"| {info.get('persona_name', pid)} "
            f"| {info['tests']} "
            f"| {info['passed']} "
            f"| {info['failed']} "
            f"| {info.get('errors', 0)} "
            f"| {info['bugs_found']} |"
        )
    lines.append("")

    # Detailed test results
    lines.append("## Detailed Test Results")
    lines.append("")
    for result in report.get("test_results", []):
        status_icon = {"PASS": "PASS", "FAIL": "FAIL", "ERROR": "ERROR", "SKIPPED": "SKIP"}.get(result["status"], "?")
        lines.append(f"### [{status_icon}] {result.get('title', result['test_id'])}")
        lines.append(f"- **Test ID:** `{result['test_id']}`")
        lines.append(f"- **Persona:** {result.get('persona_name', 'Unknown')}")
        lines.append(f"- **Duration:** {result.get('duration_seconds', 0)}s")
        lines.append(f"- **Bugs:** {len(result.get('bugs_found', []))}")
        lines.append("")

        for step in result.get("step_results", []):
            s_icon = {"PASS": "ok", "FAIL": "FAIL", "ERROR": "ERR", "INCONCLUSIVE": "???"}.get(step["status"], "?")
            lines.append(f"  {step['step_number']}. [{s_icon}] `{step['action']}`")
            if step.get("target"):
                lines.append(f"     Target: {step['target']}")
            if step.get("expected"):
                lines.append(f"     Expected: {step['expected']}")
            if step.get("actual"):
                lines.append(f"     Actual: {step['actual']}")
            if step.get("llm_reasoning"):
                lines.append(f"     Reasoning: {step['llm_reasoning']}")
            lines.append("")

    # Recommendations
    recs = report.get("recommendations", [])
    if recs:
        lines.append("## Recommendations")
        for rec in recs:
            lines.append(f"- {rec}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by AppGhost*")

    md_content = "\n".join(lines)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(md_content)

    return md_content


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def _generate_recommendations(bugs: list[dict]) -> list[str]:
    """Generate prioritized recommendations from the bug list."""
    if not bugs:
        return ["No bugs detected — all tests passed."]

    recommendations: list[str] = []
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_bugs = sorted(bugs, key=lambda b: severity_order.get(b.get("severity", "medium"), 2))

    for bug in sorted_bugs:
        sev = bug.get("severity", "medium").capitalize()
        title = bug.get("title", "Unknown issue")
        recommendations.append(f"{sev}: {title}")

    # Try LLM-powered recommendations if API key is available
    api_key = os.environ.get("NEBIUS_API_KEY", "")
    if api_key and bugs:
        try:
            import requests
            import json as _json

            api_url = os.environ.get(
                "NEBIUS_API_URL",
                "https://api.studio.nebius.com/v1/chat/completions",
            )
            model = os.environ.get("NEBIUS_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")

            bug_summary = _json.dumps(
                [{"severity": b.get("severity"), "title": b.get("title"), "description": b.get("description")}
                 for b in sorted_bugs],
                default=str,
            )

            resp = requests.post(
                api_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a senior QA engineer. Given a list of bugs found in a macOS application, provide 3-5 concise, actionable fix recommendations sorted by priority. Return them as a JSON array of strings."},
                        {"role": "user", "content": bug_summary},
                    ],
                    "temperature": 0.2,
                },
                timeout=30,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            llm_recs = _json.loads(text.strip())
            if isinstance(llm_recs, list):
                recommendations = llm_recs
        except Exception:
            pass  # fall back to simple recommendations

    return recommendations
