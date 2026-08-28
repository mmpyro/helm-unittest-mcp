# Example Chart

The `example/` directory contains a complete, runnable **sample Helm chart** that demonstrates the structure expected by `helm-unittest` and serves as a playground for the MCP tools.

---

## Chart Structure

```
example/
├── Chart.yaml            # Chart metadata
├── values.yaml           # Default values
├── .helmignore
├── templates/
│   ├── _helpers.tpl      # Named template helpers
│   ├── deployment.yaml   # Kubernetes Deployment
│   ├── service.yaml      # Kubernetes Service
│   ├── serviceaccount.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml          # HorizontalPodAutoscaler
│   └── NOTES.txt
└── tests/
    ├── deployment/       # Test suites for the Deployment template
    ├── service/          # Test suites for the Service template
    ├── serviceaccount/   # Test suites for the ServiceAccount template
    ├── ingress/          # Test suites for the Ingress template
    └── horizontalpodautoscaler/
```

Each `tests/<resource>/` directory contains one or more YAML test suite files following the `helm-unittest` convention.

---

## Running the Example

From the repository root:

```bash
helm unittest example/
```

Or via the MCP server (ask your AI assistant):

```
Use run_tests_parallel with dir_path="example/tests" and chart_path="example"
```

---

## Test Suite Anatomy

A typical test file looks like:

```yaml
suite: Deployment tests
templates:
  - templates/deployment.yaml
tests:
  - it: should render with default values
    asserts:
      - isKind:
          of: Deployment
      - equal:
          path: spec.replicas
          value: 1

  - it: should set image from values
    set:
      image.repository: nginx
      image.tag: "1.25"
    asserts:
      - equal:
          path: spec.template.spec.containers[0].image
          value: nginx:1.25
```

Key fields:

| Field | Description |
|---|---|
| `suite` | Name of this test suite (required) |
| `templates` | Template files to render for this suite |
| `tests[].it` | Human-readable test case name (required) |
| `tests[].set` | Override Helm values for this test case |
| `tests[].asserts` | List of assertion checks |

---

## Using MCP Tools on the Example

### Discover tests

```
get_tests("example/tests")
```

### Validate schema

```
validate_tests("example/tests")
```

### Check coverage

```
get_test_coverage("example")
```

### Debug a failing test

```
get_rendered_debug_output("example", "tests/deployment/*_test.yaml")
```

---

## Coverage Baseline

The example chart provides tests for all five renderable templates:

| Template | Covered |
|---|---|
| `deployment.yaml` | ✅ |
| `service.yaml` | ✅ |
| `serviceaccount.yaml` | ✅ |
| `ingress.yaml` | ✅ |
| `hpa.yaml` | ✅ |

`NOTES.txt` and `_helpers.tpl` are excluded from coverage analysis (non-manifest files).

---

_Back to [Documentation Index →](./index.md)_
