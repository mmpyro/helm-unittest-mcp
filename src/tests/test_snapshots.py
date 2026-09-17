import os
import yaml
import pytest
from unittest.mock import patch
from tools.snapshots import (
    get_snapshots,
    diff_snapshot,
    clean_snapshots,
    _parse_snapshot_file,
)
from utils.dtos import SnapshotFile, SnapshotDiffResult, SnapshotCleanResult


def test_get_snapshots_chart_not_found():
    with pytest.raises(FileNotFoundError, match="Chart directory not found"):
        get_snapshots("/nonexistent/path")


def test_clean_snapshots_chart_not_found():
    with pytest.raises(FileNotFoundError, match="Chart directory not found"):
        clean_snapshots("/nonexistent/path")


def test_parse_and_get_snapshots(tmp_path):
    chart_dir = tmp_path / "my-chart"
    chart_dir.mkdir()
    tests_dir = chart_dir / "tests"
    tests_dir.mkdir()
    snap_dir = tests_dir / "__snapshot__"
    snap_dir.mkdir()

    # Create a test file and corresponding snap file
    test_yaml = tests_dir / "deploy_test.yaml"
    test_yaml.write_text(
        yaml.dump(
            {
                "suite": "deploy tests",
                "tests": [{"it": "should render deployment"}],
            }
        )
    )

    snap_file = snap_dir / "deploy_test.yaml.snap"
    snap_data = {
        "should render deployment 1": [
            "apiVersion: apps/v1\nkind: Deployment\n"
        ]
    }
    snap_file.write_text(yaml.dump(snap_data))

    snapshots = get_snapshots(str(chart_dir))
    assert len(snapshots) == 1
    assert isinstance(snapshots[0], SnapshotFile)
    assert not snapshots[0].is_orphaned
    assert len(snapshots[0].snapshots) == 1
    assert snapshots[0].snapshots[0].name == "should render deployment 1"

    # Test filtering by test_file_path
    single = get_snapshots(str(chart_dir), test_file_path=str(test_yaml))
    assert len(single) == 1


def test_orphaned_snapshot_detection_and_cleaning(tmp_path):
    chart_dir = tmp_path / "my-chart"
    chart_dir.mkdir()
    tests_dir = chart_dir / "tests"
    tests_dir.mkdir()
    snap_dir = tests_dir / "__snapshot__"
    snap_dir.mkdir()

    # Create an orphaned snap file without corresponding test YAML
    orphaned_snap = snap_dir / "old_test.yaml.snap"
    orphaned_snap.write_text("old test 1:\n  - content")

    # Also create active test with one active test and one obsolete snapshot entry
    active_test = tests_dir / "active_test.yaml"
    active_test.write_text(
        yaml.dump(
            {
                "suite": "active",
                "tests": [{"it": "current valid test"}],
            }
        )
    )
    active_snap = snap_dir / "active_test.yaml.snap"
    active_snap.write_text(
        yaml.dump(
            {
                "current valid test 1": "valid",
                "deleted test 1": "obsolete",
            }
        )
    )

    # 1. Dry run clean
    dry_res = clean_snapshots(str(chart_dir), dry_run=True)
    assert isinstance(dry_res, SnapshotCleanResult)
    assert dry_res.dry_run is True
    assert str(orphaned_snap) in dry_res.cleaned_files
    assert any("deleted test 1" in e for e in dry_res.cleaned_entries)
    assert os.path.exists(orphaned_snap)  # Not actually deleted

    # 2. Actual clean
    actual_res = clean_snapshots(str(chart_dir), dry_run=False)
    assert actual_res.dry_run is False
    assert not os.path.exists(orphaned_snap)  # Deleted

    # Verify active_snap now only contains active test
    with open(active_snap, "r") as f:
        cleaned_snap_data = yaml.safe_load(f)
    assert "current valid test 1" in cleaned_snap_data
    assert "deleted test 1" not in cleaned_snap_data


def test_diff_snapshot_missing_file(tmp_path):
    res = diff_snapshot(str(tmp_path), str(tmp_path / "tests" / "test.yaml"))
    assert isinstance(res, SnapshotDiffResult)
    assert res.exists is False
    assert res.has_diff is True


