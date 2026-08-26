import json
import pytest
from resources.resources import (
    schema_resource,
    assertions_reference_resource,
    mocking_reference_resource,
    snapshots_resource,
)


def test_schema_resource():
    content = schema_resource()
    assert isinstance(content, str)
    data = json.loads(content)
    assert isinstance(data, dict)
    assert "$schema" in data or "title" in data or "properties" in data


def test_assertions_reference_resource():
    content = assertions_reference_resource()
    assert isinstance(content, str)
    assert "Helm Unittest Assertions Reference" in content
    assert "equal" in content
    assert "matchRegex" in content
    assert "documentSelector" in content


def test_mocking_reference_resource():
    content = mocking_reference_resource()
    assert isinstance(content, str)
    assert "Helm Unittest Mocking Reference" in content
    assert "capabilities" in content
    assert "kubernetesProvider" in content
    assert "postRenderer" in content


def test_snapshots_resource():
    content = snapshots_resource("example")
    assert isinstance(content, str)
    data = json.loads(content)
    assert isinstance(data, list)
