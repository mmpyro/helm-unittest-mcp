import os
import re
import subprocess
from typing import Annotated, Optional
from pydantic import Field
from utils.mcp import tool
from utils.truncate import truncate_text


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
    templates: Annotated[
        Optional[list[str]],
        Field(description="Return only these template paths; null returns all of them"),
    ] = None,
    max_chars: Annotated[
        int, Field(description="Per-template cap on the returned YAML")
    ] = 20000,
    include_raw_log: Annotated[
        bool,
        Field(
            description="Also return the renderer's full debug log under __raw_debug_log__. "
            "It restates every rendered template, so it is large."
        ),
    ] = False,
) -> dict[str, str]:
    """Render a chart through helm-unittest in debug mode and return the resulting manifests.

    Use it to see what a failing assertion actually rendered.
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

    if templates:
        wanted = set(templates)
        rendered = {
            path: body
            for path, body in rendered.items()
            if path in wanted or os.path.basename(path) in wanted
        }

    if include_raw_log:
        rendered["__raw_debug_log__"] = combined_output.strip()

        # The plugin may also leave rendered manifests on disk; a third copy of
        # the same content, so it rides along with the raw log rather than alone.
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

    if not rendered:
        return {
            "__note__": "No rendered templates found. "
            "Re-run with include_raw_log=true to inspect the renderer output."
        }

    return {
        path: truncate_text(body, max_chars) or "" for path, body in rendered.items()
    }
