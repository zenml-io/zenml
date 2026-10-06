# Inventory and customer operations

This example contains inventory reporting, customer conversion scoring, warehouse replenishment planning, a deployed customer risk service, customer retention model evaluation, customer segment training, and historical bike demand prediction. Runs retain their input and output artifacts, execution configuration, and operational metrics in the connected ZenML project.

## Setup

From this directory, create a dedicated Python 3.11 environment for the demo, including when launching it from an agent sandbox:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip check --python .venv/bin/python
.venv/bin/python -c "from opentelemetry.sdk._logs import LoggerProvider"
source .venv/bin/activate
```

Use this environment for every `python` and `zenml` command below. In separate sandbox shell calls, use `.venv/bin/python` and `.venv/bin/zenml` explicitly because activation may not persist. Docker settings install dependencies in remote images; they do not install dependencies into the sandbox that submits the pipeline.

The example pins ZenML 0.96.4; use a matching server version. Connect your ZenML client to the intended workspace and select the appropriate project and stack before running pipelines. The service requires a Deployer component and an endpoint reachable from the caller.

All demo pipelines use `build_settings.py` to build Python 3.11 images with ZenML 0.96.4 for Linux AMD64 workers. Their images install the explicit dependencies in `requirements.txt`, including matching OpenTelemetry API and SDK versions and the S3 and Kubernetes clients. The image build reinstalls the pinned OpenTelemetry API package and does not copy the launcher's installed packages or add integration dependencies from the selected stack. Use a remote image builder that supports this architecture. These settings apply when building an image; an explicitly reused image or `skip_build=True` bypasses dependency installation.

## Batch operations

```bash
python run.py inventory
python run.py customers --source-uri /path/to/customers.csv
python run.py train-risk
python run.py replenishment
```

The customer export contains `customer_id`, `account_length`, `basket_value`, and `converted` columns. The target `converted` is 0 or 1. The source can be a local file, a plain HTTP(S) URL, or an object URI accessible through the active stack's artifact store. For remote workers, use an HTTP(S) or object URI they can access; local paths refer to the worker's filesystem. Use stack credentials for private object storage; do not put credentials or signed query strings in source URLs, because pipeline parameters are retained in run configuration.

The command-line runner also accepts `--run-name` and `--no-cache` for normal execution control. Inspect recorded artifacts and metrics through the ZenML dashboard or SDK.

## Daily inventory reporting

The inventory pipeline loads a reproducible product catalog and calculates a dated inventory report from simulated daily demand and replenishment. The catalog step is cached for fixed source parameters. The reporting step executes on every run and records both itemized daily inventory and summary metrics.

```bash
python run.py inventory --business-date 2026-09-10 --simulation-start-date 2026-09-10
python run.py inventory --business-date 2026-09-11 --simulation-start-date 2026-09-10
```

Keep the source parameters and simulation start date fixed across a reporting series. Each report replays stock movements from that start date, so consecutive days reconcile without requiring the previous report as an input. The same date and inputs reproduce the same inventory, while each execution writes fresh report artifacts. Business dates describe synthetic inventory observations; ZenML execution timestamps record when the pipeline actually ran.

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

## Customer retention evaluation

The retention training pipeline records a classifier and a separate held-out dataset under the `customer-retention` model. Its evaluation pipeline loads both artifacts from one completed training run and produces classification metrics, a confusion matrix, and an HTML report with source identifiers.

```bash
python run.py train-retention
python run.py evaluate-retention --training-run-id <TRAINING_RUN_UUID>
```

For automatic evaluation, attach a remotely runnable snapshot of `scenario_05.pipelines.customer_model_evaluation` to a platform event trigger for the training pipeline. Leave `training_run_id` unset in that snapshot; evaluation uses the exact upstream run recorded by the trigger. Creating triggers requires ZenML Pro and a remote execution stack.

## Customer segment training

The dynamic segment training pipeline runs an isolated training step with configurable CPU resources. It produces a random forest classifier, structured held-out metrics, and an HTML evaluation report.

```bash
python run.py train-segments --cpu-count 4
```

Use `--sample-count` and `--random-seed` to configure the synthetic dataset. Resource pool admission requires a configured ZenML Pro pool and a policy associated with the execution component. The requested CPU and memory must fit that policy. Inspect the step's resource request and status reason in the workspace when diagnosing admission or allocation. Pool APIs differ between ZenML versions; use the API supported by the connected server.

## Bike demand prediction

The bike pipelines use the public [UCI Bike Sharing dataset](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset), which records hourly rental counts with calendar and observed weather information. Two named versions in the `bike-demand` model compare a calendar baseline and a gradient boosting estimator. Training uses observations before July 2012; evaluation uses July through September 2012. Target-derived rental counts are excluded from the model inputs.

```bash
python run.py train-bikes --model-version calendar-v1 --model-variant baseline
python run.py train-bikes --model-version weather-v1 --model-variant gradient_boosting
python run.py score-bikes --training-run-id <TRAINING_RUN_UUID> --scoring-date 2012-10-15
```

Choose a fresh model-version name for each training experiment. The runner links scoring to the exact training run's model version. Scoring requires the same source dataset bytes used for training, and its date must follow the evaluation interval. These are historical predictions using observed weather, not a live weather forecast.

The default source is the public UCI archive. Both commands accept `--source-uri` for an hourly CSV or UCI archive and `--source-sha256` to verify the source bytes. For private remote storage, use the active artifact store's URI and connector. The digest describes the supplied file bytes, so a CSV and an archive containing that CSV have different digests.

Training creates a demand explorer with calendar and weather patterns and a model scorecard with held-out error, rush-hour errors, and feature importance. Scoring creates a daily operations report with hourly estimates, observed rentals, peak hours, and model provenance. Each report is a self-contained HTML artifact with embedded SVG charts. Structured metrics and prediction tables remain available alongside the reports.

Dataset attribution: Fanaee-T, H. (2013), *Bike Sharing*, UCI Machine Learning Repository, [DOI: 10.24432/C5W894](https://doi.org/10.24432/C5W894), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Reports and derived data retain this attribution.
