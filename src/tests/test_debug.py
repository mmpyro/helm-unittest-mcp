import pytest
from unittest.mock import patch, MagicMock
from tools.debug import (
    get_rendered_debug_output,
    _extract_rendered_templates_from_debug,
)


SAMPLE_DEBUG_OUTPUT = """
time="2026-08-26T10:56:24+02:00" level=debug msg="outputOfFiles:map[example/templates/deployment.yaml:apiVersion: apps/v1
kind: Deployment
metadata:
  name: release-name-example
 example/templates/service.yaml:apiVersion: v1
kind: Service
metadata:
  name: release-name-example
]renderSucceed:trueerr:<nil>" test-job=render-v3-chart
 PASS  example deployment tests	example/tests/deployment/deployment_example_test.yaml
"""


def test_extract_rendered_templates_from_debug():
    rendered = _extract_rendered_templates_from_debug(SAMPLE_DEBUG_OUTPUT)
    assert "example/templates/deployment.yaml" in rendered
    assert "apiVersion: apps/v1" in rendered["example/templates/deployment.yaml"]
    assert "example/templates/service.yaml" in rendered
    assert "kind: Service" in rendered["example/templates/service.yaml"]


def test_get_rendered_debug_output_chart_not_found():
    with pytest.raises(FileNotFoundError, match="Chart path not found"):
        get_rendered_debug_output("/nonexistent/chart/path")


@patch("tools.debug.os.path.exists", return_value=True)
@patch("tools.debug.subprocess.run")
def test_get_rendered_debug_output_success(mock_run, mock_exists):
    mock_res = MagicMock()
    mock_res.stdout = SAMPLE_DEBUG_OUTPUT
    mock_res.stderr = ""
    mock_run.return_value = mock_res

    res = get_rendered_debug_output("./example", "tests/*_test.yaml", ["values.yaml"])
    assert "example/templates/deployment.yaml" in res
    assert "example/templates/service.yaml" in res
    # the raw log restates every rendered template, so it is opt-in
    assert "__raw_debug_log__" not in res
    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "-d" in cmd
    assert "-v" in cmd
    assert "values.yaml" in cmd


@patch("tools.debug.os.path.isdir", return_value=False)
@patch("tools.debug.os.path.exists", return_value=True)
@patch("tools.debug.subprocess.run")
def test_get_rendered_debug_output_include_raw_log(mock_run, mock_exists, mock_isdir):
    mock_res = MagicMock()
    mock_res.stdout = SAMPLE_DEBUG_OUTPUT
    mock_res.stderr = ""
    mock_run.return_value = mock_res

    res = get_rendered_debug_output("./example", include_raw_log=True)
    assert "__raw_debug_log__" in res


@patch("tools.debug.os.path.exists", return_value=True)
@patch("tools.debug.subprocess.run")
def test_get_rendered_debug_output_filters_templates(mock_run, mock_exists):
    mock_res = MagicMock()
    mock_res.stdout = SAMPLE_DEBUG_OUTPUT
    mock_res.stderr = ""
    mock_run.return_value = mock_res

    res = get_rendered_debug_output("./example", templates=["service.yaml"])
    assert list(res) == ["example/templates/service.yaml"]


@patch("tools.debug.os.path.exists", return_value=True)
@patch("tools.debug.subprocess.run")
def test_get_rendered_debug_output_truncates(mock_run, mock_exists):
    mock_res = MagicMock()
    mock_res.stdout = SAMPLE_DEBUG_OUTPUT
    mock_res.stderr = ""
    mock_run.return_value = mock_res

    res = get_rendered_debug_output("./example", max_chars=10)
    body = res["example/templates/deployment.yaml"]
    assert body.startswith("apiVersion")
    assert "truncated" in body
