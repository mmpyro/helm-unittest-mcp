import json
from pathlib import Path
from utils.mcp import Server
from resources.references import ASSERTIONS_REFERENCE, MOCKING_REFERENCE
from tools.snapshots import get_snapshots


mcp = Server().mcp


@mcp.resource("helm-unittest://schema")
def schema_resource() -> str:
    """Official JSON schema for helm-unittest test suites."""
    bundled_path = Path(__file__).parent / "schemas" / "helm-testsuite.json"
    if bundled_path.exists():
        with open(bundled_path, "r", encoding="utf-8") as f:
            return f.read()
    return "{}"


@mcp.resource("helm-unittest://reference/assertions")
def assertions_reference_resource() -> str:
    """Comprehensive reference guide for helm-unittest assertions and document selectors."""
    return ASSERTIONS_REFERENCE


@mcp.resource("helm-unittest://reference/mocking")
def mocking_reference_resource() -> str:
    """Guide for mocking Helm capabilities, Release objects, k8s lookup resources, and postRenderers."""
    return MOCKING_REFERENCE


@mcp.resource("helm-unittest://snapshots/{chart_path}")
def snapshots_resource(chart_path: str) -> str:
    """Snapshot entries for a specific Helm chart."""
    try:
        snapshots = get_snapshots(chart_path)
        return json.dumps(
            [
                {
                    "file_path": s.file_path,
                    "test_file_path": s.test_file_path,
                    "is_orphaned": s.is_orphaned,
                    "entries": [{"name": e.name, "content": e.content} for e in s.snapshots],
                }
                for s in snapshots
            ],
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})
