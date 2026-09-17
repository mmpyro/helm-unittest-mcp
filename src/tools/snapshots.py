import os
import difflib
import yaml
from typing import Optional
from utils.mcp import Server, tool
from utils.dtos import (
    SnapshotFile,
    SnapshotEntry,
    SnapshotDiffResult,
    SnapshotCleanResult,
)
from tools.debug import get_rendered_debug_output


mcp = Server().mcp


def _parse_snapshot_file(snap_path: str, chart_path: str) -> SnapshotFile:
    """Parse a .snap YAML file and return a SnapshotFile DTO.

    Args:
        snap_path: Absolute or relative path to the .snap file
        chart_path: Root path to the Helm chart

    Returns:
        SnapshotFile object
    """
    # Infer test file path from snap path
    # e.g., tests/deployment/__snapshot__/deployment_example_test.yaml.snap -> tests/deployment/deployment_example_test.yaml
    parent_dir = os.path.dirname(snap_path)
    if os.path.basename(parent_dir) == "__snapshot__":
        test_dir = os.path.dirname(parent_dir)
        snap_filename = os.path.basename(snap_path)
        if snap_filename.endswith(".snap"):
            test_filename = snap_filename[:-5]
            test_file_path = os.path.join(test_dir, test_filename)
        else:
            test_file_path = os.path.join(test_dir, snap_filename)
    else:
        test_file_path = snap_path.removesuffix(".snap")

    is_orphaned = not os.path.exists(test_file_path)

    entries: list[SnapshotEntry] = []
    try:
        with open(snap_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict):
                for name, content in data.items():
                    if isinstance(content, list):
                        content_str = "\n---\n".join(
                            yaml.dump(c).strip() if isinstance(c, (dict, list)) else str(c).strip()
                            for c in content
                        )
                    elif isinstance(content, (dict, list)):
                        content_str = yaml.dump(content).strip()
                    else:
                        content_str = str(content).strip()
                    entries.append(SnapshotEntry(name=str(name), content=content_str))
    except Exception as e:
        entries.append(SnapshotEntry(name="__error__", content=f"Failed to parse snapshot: {e}"))

    return SnapshotFile(
        file_path=snap_path,
        test_file_path=test_file_path,
        snapshots=entries,
        is_orphaned=is_orphaned,
    )


@tool(read_only=True, idempotent=True)
def get_snapshots(
    chart_path: str,
    test_file_path: Optional[str] = None,
) -> list[SnapshotFile]:
    """Discover, parse, and return all snapshot files and entries in a Helm chart.

    Args:
        chart_path (str): Path to the Helm chart directory
        test_file_path (str, optional): If provided, returns snapshots specifically
                                        associated with this test file.

    Returns:
        list[SnapshotFile]: List of discovered snapshot files with their individual entries.
    """
    if not os.path.exists(chart_path):
        raise FileNotFoundError(f"Chart directory not found: {chart_path}")

    snapshot_files: list[SnapshotFile] = []

    if test_file_path:
        test_dir = os.path.dirname(test_file_path)
        test_filename = os.path.basename(test_file_path)
        snap_path = os.path.join(test_dir, "__snapshot__", f"{test_filename}.snap")
        if os.path.exists(snap_path):
            snapshot_files.append(_parse_snapshot_file(snap_path, chart_path))
        return snapshot_files

    for root, dirs, files in os.walk(chart_path):
        if os.path.basename(root) == "__snapshot__":
            for file in files:
                if file.endswith(".snap"):
                    full_snap_path = os.path.join(root, file)
                    snapshot_files.append(_parse_snapshot_file(full_snap_path, chart_path))

    return snapshot_files


def _normalize_yaml_str(yaml_str: str) -> str:
    try:
        docs = list(yaml.safe_load_all(yaml_str))
        if docs:
            return "\n---\n".join(yaml.dump(d).strip() for d in docs if d is not None)
    except Exception:
        pass
    return yaml_str.strip()


