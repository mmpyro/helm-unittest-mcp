import os
import difflib
import yaml
from typing import Annotated, Optional
from pydantic import Field
from utils.mcp import tool
from utils.truncate import truncate_text
from utils.dtos import (
    SnapshotFile,
    SnapshotEntry,
    SnapshotDiffResult,
    SnapshotCleanResult,
)
from tools.debug import get_rendered_debug_output


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
    test_file_path: Annotated[
        Optional[str], Field(description="Only snapshots belonging to this test file")
    ] = None,
    names_only: Annotated[
        bool,
        Field(
            description="Return entry names without their stored manifests. "
            "The manifests are large; fetch them only when you need to read one."
        ),
    ] = True,
    limit: Optional[int] = None,
    offset: int = 0,
) -> list[SnapshotFile]:
    """List the snapshot files in a chart and the entries each one stores."""
    if not os.path.exists(chart_path):
        raise FileNotFoundError(f"Chart directory not found: {chart_path}")

    snapshot_files: list[SnapshotFile] = []

    if test_file_path:
        test_dir = os.path.dirname(test_file_path)
        test_filename = os.path.basename(test_file_path)
        snap_path = os.path.join(test_dir, "__snapshot__", f"{test_filename}.snap")
        if os.path.exists(snap_path):
            snapshot_files.append(_parse_snapshot_file(snap_path, chart_path))
        return [_strip_bodies(f) for f in snapshot_files] if names_only else snapshot_files

    for root, dirs, files in os.walk(chart_path):
        if os.path.basename(root) == "__snapshot__":
            for file in files:
                if file.endswith(".snap"):
                    full_snap_path = os.path.join(root, file)
                    snapshot_files.append(_parse_snapshot_file(full_snap_path, chart_path))

    if offset > 0:
        snapshot_files = snapshot_files[offset:]
    if limit is not None and limit >= 0:
        snapshot_files = snapshot_files[:limit]

    return [_strip_bodies(f) for f in snapshot_files] if names_only else snapshot_files


def _strip_bodies(snap_file: SnapshotFile) -> SnapshotFile:
    """Replace each entry's stored manifest with its size, keeping the names."""
    return SnapshotFile(
        file_path=snap_file.file_path,
        test_file_path=snap_file.test_file_path,
        snapshots=[
            SnapshotEntry(name=e.name, content=f"<{len(e.content)} chars>")
            for e in snap_file.snapshots
        ],
        is_orphaned=snap_file.is_orphaned,
    )


def _manifest_identity(yaml_str: str) -> Optional[tuple[str, str]]:
    """Identify a rendered manifest by its kind and metadata.name, if it has both."""
    try:
        for doc in yaml.safe_load_all(yaml_str):
            if isinstance(doc, dict) and doc.get("kind"):
                metadata = doc.get("metadata") or {}
                name = metadata.get("name", "") if isinstance(metadata, dict) else ""
                return (str(doc["kind"]), str(name))
    except Exception:
        pass
    return None


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
    test_it: Annotated[
        Optional[str], Field(description="Only the entries whose name contains this text")
    ] = None,
    max_chars: Annotated[int, Field(description="Cap on the returned diff")] = 20000,
) -> SnapshotDiffResult:
    """Compare a test file's stored snapshots against a fresh render, without touching them."""
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

    # Index the rendered manifests by kind/name so each snapshot entry is diffed
    # against the template it actually came from, not against all of them at once.
    manifests = {k: v for k, v in rendered_output.items() if not k.startswith("__")}
    by_identity: dict[tuple[str, str], str] = {}
    for body in manifests.values():
        identity = _manifest_identity(body)
        if identity is not None:
            by_identity.setdefault(identity, body)

    all_rendered = "\n---\n".join(manifests.values())

    diff_lines_all: list[str] = []
    has_diff = False
    unmatched: list[str] = []

    for entry in matching_entries:
        expected_norm = _normalize_yaml_str(entry.content)

        identity = _manifest_identity(entry.content)
        actual_raw = by_identity.get(identity) if identity is not None else None
        if actual_raw is None:
            actual_raw = all_rendered
            unmatched.append(entry.name)

        actual_norm = _normalize_yaml_str(actual_raw)

        diff = list(
            difflib.unified_diff(
                expected_norm.splitlines(keepends=True),
                actual_norm.splitlines(keepends=True),
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
            diff=truncate_text("".join(diff_lines_all), max_chars),
            message=(
                "Differences found between snapshot and rendered output."
                + (
                    f" {len(unmatched)} entries could not be matched to a rendered "
                    "manifest and were compared against the whole render: "
                    + ", ".join(unmatched[:5])
                    if unmatched
                    else ""
                )
            ),
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
    dry_run: Annotated[
        bool, Field(description="Report what would be removed without removing it")
    ] = True,
) -> SnapshotCleanResult:
    """Remove snapshot files and entries left behind by deleted tests."""
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
