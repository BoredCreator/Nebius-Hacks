"""Stub - teammate 4 will replace this with real agent execution."""


def run_agents(app_name, test_cases, personas, scan_dir):
    """Stub - returns dummy report."""
    print("Running agents... (stubbed)")
    return {
        "total_tests": len(test_cases),
        "passed": len(test_cases) - 1,
        "failed": 1,
        "report_path": f"{scan_dir}/reports/report.json",
    }
