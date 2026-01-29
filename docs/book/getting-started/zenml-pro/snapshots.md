---
description: Trigger pipelines from the dashboard, SDK, CLI, or REST API.
icon: camera
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Snapshots

A **Pipeline Snapshot** is an immutable snapshot of your pipeline that includes the pipeline DAG, code, configuration, and container images. Snapshots enable you to trigger pipeline runs without direct access to the codebase—from the ZenML Pro dashboard, Python SDK, CLI, or REST API.

{% hint style="success" %}
Running snapshots is a ZenML Pro feature. For comprehensive documentation including advanced usage patterns, see the [main Snapshots documentation](../../how-to/snapshots/snapshots.md).
{% endhint %}

## Why Use Snapshots?

Snapshots solve common production challenges:

- **Data Scientists** can experiment with different parameters without modifying code
- **MLOps Engineers** can schedule retraining or integrate with CI/CD systems
- **Stakeholders** can trigger model training through the dashboard
- **External Systems** can invoke pipelines via REST API calls

## Requirements

{% hint style="warning" %}
Snapshots require a **remote stack** with at least:
- Remote orchestrator
- Remote artifact store
- Container registry

Local stacks cannot run snapshots.
{% endhint %}

{% hint style="info" %}
**Platform Engineers:** For snapshots to work in Hybrid or Self-hosted deployments, you must configure the workload manager on your Workspace Server. See [Workspace Server Configuration - Workload Manager](config-workspace-server.md#workload-manager) for the required environment variables and Kubernetes RBAC setup.
{% endhint %}

## Creating Snapshots

### From the CLI

```bash
zenml pipeline snapshot create <PIPELINE-SOURCE-PATH> --name=<SNAPSHOT-NAME>
```

You can also specify a configuration file and stack:

```bash
zenml pipeline snapshot create <PIPELINE-SOURCE-PATH> \
    --name=<SNAPSHOT-NAME> \
    --config=<PATH-TO-CONFIG-YAML> \
    --stack=<STACK-ID-OR-NAME>
```

### From Python SDK

```python
from zenml import pipeline

@pipeline
def my_pipeline():
    ...

snapshot = my_pipeline.create_snapshot(name="production-training")
```

### From the Dashboard

1. Navigate to a pipeline run
2. Click `...` in the top right corner
3. Select `+ New Snapshot`
4. Enter a name and click `Create`

## Running Snapshots

### From the CLI

```bash
zenml pipeline snapshot run <SNAPSHOT-NAME-OR-ID>

# With custom configuration
zenml pipeline snapshot run <SNAPSHOT-NAME-OR-ID> --config=config.yaml
```

### From Python SDK

```python
from zenml.client import Client

# Get the snapshot
snapshot = Client().get_snapshot("<NAME-OR-ID>")

# Optionally modify configuration
config = snapshot.config_template
config.steps["my_step"].parameters["my_param"] = new_value

# Trigger the run
Client().trigger_pipeline(
    snapshot_name_or_id=snapshot.id,
    run_configuration=config,
)
```

### From the Dashboard

1. Click `Run a Pipeline` on the Pipelines page, or navigate to a snapshot and click `Run Snapshot`
2. Modify configuration using the built-in editor or upload a YAML file
3. Click `Run`

### From REST API

```bash
curl -X 'POST' \
  '<YOUR-ZENML-SERVER>/api/v1/pipeline_snapshots/<SNAPSHOT-ID>/runs' \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
    "run_configuration": {
      "steps": {
        "train_model": {
          "parameters": {"model_type": "rf"}
        }
      }
    }
  }'
```

{% hint style="info" %}
For REST API authentication, use [Personal Access Tokens](personal-access-tokens.md) or [Service Accounts](service-accounts.md).
{% endhint %}

## Deleting Snapshots

```bash
zenml pipeline snapshot delete <SNAPSHOT-NAME-OR-ID>
```

Or via Python:

```python
from zenml.client import Client
Client().delete_snapshot(name_id_or_prefix="<SNAPSHOT-NAME-OR-ID>")
```

## Important Notes

{% hint style="warning" %}
**After upgrading your ZenML server**, you need to recreate your snapshots. Snapshots are tied to specific server versions and may not work correctly after an upgrade.
{% endhint %}

## Related Documentation

- [Snapshots - Full Documentation](../../how-to/snapshots/snapshots.md) - Complete reference with advanced usage
- [Trigger Pipelines from External Systems](../../user-guide/tutorial/trigger-pipelines-from-external-systems.md) - Tutorial for CI/CD integration
- [Workspace Server Configuration](config-workspace-server.md#workload-manager) - Configure the workload manager that powers snapshots
- [Service Accounts](service-accounts.md) - Set up API authentication for automated triggers

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

