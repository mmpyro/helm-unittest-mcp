"""Reference documentation for helm-unittest assertions, mocking, and capabilities."""

ASSERTIONS_REFERENCE = """# Helm Unittest Assertions Reference Guide

In `helm-unittest`, assertions validate rendered Kubernetes manifests.

## Assertion Types

### 1. `equal` / `notEqual`
Compares a value at a target JSONPath to an expected value.
```yaml
- equal:
    path: spec.replicas
    value: 3
- notEqual:
    path: metadata.namespace
    value: kube-system
```

### 2. `matchRegex` / `notMatchRegex`
Validates that a string value matches or does not match a regular expression.
```yaml
- matchRegex:
    path: metadata.name
    pattern: ^my-app-[a-z0-9]+$
```

### 3. `contains` / `notContains`
Checks if an array or string contains a specific element or substring.
```yaml
- contains:
    path: spec.template.spec.containers[0].args
    content: --verbose
```

### 4. `containsSubPath` / `notContainsSubPath`
Checks whether an object within an array or map contains specific sub-path key-value pairs.
```yaml
- containsSubPath:
    path: spec.template.spec.containers
    content:
      name: my-app
      image: nginx:latest
```

### 5. `isNull` / `isNotNull`
Asserts that a path does not exist (is null) or does exist (is not null).
```yaml
- isNull:
    path: spec.template.spec.securityContext
- isNotNull:
    path: spec.template.spec.containers[0].resources
```

### 6. `isEmpty` / `isNotEmpty`
Asserts that an array, map, or string at a given path is empty or non-empty.
```yaml
- isEmpty:
    path: metadata.annotations
```

### 7. `isKind`
Asserts the `kind` of the rendered document.
```yaml
- isKind:
    of: Deployment
```

### 8. `isAPIVersion`
Asserts the `apiVersion` of the rendered document.
```yaml
- isAPIVersion:
    of: apps/v1
```

### 9. `hasDocuments`
Asserts the total number of documents rendered by the template.
```yaml
- hasDocuments:
    count: 2
```

### 10. `lengthEqual`
Asserts the length of an array or object at a given path.
```yaml
- lengthEqual:
    path: spec.template.spec.containers
    count: 1
```

### 11. `matchSnapshot` / `matchSnapshotRaw`
Compares the rendered document against a saved snapshot in `__snapshot__/*.snap`.
```yaml
- matchSnapshot: {}
- matchSnapshot:
    path: spec.template.spec
```

### 12. `failedTemplate`
Asserts that rendering the template should fail with `fail` or an error.
```yaml
- failedTemplate:
    errorMessage: "A valid storageClassName is required!"
```

## Document Selection (`documentIndex` and `documentSelector`)

When a template renders multiple manifests (multi-document YAML):
- **`documentIndex`**: 0-based integer index of the document in the output.
- **`documentSelector`**: Select a document using JSONPath queries:
```yaml
documentSelector:
  path: $[?(@.kind == "Service")].metadata.name
  value: my-service
```
"""

MOCKING_REFERENCE = """# Helm Unittest Mocking Reference Guide

Guide for mocking Kubernetes capabilities, release options, cluster provider objects, and post-renderers.

## 1. Capabilities Mocking
Define the `.Capabilities` object for your test suite to test API compatibility:
```yaml
capabilities:
  majorVersion: 1
  minorVersion: 28
  apiVersions:
    - networking.k8s.io/v1
    - monitoring.coreos.com/v1
```

## 2. Release Mocking
Simulate `.Release` variables such as installation name, namespace, revision, or upgrade status:
```yaml
release:
  name: my-release
  namespace: production
  revision: 2
  upgrade: true
```

## 3. Kubernetes Provider Mocking (`lookup` function)
Mock cluster resources queried via Helm's `lookup` function:
```yaml
kubernetesProvider:
  scheme:
    "v1/Secret":
      gvr:
        version: "v1"
        resource: "secrets"
      namespaced: true
  objects:
    - kind: Secret
      apiVersion: v1
      metadata:
        name: my-existing-secret
        namespace: default
      data:
        api-key: "c2VjcmV0"
```

## 4. PostRenderer Mocking
Apply post-rendering transformations (e.g. kustomize or yq) before assertions:
```yaml
postRenderer:
  cmd: "yq"
  args:
    - "eval"
    - '.metadata.annotations["app.kubernetes.io/injected"]="true"'
    - "-"
```

## 5. Subchart and Values Mocking
Override subchart values or test individual subcharts:
```yaml
values:
  - values/prod.yaml
set:
  global.imageRegistry: "docker.io"
  subchart.enabled: true
```
"""
