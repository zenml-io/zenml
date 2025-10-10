---
description: Understanding source roots and source paths
icon: folders
---

# Source Code and Imports

When ZenML interacts with your pipeline code, it needs to understand how to locate and import your code. This page explains how ZenML determines the source root directory and how to construct source paths for referencing your Python objects.

## Source Root

The **source root** is the root directory of all your local code files.

ZenML determines the source root using the following priority:

1. **ZenML Repository**: If you're in a child directory of a [ZenML repository](https://docs.zenml.io/user-guides/best-practices/set-up-your-repository) (initialized with `zenml init`), the repository directory becomes the source root. We recommend always initializing a ZenML repository to make the source root explicit.

2. **Execution Context Fallback**: If no ZenML repository exists in your current working directory or parent directories, ZenML uses the parent directory of the Python file you're executing. For example, running `/a/b/run.py` sets the source root to `/a/b`.

{% hint style="warning" %}
If you're running in a notebook or an interactive Python environment, there will be no file that is currently executed and ZenML won't be able to automatically infer the source root. Therefore, you'll need to explicitly define the source root by initializing a ZenML repository in these cases.
{% endhint %}

## Source Paths

ZenML requires source paths in various configuration contexts. These are Python-style dotted paths that reference objects in your code.

### Common Use Cases

**Step Hook Configuration**:
```yaml
success_hook_source: <SUCCESS-HOOK-SOURCE>
```

**Pipeline Deployment via CLI**:
```bash
zenml pipeline deploy <PIPELINE-SOURCE>
```

### Path Construction

Import paths must be **relative to your source root** and follow Python import syntax.

**Example**: Consider this pipeline in `/a/b/c/run.py`:
```python
from zenml import pipeline

@pipeline
def my_pipeline():
    ...
```

The source path depends on your source root:
- Source root `/a/b/c` → `run.my_pipeline`
- Source root `/a` → `b.c.run.my_pipeline`

{% hint style="info" %}
Note that the source is not a file path, but instead its elements are separated by dots similar to how you would write import statements in Python.
{% endhint %}

## Containerized Step Execution

When running pipeline steps in containers, ZenML ensures your source root files are available in the container (either by including them in the image or downloading them at runtime). 

To execute your step code, ZenML imports the Python module containing the step definition. **All imports of local code files must be relative to the source root** for this to work correctly.

{% hint style="info" %}
If you don't need all files inside your source root for step execution, see the [containerization guide](../containerization/containerization.md#controlling-included-files) for controlling which files are included.
{% endhint %}