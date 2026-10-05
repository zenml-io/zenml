# Inventory and customer operations

This example contains inventory reporting, customer conversion scoring, warehouse replenishment planning, and a deployed customer risk service. Runs retain their input and output artifacts, execution configuration, and operational metrics in the connected ZenML project.

## Setup

From this directory, install the requirements into your environment with `uv pip install -r requirements.txt`. Connect your ZenML client to the intended workspace and select the appropriate project and stack before running pipelines. The service requires a Deployer component and an endpoint reachable from the caller. Use a compatible ZenML client and server version.

## Batch operations

```bash
python run.py inventory
python run.py customers --source-uri /path/to/customers.csv
python run.py train-risk
python run.py replenishment
```

The customer export contains `customer_id`, `account_length`, `basket_value`, and `converted` columns. The target `converted` is 0 or 1. The source can be a local file, a plain HTTP(S) URL, or an object URI accessible through the active stack's artifact store. For remote workers, use an HTTP(S) or object URI they can access; local paths refer to the worker's filesystem. Use stack credentials for private object storage; do not put credentials or signed query strings in source URLs, because pipeline parameters are retained in run configuration.

The command-line runner also accepts `--run-name` and `--no-cache` for normal execution control. Inspect recorded artifacts and metrics through the ZenML dashboard or SDK.

## Warehouse replenishment

The replenishment pipeline creates itemized orders and a summary from a reproducible warehouse stock sample. Use `--minimum-stock` to configure the target stock level; its default is 20 units per product. `--batch-size` and `--source-seed` select the sample.

```bash
python run.py replenishment --minimum-stock 20
```

For recurring execution, create a pipeline snapshot and attach it to a schedule trigger using ZenML's [trigger workflow](https://docs.zenml.io/pro/core-concepts/triggers). This requires Pro triggers and a remote execution stack. The runner above starts a manual execution.

## Customer risk service

Train the risk model before deploying the inference pipeline:

```bash
python run.py train-risk
zenml pipeline deploy scenario_03.pipelines.customer_risk --name customer-risk
zenml deployment describe customer-risk
zenml deployment invoke customer-risk --customer_features='{"monthly_charges":80,"account_length":12,"support_calls":3}'
```

The service loads the latest `customer_risk_model` artifact in the active project at startup and returns its artifact ID with each prediction. Deployment logs record the loaded version. Use a dedicated demo project or choose distinct resource names when sharing a project with other applications.

After making changes, update the deployment and verify its responses:

```bash
zenml pipeline deploy scenario_03.pipelines.customer_risk --name customer-risk --update
```

The model uses synthetic customer data and is intended for demonstration.
