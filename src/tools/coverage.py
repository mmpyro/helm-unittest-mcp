import os
import re
import yaml
from typing import Optional
from utils.mcp import Server
from utils.dtos import TemplateCoverage, CoverageReport


mcp = Server().mcp


def _is_manifest_template(filename: str) -> bool:
    """Check if a file is a testable Kubernetes manifest template.

    Excludes partial templates starting with '_' and NOTES.txt by default.
    """
    if filename.startswith("_") or filename.lower() == "notes.txt":
        return False
    return filename.endswith((".yaml", ".yml", ".tpl"))


def _normalize_template_ref(ref: str) -> str:
    """Normalize a template path reference from a test file."""
    ref = ref.strip().lstrip("/")
    if ref.startswith("templates/"):
        ref = ref[len("templates/"):]
    return ref


@mcp.tool()
def get_test_coverage(
    chart_path: str,
    tests_dir: str = "tests",
    pattern: Optional[str] = "",
    with_subcharts: bool = False,
) -> CoverageReport:
    """Analyze a Helm chart to determine unit test coverage across its template files.

    Scans the chart's template files and cross-references them against all test suites
    to calculate coverage percentage and identify untested templates.

    Args:
        chart_path (str): Path to the Helm chart root directory
        tests_dir (str): Relative path from chart root to tests directory (default "tests")
        pattern (str, optional): Regex pattern to filter test suite files
        with_subcharts (bool): Whether to include subcharts in the coverage calculation (default False)

    Returns:
        CoverageReport: Summary of tested and untested templates with percentage coverage.
    """
    if not os.path.exists(chart_path):
        raise FileNotFoundError(f"Chart directory not found: {chart_path}")

    templates_dir = os.path.join(chart_path, "templates")
    if not os.path.isdir(templates_dir):
        return CoverageReport(
            chart_path=chart_path,
            total_templates=0,
            tested_templates=0,
            untested_templates=0,
            coverage_percentage=100.0,
            template_details=[],
            untested_template_paths=[],
        )

    # 1. Discover all manifest template files
    discovered_templates: list[str] = []
    for root, _, files in os.walk(templates_dir):
        for f in files:
            if _is_manifest_template(f):
                full_path = os.path.join(root, f)
                rel_to_templates = os.path.relpath(full_path, templates_dir)
                discovered_templates.append(rel_to_templates)

    # If with_subcharts, also scan charts/*/templates
    if with_subcharts:
        charts_dir = os.path.join(chart_path, "charts")
        if os.path.isdir(charts_dir):
            for subchart in os.listdir(charts_dir):
                sub_tpl_dir = os.path.join(charts_dir, subchart, "templates")
                if os.path.isdir(sub_tpl_dir):
                    for root, _, files in os.walk(sub_tpl_dir):
                        for f in files:
                            if _is_manifest_template(f):
                                full_path = os.path.join(root, f)
                                rel_to_chart = os.path.relpath(full_path, chart_path)
                                discovered_templates.append(rel_to_chart)

    # 2. Discover and parse all test files
    full_tests_dir = os.path.join(chart_path, tests_dir)
    file_pattern = re.compile(pattern) if pattern else re.compile(r".*\.ya?ml$", re.IGNORECASE)

    # Mapping: normalized_template_name -> {"files": set(), "suites": set()}
    template_coverage_map: dict[str, dict[str, set[str]]] = {
        tpl: {"files": set(), "suites": set()} for tpl in discovered_templates
    }

    if os.path.isdir(full_tests_dir):
        for root, _, files in os.walk(full_tests_dir):
            for filename in files:
                if file_pattern.match(filename):
                    test_file_path = os.path.join(root, filename)
                    try:
                        with open(test_file_path, "r", encoding="utf-8") as tf:
                            test_doc = yaml.safe_load(tf)

                        if not isinstance(test_doc, dict):
                            continue

                        suite_name = test_doc.get("suite", filename)
                        rel_test_path = os.path.relpath(test_file_path, chart_path)

                        # Check suite-level templates
                        suite_templates = test_doc.get("templates", [])
                        if isinstance(suite_templates, str):
                            suite_templates = [suite_templates]

                        # Check test-level templates
                        tests_list = test_doc.get("tests", [])
                        test_level_templates = []
                        if isinstance(tests_list, list):
                            for t in tests_list:
                                if isinstance(t, dict) and "template" in t:
                                    tpl_val = t["template"]
                                    if isinstance(tpl_val, str):
                                        test_level_templates.append(tpl_val)

                        all_referenced = list(suite_templates) + test_level_templates

                        for ref in all_referenced:
                            norm_ref = _normalize_template_ref(ref)
                            # Match against discovered templates
                            for disc_tpl in discovered_templates:
                                norm_disc = _normalize_template_ref(disc_tpl)
                                # Check exact or wildcard/basename match
                                if norm_ref == norm_disc or norm_ref == os.path.basename(norm_disc) or norm_ref == "*":
                                    template_coverage_map[disc_tpl]["files"].add(rel_test_path)
                                    template_coverage_map[disc_tpl]["suites"].add(suite_name)
                    except Exception:
                        continue

    # 3. Assemble report
    details: list[TemplateCoverage] = []
    untested_paths: list[str] = []
    tested_count = 0

    for tpl in sorted(discovered_templates):
        info = template_coverage_map[tpl]
        is_tested = len(info["files"]) > 0
        if is_tested:
            tested_count += 1
        else:
            untested_paths.append(tpl)

        details.append(
            TemplateCoverage(
                template_path=tpl,
                tested=is_tested,
                test_files=sorted(list(info["files"])),
                test_suites=sorted(list(info["suites"])),
            )
        )

    total_count = len(discovered_templates)
    pct = round((tested_count / total_count) * 100.0, 2) if total_count > 0 else 100.0

    return CoverageReport(
        chart_path=chart_path,
        total_templates=total_count,
        tested_templates=tested_count,
        untested_templates=total_count - tested_count,
        coverage_percentage=pct,
        template_details=details,
        untested_template_paths=untested_paths,
    )