@patch("tools.snapshots.get_rendered_debug_output")
def test_diff_snapshot_matches_and_mismatches(mock_debug, tmp_path):
    chart_dir = tmp_path / "my-chart"
    chart_dir.mkdir()
    tests_dir = chart_dir / "tests"
    tests_dir.mkdir()
    snap_dir = tests_dir / "__snapshot__"
    snap_dir.mkdir()

    test_yaml = tests_dir / "app_test.yaml"
    test_yaml.write_text(yaml.dump({"suite": "s", "tests": [{"it": "it1"}]}))

    snap_file = snap_dir / "app_test.yaml.snap"
    snap_file.write_text("it1 1:\n  - apiVersion: v1\n    kind: Service\n")

    # Case 1: Match
    mock_debug.return_value = {
        "templates/service.yaml": "apiVersion: v1\nkind: Service\n"
    }
    match_res = diff_snapshot(str(chart_dir), str(test_yaml), "it1")
    assert match_res.exists is True
    assert match_res.has_diff is False

    # Case 2: Mismatch
    mock_debug.return_value = {
        "templates/service.yaml": "apiVersion: v1\nkind: Service\nmetadata:\n  name: changed\n"
    }
    mismatch_res = diff_snapshot(str(chart_dir), str(test_yaml), "it1")
    assert mismatch_res.exists is True
    assert mismatch_res.has_diff is True
    assert mismatch_res.diff is not None
    assert "-apiVersion: v1" in mismatch_res.diff or "+apiVersion: v1" in mismatch_res.diff or "changed" in mismatch_res.diff


def _chart_with_snapshot(tmp_path, snap_text):
    chart_dir = tmp_path / "my-chart"
    (chart_dir / "tests" / "__snapshot__").mkdir(parents=True)
    test_yaml = chart_dir / "tests" / "app_test.yaml"
    test_yaml.write_text(yaml.dump({"suite": "s", "tests": [{"it": "it1"}]}))
    (chart_dir / "tests" / "__snapshot__" / "app_test.yaml.snap").write_text(snap_text)
    return chart_dir, test_yaml


def test_get_snapshots_names_only_omits_bodies(tmp_path):
    chart_dir, test_yaml = _chart_with_snapshot(
        tmp_path, "it1 1:\n  - apiVersion: v1\n    kind: Service\n"
    )

    names_only = get_snapshots(str(chart_dir))
    assert names_only[0].snapshots[0].name == "it1 1"
    assert names_only[0].snapshots[0].content.startswith("<")
    assert names_only[0].snapshots[0].content.endswith("chars>")

    full = get_snapshots(str(chart_dir), names_only=False)
    assert "kind: Service" in full[0].snapshots[0].content


def test_get_snapshots_pagination(tmp_path):
    chart_dir = tmp_path / "chart"
    snap_dir = chart_dir / "tests" / "__snapshot__"
    snap_dir.mkdir(parents=True)
    for i in range(3):
        (snap_dir / f"s{i}_test.yaml.snap").write_text("a 1:\n  - kind: Service\n")

    assert len(get_snapshots(str(chart_dir))) == 3
    assert len(get_snapshots(str(chart_dir), limit=2)) == 2
    assert len(get_snapshots(str(chart_dir), offset=2)) == 1


@patch("tools.snapshots.get_rendered_debug_output")
def test_diff_snapshot_compares_entry_against_its_own_template(mock_debug, tmp_path):
    """A snapshot entry must be diffed against the manifest it came from.

    Previously every entry was diffed against the concatenation of all rendered
    templates, so an unchanged snapshot still reported a diff whenever the chart
    rendered more than one template.
    """
    chart_dir, test_yaml = _chart_with_snapshot(
        tmp_path, "it1 1:\n  - apiVersion: v1\n    kind: Service\n"
    )

    mock_debug.return_value = {
        "templates/service.yaml": "apiVersion: v1\nkind: Service\n",
        "templates/deployment.yaml": "apiVersion: apps/v1\nkind: Deployment\n",
    }

    res = diff_snapshot(str(chart_dir), str(test_yaml))
    assert res.has_diff is False


@patch("tools.snapshots.get_rendered_debug_output")
def test_diff_snapshot_reports_unmatched_entries(mock_debug, tmp_path):
    chart_dir, test_yaml = _chart_with_snapshot(
        tmp_path, "it1 1:\n  - apiVersion: v1\n    kind: Service\n"
    )
    mock_debug.return_value = {
        "templates/cm.yaml": "apiVersion: v1\nkind: ConfigMap\n",
    }

    res = diff_snapshot(str(chart_dir), str(test_yaml))
    assert res.has_diff is True
    assert "could not be matched" in res.message


@patch("tools.snapshots.get_rendered_debug_output")
def test_diff_snapshot_truncates(mock_debug, tmp_path):
    chart_dir, test_yaml = _chart_with_snapshot(
        tmp_path, "it1 1:\n  - apiVersion: v1\n    kind: Service\n"
    )
    mock_debug.return_value = {
        "templates/service.yaml": "apiVersion: v1\nkind: Service\nmetadata:\n  name: x\n"
    }

    res = diff_snapshot(str(chart_dir), str(test_yaml), max_chars=20)
    assert res.diff is not None
    assert "truncated" in res.diff
