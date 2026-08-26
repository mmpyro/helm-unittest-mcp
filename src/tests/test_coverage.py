import os
import yaml
import pytest
from tools.coverage import get_test_coverage, _normalize_template_ref, _is_manifest_template
from utils.dtos import CoverageReport


def test_normalize_template_ref():
    assert _normalize_template_ref("templates/deployment.yaml") == "deployment.yaml"
    assert _normalize_template_ref("/deployment.yaml") == "deployment.yaml"
    assert _normalize_template_ref("service.yaml") == "service.yaml"


def test_is_manifest_template():
    assert _is_manifest_template("deployment.yaml") is True
    assert _is_manifest_template("service.yml") is True
    assert _is_manifest_template("_helpers.tpl") is False
    assert _is_manifest_template("NOTES.txt") is False


def test_get_test_coverage_chart_not_found():
    with pytest.raises(FileNotFoundError, match="Chart directory not found"):
        get_test_coverage("/nonexistent/path")


def test_get_test_coverage_no_templates_dir(tmp_path):
    empty_chart = tmp_path / "empty-chart"
    empty_chart.mkdir()
    report = get_test_coverage(str(empty_chart))
    assert isinstance(report, CoverageReport)
    assert report.total_templates == 0
    assert report.coverage_percentage == 100.0


def test_get_test_coverage_calculation(tmp_path):
    chart_dir = tmp_path / "test-chart"
    chart_dir.mkdir()
    templates_dir = chart_dir / "templates"
    templates_dir.mkdir()
    tests_dir = chart_dir / "tests"
    tests_dir.mkdir()

    # Create 3 templates: 2 manifests, 1 partial helper
    (templates_dir / "deployment.yaml").write_text("apiVersion: apps/v1")
    (templates_dir / "service.yaml").write_text("apiVersion: v1")
    (templates_dir / "_helpers.tpl").write_text("{{/* helper */}}")

    # Create 1 test file covering only deployment.yaml
    test_yaml = tests_dir / "deployment_test.yaml"
    test_yaml.write_text(
        yaml.dump(
            {
                "suite": "deployment suite",
                "templates": ["deployment.yaml"],
                "tests": [{"it": "should work"}],
            }
        )
    )

    report = get_test_coverage(str(chart_dir))
    assert report.total_templates == 2
    assert report.tested_templates == 1
    assert report.untested_templates == 1
    assert report.coverage_percentage == 50.0
    assert "service.yaml" in report.untested_template_paths
    assert "deployment.yaml" not in report.untested_template_paths


def test_get_test_coverage_example_chart():
    # Test on the workspace example chart
    chart_path = os.path.abspath("example")
    if os.path.exists(chart_path):
        report = get_test_coverage(chart_path, tests_dir="tests")
        assert isinstance(report, CoverageReport)
        assert report.total_templates >= 5
        assert report.coverage_percentage == 100.0
        assert len(report.untested_template_paths) == 0