@tool(read_only=True, idempotent=True)
def diff_snapshot(
    chart_path: str,
    test_file_path: str,
    test_it: Optional[str] = None,
) -> SnapshotDiffResult:
    """Compare the stored snapshot against the rendered template output without modifying snapshots.

    Args:
        chart_path (str): Path to the Helm chart
        test_file_path (str): Path to the test file (e.g. "tests/deployment_test.yaml")
        test_it (str, optional): Name of a specific test case ('it' description) to diff.

    Returns:
        SnapshotDiffResult: Summary of differences, including a unified diff if mismatched.
    """
    test_dir = os.path.dirname(test_file_path)
    test_filename = os.path.basename(test_file_path)
    snap_path = os.path.join(test_dir, "__snapshot__", f"{test_filename}.snap")

    if not os.path.exists(snap_path):
        return SnapshotDiffResult(
            test_file=test_file_path,
            test_it=test_it,
            exists=False,
            has_diff=True,
            diff=None,
            message=f"Snapshot file not found at {snap_path}. Run update_snapshot to generate it.",
        )

    snap_file = _parse_snapshot_file(snap_path, chart_path)
    if not snap_file.snapshots:
        return SnapshotDiffResult(
            test_file=test_file_path,
            test_it=test_it,
            exists=True,
            has_diff=False,
            diff=None,
            message="Snapshot file exists but contains no snapshot entries.",
        )

    # Render debug output to obtain actual rendered output
    rendered_output = get_rendered_debug_output(chart_path, test_suite_files=test_file_path)

    # Find matching entry
    matching_entries = snap_file.snapshots
    if test_it:
        matching_entries = [e for e in snap_file.snapshots if test_it in e.name]
        if not matching_entries:
            return SnapshotDiffResult(
                test_file=test_file_path,
                test_it=test_it,
                exists=True,
                has_diff=True,
                diff=None,
                message=f"No snapshot entry found matching test case: '{test_it}'",
            )

    diff_lines_all: list[str] = []
    has_diff = False

    for entry in matching_entries:
        expected_norm = _normalize_yaml_str(entry.content)
        expected_lines = expected_norm.splitlines(keepends=True)

        actual_content = "\n---\n".join(
            v for k, v in rendered_output.items() if not k.startswith("__")
        )
        actual_norm = _normalize_yaml_str(actual_content)
        actual_lines = actual_norm.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                expected_lines,
                actual_lines,
                fromfile=f"snapshot: {entry.name}",
                tofile="actual rendered output",
            )
        )
        if diff:
            has_diff = True
            diff_lines_all.extend(diff)

    if has_diff:
        return SnapshotDiffResult(
            test_file=test_file_path,
            test_it=test_it,
            exists=True,
            has_diff=True,
            diff="".join(diff_lines_all),
            message="Differences found between snapshot and rendered output.",
        )

    return SnapshotDiffResult(
        test_file=test_file_path,
        test_it=test_it,
        exists=True,
        has_diff=False,
        diff=None,
        message="Snapshot is up to date and matches rendered output.",
    )


@tool(destructive=True)
def clean_snapshots(
    chart_path: str,
    dry_run: bool = True,
) -> SnapshotCleanResult:
    """Detect and prune orphaned snapshot files or obsolete snapshot entries for deleted tests.

    Args:
        chart_path (str): Path to the Helm chart directory
        dry_run (bool): If True, only reports what would be deleted without making changes.
                        If False, deletes orphaned snapshot files and prunes obsolete entries.

    Returns:
        SnapshotCleanResult: Summary of cleaned files, cleaned entry keys, and status message.
    """
    if not os.path.exists(chart_path):
        raise FileNotFoundError(f"Chart directory not found: {chart_path}")

    cleaned_files: list[str] = []
    cleaned_entries: list[str] = []

    for root, dirs, files in os.walk(chart_path):
        if os.path.basename(root) == "__snapshot__":
            for file in files:
                if file.endswith(".snap"):
                    snap_path = os.path.join(root, file)
                    snap_file = _parse_snapshot_file(snap_path, chart_path)

                    if snap_file.is_orphaned:
                        cleaned_files.append(snap_path)
                        if not dry_run:
                            try:
                                os.remove(snap_path)
                            except Exception:
                                pass
                        continue

                    # If test file exists, inspect test cases defined in test file
                    try:
                        with open(snap_file.test_file_path, "r", encoding="utf-8") as tf:
                            test_yaml = yaml.safe_load(tf)
                        active_tests = [
                            t.get("it", "").strip()
                            for t in test_yaml.get("tests", [])
                            if isinstance(t, dict) and t.get("it")
                        ]
                    except Exception:
                        active_tests = []

                    # Check which snapshot entries are obsolete
                    with open(snap_path, "r", encoding="utf-8") as sf:
                        snap_data = yaml.safe_load(sf) or {}

                    entries_to_remove = []
                    for entry_key in snap_data.keys():
                        # Entry keys usually contain test 'it' description
                        matches_any = any(act_test in str(entry_key) for act_test in active_tests)
                        if not matches_any and active_tests:
                            entries_to_remove.append(str(entry_key))
                            cleaned_entries.append(f"{snap_path} -> {entry_key}")

                    if entries_to_remove and not dry_run:
                        for k in entries_to_remove:
                            del snap_data[k]
                        if not snap_data:
                            os.remove(snap_path)
                            cleaned_files.append(snap_path)
                        else:
                            with open(snap_path, "w", encoding="utf-8") as sf:
                                yaml.dump(snap_data, sf)

            # Cleanup empty __snapshot__ directory if not dry_run
            if not dry_run:
                try:
                    if not os.listdir(root):
                        os.rmdir(root)
                except Exception:
                    pass

    mode_str = "Dry run: " if dry_run else ""
    return SnapshotCleanResult(
        cleaned_files=cleaned_files,
        cleaned_entries=cleaned_entries,
        dry_run=dry_run,
        message=f"{mode_str}Found {len(cleaned_files)} orphaned snapshot file(s) and {len(cleaned_entries)} obsolete entry(ies).",
    )
