---
description: Stacks define where and how your pipelines run
---

# Stacks

A stack is made up of the following three core components:

* An Artifact Store
* A Metadata Store
* An Orchestrator \(backend\)

A ZenML stack also happens to be a Pydantic `BaseSettings` class, which means that there are multiple ways to use it.

```bash
zenml stack register MY_NEW_STACK
    --metadata_store my-new-metadata-store \
    --artifact_store my-new-artifact-store \ 
    --orchestrator my-new-orchestrator

```

{% hint style="info" %}
See [CLI reference](../support/cli-command-reference.md) for more help.
{% endhint %}

