import os
import re
import subprocess
from utils.mcp import Server, tool


mcp = Server().mcp


def _extract_rendered_templates_from_debug(debug_text: str) -> dict[str, str]:
    """Extract rendered templates from helm-unittest -d debug log output.

    Args:
        debug_text: The full stdout/stderr output from helm unittest -d

    Returns:
        Dictionary mapping template file path to rendered YAML string
    """
    templates: dict[str, str] = {}

    # Match outputOfFiles:map[...] pattern
    match = re.search(r"outputOfFiles:map\[(.*?)\]renderSucceed:", debug_text, re.DOTALL)
    if match:
        content = match.group(1)
        # Template keys look like: example/templates/deployment.yaml:... or templates/deployment.yaml:...
        # Split by occurrences of template file paths
        entries = re.split(r"(?:\s+|^)([^\s:]+templates/[^\s:]+):", content)
        if len(entries) > 1:
            # entries[0] might be empty before first match
            i = 1
            while i < len(entries):
                tpl_path = entries[i].strip()
                tpl_content = entries[i + 1].strip() if i + 1 < len(entries) else ""
                templates[tpl_path] = tpl_content
                i += 2

    # Check for any .debug directory created by the plugin
    return templates


@tool(read_only=True, idempotent=True)
def get_rendered_debug_output(
    chart_path: str,
    test_suite_files: str = "tests/*_test.yaml",
    values_path: list[str] = [],
) -> dict[str, str]:
    """Execute tests in debug mode and extract the rendered template outputs and debug logs.

    Useful for troubleshooting failed assertions by viewing the exact rendered
    manifests and values resolution produced by the helm-unittest renderer.

    Args:
        chart_path (str): Path to the Helm chart
        test_suite_files (str): Glob pattern or path for test suite files
        values_path (list[str]): Optional list of values files to pass

    Returns:
        dict[str, str]: Dictionary mapping template paths to their rendered YAML manifests,
                        plus a '__raw_debug_log__' key with the full debug output.
    """
    if not os.path.exists(chart_path):
        raise FileNotFoundError(f"Chart path not found: {chart_path}")

    cmd = [
        "helm",
        "unittest",
        "-d",
        "-f",
        test_suite_files,
        chart_path,
    ]
    for v in values_path:
        cmd.extend(["-v", v])

    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

    rendered = _extract_rendered_templates_from_debug(combined_output)
    rendered["__raw_debug_log__"] = combined_output.strip()

    # Also check if a .debug directory exists in chart_path
    debug_dir = os.path.join(chart_path, ".debug")
    if os.path.isdir(debug_dir):
        for root, _, files in os.walk(debug_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, chart_path)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        rendered[rel_path] = f.read()
                except Exception:
                    pass

    return rendered
