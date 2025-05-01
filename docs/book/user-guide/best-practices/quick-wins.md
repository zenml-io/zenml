---
description: 5-minute Quick Wins
icon: lightning
---

# Quick Wins

Below is a menu of 5-minute quick wins you can sprinkle into an existing ZenML
project with almost no code changes. Each entry explains why it matters, the
micro-setup (under 5 minutes) and any tips or gotchas to anticipate.

| Quick Win | What it does | Why you need it |
|-----------|--------------|----------------|
| [Log rich metadata](#1-log-rich-metadata-on-every-run) | Track params, metrics, and properties on every run | Foundation for reproducibility and analytics |
| [Experiment comparison](#2-activate-the-experiment-comparison-view-zenml-pro) | Visualize and compare runs with parallel plots | Identify patterns and optimize faster |
| [Autologging](#3-drop-in-experiment-tracker-autologging) | Automatic metric and artifact tracking | Zero-effort experiment tracking |
| [Slack/Discord alerts](#4-instant-slack-alerts-for-successesfailures) | Instant notifications for pipeline events | Stay informed without checking dashboards |
| [Cron scheduling](#5-schedule-the-pipeline-on-a-cron) | Run pipelines automatically on schedule | Promote notebooks to production workflows |
| [Warm pools/resources](#6-kill-cold-starts-with-sagemaker-warm-pools--vertex-persistent-resources) | Eliminate cold starts in cloud environments | Reduce iteration time from minutes to seconds |
| [Secret management](#7-centralise-secrets-tokens-db-creds-s3-keys) | Centralize credentials and tokens | Keep sensitive data out of code |
| [Git repo hooks](#8-hook-your-git-repo-to-every-run) | Track code state with every run | Perfect reproducibility and faster builds |
| [HTML reports](#9-simple-html-reports) | Create rich visualizations effortlessly | Beautiful stakeholder-friendly outputs |


## 1 Log rich metadata on every run
**Why** -- instant lineage, reproducibility, and the raw material for all other dashboard analytics. Metadata is the foundation for experiment tracking, model governance, and comparative analysis.

```python
from zenml import log_metadata

# Basic metadata logging at step level - automatically attaches to current step
log_metadata({"lr": 1e-3, "epochs": 10, "prompt": my_prompt})

# Group related metadata in categories for better dashboard organization
log_metadata({
    "training_params": {
        "learning_rate": 1e-3,
        "epochs": 10,
        "batch_size": 32
    },
    "dataset_info": {
        "num_samples": 10000,
        "features": ["age", "income", "score"]
    }
})

# Use special types for consistent representation
from zenml.metadata.metadata_types import StorageSize, Uri
log_metadata({
    "dataset_source": Uri("gs://my-bucket/datasets/source.csv"),
    "model_size": StorageSize(256000000)  # in bytes
})
```

**Works at multiple levels:**
- **Within steps**: Logs automatically attach to the current step
- **Pipeline runs**: Track environment variables or overall run characteristics
- **Artifacts**: Document data characteristics or processing details
- **Models**: Capture hyperparameters, evaluation metrics, or deployment information

**Best practices:**
- Use consistent keys across runs for better comparison
- Group related metadata using nested dictionaries
- Use ZenML's special metadata types for standardized representation

*Metadata becomes the foundation for the Experiment Comparison tool and other
dashboard views.* (Learn more: [Metadata |
ZenML](https://docs.zenml.io/concepts/metadata), [Tracking Metrics with
Metadata](https://docs.zenml.io/how-to/model-management-metrics/track-metrics-metadata))

## 2 Activate the **Experiment Comparison** view (ZenML Pro)

**Why** -- side-by-side tables + parallel-coordinate plots of any numerical metadata help you quickly identify patterns, trends, and outliers across multiple runs. This visual analysis speeds up debugging and parameter tuning.

**Setup** -- once you've logged metadata (see quick win #1) nothing else to do; open **Dashboard → Compare**.  

[![Experiment Comparison Video](../.gitbook/assets/experiment_comparison_video.png)](https://www.loom.com/share/693b2d829600492da7cd429766aeba6a)

**Compare experiments at a glance:**
- **Table View**: See all runs side-by-side with automatic change highlighting
- **Parallel Coordinates Plot**: Visualize relationships between hyperparameters and metrics
- **Filter & Sort**: Focus on specific runs or metrics that matter most
- **CSV Export**: Download experiment data for further analysis (Pro tier)

**Practical uses:**
- Compare metrics across model architectures or hyperparameter settings
- Identify which parameters have the greatest impact on performance
- Track how metrics evolve across iterations of your pipeline

(Learn more: [Metadata | ZenML - Bridging the gap between ML & Ops](https://docs.zenml.io/how-to/model-management-metrics/track-metrics-metadata), [New Dashboard Feature: Compare Your Experiments - ZenML Blog](https://www.zenml.io/blog/new-dashboard-feature-compare-your-experiments))

## 3 Drop-in **Experiment Tracker Autologging**

**Why** -- Stream metrics, system stats, model files, and artifacts—all without modifying step code. Different experiment trackers offer varying levels of automatic tracking to simplify your MLOps workflows.
**Setup**

```bash
# First install your preferred experiment tracker integration
zenml integration install mlflow -y  # or wandb, neptune, comet
# Register the experiment tracker in your stack
zenml experiment-tracker register <NAME> --flavor=mlflow  # or wandb, neptune, comet
zenml stack update your_stack_name -e your_experiment_tracker_name
```

The experiment tracker's autologging capabilities kick in based on your tracker's features:

| Experiment Tracker | Autologging Capabilities |
|--------------------|-----------------------|
| **MLflow** | Comprehensive framework-specific autologging for TensorFlow, PyTorch, scikit-learn, XGBoost, LightGBM, Spark, Statsmodels, Fastai, and more. Automatically tracks parameters, metrics, artifacts, and environment details. |
| **Weights & Biases** | Out-of-the-box tracking for ML frameworks, media artifacts, system metrics, and hyperparameters. |
| **Neptune** | Requires explicit logging for most frameworks but provides automatic tracking of hardware metrics, environment information, and various model artifacts. |
| **Comet** | Automatic tracking of hardware metrics, hyperparameters, model artifacts, and source code. Framework-specific autologging similar to MLflow. |

**Best Practices**
* Store API keys in ZenML secrets (see quick win #8) to prevent exposure in Git.
* Configure the experiment tracker settings in your steps for more granular control.
* For MLflow, use `@step(experiment_tracker="mlflow")` to enable autologging in specific steps only.
* Disable MLflow autologging when needed, e.g.: `experiment_tracker.disable_autologging()`.

**Resources**
* [MLflow Experiment Tracking](https://docs.zenml.io/how-to/popular-integrations/mlflow)
* [Weights & Biases Integration](https://www.zenml.io/integrations/wandb)
* [Neptune Integration](https://www.zenml.io/integrations/neptune)
* [Comet Integration](https://www.zenml.io/integrations/comet)

## 4 Instant **Slack alerts** for successes/failures

**Why** -- get immediate notifications when pipelines succeed or fail, enabling
faster response times and improved collaboration. Slack notifications ensure
your team is always aware of critical model training status, data drift alerts,
and deployment changes.

{% hint style="info" %}
You can use the Discord alerter instead of Slack.
{% endhint %}

```bash
# Install the Slack integration
zenml integration install slack -y

# Register the alerter with your bot token and default channel
zenml alerter register slack_alerter \
    --flavor=slack \
    --slack_token=<SLACK_TOKEN> \
    --default_slack_channel_id=<SLACK_CHANNEL_ID>

# Add the alerter to your stack
zenml stack update your_stack_name -al slack_alerter
```

**Using in your pipelines**
```python
from zenml.integrations.slack.steps import slack_alerter_post_step

@pipeline
def pipeline_with_alerts():
    # Your pipeline steps
    train_model_step(...)

    # Post a simple text message
    slack_alerter_post_step(
        message="Model training completed successfully!"
    )

    # Or use advanced formatting with payload and metadata
    slack_alerter_post_step(
        message="Model metrics report",
        params=SlackAlerterParameters(
            slack_channel_id="#alerts-channel",  # Override default channel
            payload=SlackAlerterPayload(
                pipeline_name="Training Pipeline",
                step_name="Evaluation",
                stack_name="Production"
            )
        )
    )
```

**Key features**
* **Rich message formatting** with custom blocks, embedded metadata and pipeline artifacts
* **Human-in-the-loop approval** using the `slack_alerter_ask_step` for critical deployment decisions
* **Channel flexibility** to target different teams with specific alerts
* **Custom approval options** to configure which responses count as approvals/rejections

Learn more: [Full Slack alerter documentation](https://docs.zenml.io/stack-components/alerters/slack), [Alerters overview](https://docs.zenml.io/stack-components/alerters)

## 5 Schedule the pipeline on a cron

**Why** -- promote "run-by-hand" notebooks to automated, repeatable jobs. Scheduled pipelines ensure consistency, enable overnight training runs, and help maintain regularly updated models.

{% hint style="info" %}
Scheduling works with any orchestrator that supports schedules (Kubeflow, Airflow, Vertex AI, etc.)
{% endhint %}

**Setup - Using Python**
```python
from zenml.config.schedule import Schedule
from zenml import pipeline

# Define a schedule with a cron expression
schedule = Schedule(
    name="daily-training",
    cron_expression="0 3 * * *"  # Run at 3 AM every day
)

# Attach the schedule to your pipeline
@pipeline(schedule=schedule)
def my_pipeline():
    # Your pipeline steps
    pass

# Run once to register the schedule
my_pipeline()
```

**Key Features**
* **Cron expressions** for flexible scheduling (daily, weekly, monthly)
* **Start/end time controls** to limit when schedules are active
* **Timezone awareness** to ensure runs start at your preferred local time
* **Orchestrator-native scheduling** leveraging your infrastructure's capabilities

**Best Practices**
* Use descriptive schedule names like `daily-feature-engineering-prod-v1`
* For critical pipelines, add alert notifications for failures
* Verify schedules were created both in ZenML and the orchestrator
* When updating schedules, delete the old one before creating a new one

**Common troubleshooting**
* For cloud orchestrators, verify service account permissions
* Remember that deleting a schedule from ZenML doesn't remove it from the orchestrator!

Learn more: [Scheduling Pipelines](https://docs.zenml.io/how-to/build-pipelines/schedule-a-pipeline), [Managing Scheduled Pipelines](https://docs.zenml.io/user-guides/tutorial/managing-scheduled-pipelines)

## 6 Kill cold-starts with **SageMaker Warm Pools / Vertex Persistent Resources**

**Why** -- eliminate infrastructure initialization delays and reduce model iteration cycle time. Cold starts can add minutes to your workflow, but with warm pools, containers stay ready and model iterations can start in seconds.

{% hint style="info" %}
This feature works with AWS SageMaker and Google Cloud Vertex AI orchestrators.
{% endhint %}

**Setup for AWS SageMaker**
```bash
# Register SageMaker orchestrator with warm pools enabled
zenml orchestrator register sagemaker_warm \
    --flavor=sagemaker \
    --use_warm_pools=True

# Update your stack to use this orchestrator
zenml stack update your_stack_name -o sagemaker_warm
```

**Setup for Google Cloud Vertex AI**
```bash
# Register Vertex step operator with persistent resources
zenml step-operator register vertex_persistent \
    --flavor=vertex \
    --persistent_resource_id=my-resource-id

# Update your stack to use this step operator
zenml stack update your_stack_name -s vertex_persistent
```

**Key benefits**
* **Faster iteration cycles** - no waiting for VM provisioning and container startup
* **Cost-effective** - share resources across pipeline runs
* **No code changes** - zero modifications to your pipeline code
* **Significant speedup** - reduce startup times from minutes to seconds

**Important considerations**
* SageMaker warm pools incur charges when resources are idle
* For Vertex AI, set an appropriate persistent resource name for tracking
* Resources need occasional recycling for updates or maintenance

Learn more: [AWS SageMaker Orchestrator](https://docs.zenml.io/stack-components/orchestrators/sagemaker), [Google Cloud Vertex AI Step Operator](https://docs.zenml.io/stack-components/step-operators/vertex)

## 7 Centralise secrets (tokens, DB creds, S3 keys)

**Why** -- eliminate hardcoded credentials from your code and gain centralized control over sensitive information. Secrets management prevents exposing sensitive information in version control, enables secure credential rotation, and simplifies access management across environments.

**Setup - Basic usage**
```bash
# Create a secret with a key-value pair
zenml secret create wandb --api_key=$WANDB_KEY

# Reference the secret in stack components
zenml experiment-tracker register wandb_tracker \
    --flavor=wandb \
    --api_key={{wandb.api_key}}

# Update your stack with the new component
zenml stack update your_stack_name -e wandb_tracker
```

**Setup - Multi-value secrets**
```bash
# Create a secret with multiple values
zenml secret create database_creds \
    --username=db_user \
    --password=db_pass \
    --host=db.example.com

# Reference specific secret values
zenml artifact-store register my_store \
    --flavor=s3 \
    --aws_access_key_id={{database_creds.username}} \
    --aws_secret_access_key={{database_creds.password}}
```

**Key features**
* **Secure storage** - credentials kept in secure backend storage, not in your code
* **Scoped access** - restrict secret visibility based on user permissions
* **Easy rotation** - update credentials in one place when they change
* **Multiple backends** - support for Vault, AWS Secrets Manager, GCP Secret Manager, and more
* **Templated references** - use `{{secret_name.key}}` syntax in any stack configuration

**Best practices**
* Use a dedicated secret store in production instead of the default file-based store
* Set up CI/CD to use service accounts with limited permissions
* Regularly rotate sensitive credentials like API keys and access tokens

Learn more: [Secret Management](https://docs.zenml.io/getting-started/deploying-zenml/secret-management), [Working with Secrets](https://docs.zenml.io/how-to/project-setup-and-management/interact-with-secrets)

## 8 Hook your Git repo to every run

**Why** -- capture exact code state for reproducibility, automatic model versioning, and faster Docker builds. Connecting your Git repo transforms data science from local experiments to production-ready workflows with minimal effort:

- **Code reproducibility**: All pipelines track their exact commit hash and detect dirty repositories
- **Docker build acceleration**: ZenML avoids rebuilding images when your code hasn't changed
- **Model provenance**: Trace any model back to the exact code that created it
- **Team collaboration**: Share builds across the team for faster iteration

**Setup**
```bash
# Install the GitHub or GitLab integration
zenml integration install github  # or gitlab

# Register your code repository
zenml code-repository register project_repo \
    --type=github \
    --url=https://github.com/your/repo.git \
    --token=<GITHUB_TOKEN>  # use {{github_secret.token}} for stored secrets
```

**How it works**
1. When you run a pipeline, ZenML checks if your code is tracked in a registered repository
2. Your current commit and any uncommitted changes are detected and stored
3. ZenML can download files from the repository inside containers instead of copying them
4. Docker builds become highly optimized and are automatically shared across the team

**Best practices**
* Keep a clean repository state when running important pipelines
* Store your GitHub/GitLab tokens in ZenML secrets
* For CI/CD workflows, this pattern enables automatic versioning with Git SHAs
* Consider using `zenml pipeline build` to pre-build images once, then run multiple times

This simple setup can save hours of engineering time compared to manually tracking code versions and managing Docker builds yourself.

Learn more: [Code Repositories | ZenML - Bridging the gap between ML & Ops](https://docs.zenml.io/how-to/project-setup-and-management/setting-up-a-project-repository/connect-your-git-repository)

## 9 Simple HTML reports

**Why** -- create beautiful, interactive visualizations and reports with minimal effort using ZenML's HTMLString type and LLM assistance. HTML reports are perfect for sharing insights, summarizing pipeline results, and making your ML projects more accessible to stakeholders.

{% hint style="info" %}
This approach works with any LLM integration (GitHub Copilot, Claude in Cursor, ChatGPT, etc.) to generate complete, styled HTML reports with just a few prompts.
{% endhint %}

**Setup**
```python
from zenml.types import HTMLString
from typing import Dict, Any

@step
def generate_html_report(metrics: Dict[str, Any]) -> HTMLString:
    """Generate a beautiful HTML report from metrics dictionary."""
    # This HTML can be generated by an LLM or written manually
    html = f"""
    <html>
      <head>
        <style>
          body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f7f9fc; }}
          .report {{ max-width: 800px; margin: 0 auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 3px 10px rgba(0,0,0,0.1); }}
          h1 {{ color: #2d3748; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
          .metric {{ display: flex; margin: 15px 0; align-items: center; }}
          .metric-name {{ font-weight: 600; width: 180px; }}
          .metric-value {{ font-size: 20px; color: #4a5568; }}
          .good {{ color: #38a169; }}
          .bad {{ color: #e53e3e; }}
        </style>
      </head>
      <body>
        <div class="report">
          <h1>Model Training Report</h1>
          <div class="metric">
            <div class="metric-name">Accuracy:</div>
            <div class="metric-value">{metrics["accuracy"]:.4f}</div>
          </div>
          <div class="metric">
            <div class="metric-name">Loss:</div>
            <div class="metric-value">{metrics["loss"]:.4f}</div>
          </div>
          <div class="metric">
            <div class="metric-name">Training Time:</div>
            <div class="metric-value">{metrics["training_time"]:.2f} seconds</div>
          </div>
        </div>
      </body>
    </html>
    """
    return HTMLString(html)

@pipeline
def training_pipeline():
    # Your training pipeline steps
    metrics = model_training_step()
    # Generate an HTML report from metrics
    generate_html_report(metrics)
```

**Sample LLM prompt for building reports**
```
Generate an HTML report with CSS styling that displays the metrics that are input into the template in a visually appealing way.

Include:
1. A clean, modern design with responsive layout
2. Color coding for good/bad metrics
3. A simple bar chart using pure HTML/CSS to visualize the metrics
4. A summary section that interprets what these numbers mean

Provide only the HTML code without explanations. The HTML will be used with ZenML's HTMLString type.
```

**Key features**
* **Rich formatting** - Full HTML/CSS support for beautiful reports
* **Interactive elements** - Add charts, tables, and responsive design
* **Easy sharing** - Reports appear directly in ZenML dashboard
* **LLM assistance** - Generate complex visualizations with simple prompts
* **No dependencies** - Works out of the box without extra libraries

**Advanced use cases**
* Include interactive charts using [D3.js](https://d3js.org/) or [Chart.js](https://www.chartjs.org/)
* Create comparative reports showing before/after metrics
* Build error analysis dashboards with filtering capabilities
* Generate PDF-ready reports for stakeholder presentations

Simply return an `HTMLString` from any step, and your visualization will automatically appear in the ZenML dashboard for that step's artifacts.

Learn more: [Visualizations | ZenML - Bridging the gap between ML & Ops](https://docs.zenml.io/concepts/artifacts/visualizations)
