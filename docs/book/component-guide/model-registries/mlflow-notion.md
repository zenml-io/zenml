---
description: Hybrid MLflow-Notion model registry for collaborative ML workflows
---

# MLflow-Notion Model Registry

The MLflow-Notion hybrid model registry combines the robustness of [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html) as the source of truth with [Notion's](https://www.notion.so/) collaborative database features for team visibility and cross-functional collaboration.

This integration automatically syncs model versions, stages, and metadata between MLflow, Notion, and ZenML, creating a unified view across all three systems with clickable cross-links for easy navigation.

![MLflow-Notion Architecture](../../.gitbook/assets/mlflow-notion-architecture.png)

## When would you want to use it?

The MLflow-Notion model registry is ideal for teams that need:

* **Cross-functional collaboration**: Share model information with non-technical stakeholders through Notion's familiar interface
* **MLflow as source of truth**: Keep MLflow's robust versioning and lifecycle management while adding a collaboration layer
* **Unified model tracking**: Automatically sync model metadata across MLflow UI, Notion database, and ZenML dashboard
* **Easy navigation**: Jump between systems with one click via embedded cross-system URLs
* **Team visibility**: Give product managers, business stakeholders, and QA teams visibility into model deployments without needing MLflow access

This is particularly useful when:

* Your team includes non-technical members who need to track model deployments
* You want to add rich context (notes, decisions, stakeholder approvals) to model versions in Notion
* You need a single source of truth (MLflow) with a collaborative overlay (Notion)
* You want automatic synchronization without manual data entry

## Architecture

The integration creates a triangle of synchronized systems:

```
    MLflow Registry (Source of Truth)
           ↓     ↑
          sync  tags
           ↓     ↑
    Notion Database ←→ ZenML Model
   (Collaboration)    (Lineage)
```

**Data flow:**
1. **MLflow → Notion**: Model versions, stages, descriptions sync to Notion database
2. **Notion → MLflow**: Notion page URLs added as tags to MLflow versions
3. **MLflow → ZenML**: Stages and metadata sync to ZenML Model versions
4. **Cross-links**: All three systems store URLs to each other for easy navigation

**Key principle**: MLflow is the source of truth. Notion and ZenML sync failures don't block MLflow operations.

## How do you deploy it?

### Prerequisites

1. **MLflow server**: Running MLflow tracking/registry server (local or remote)
2. **Notion workspace**: Notion account with database creation permissions
3. **Notion integration**: Create a Notion integration at [notion.so/my-integrations](https://www.notion.so/my-integrations)

### Step 1: Install the integration

```shell
zenml integration install mlflow_notion -y
```

### Step 2: Create Notion database

1. Create a new database in your Notion workspace
2. Share the database with your Notion integration
3. Copy the database ID from the URL: `notion.so/workspace/{database_id}?v=...`

The database will be auto-populated with these properties:
- **Model Name** (title) - Name of the model
- **Version** (text) - Version number
- **Stage** (select) - One of: None, Staging, Production, Archived
- **Model Source URI** (url) - Location where model is stored
- **Description** (text) - Model description
- **Created At** (date) - Creation timestamp
- **MLflow Model URL** (url) - Link to MLflow model registry version
- **ZenML Model URL** (url) - Link to ZenML dashboard

### Step 3: Register the model registry

```shell
zenml model-registry register mlflow_notion_registry \
    --flavor=mlflow_notion \
    --tracking_uri=http://localhost:5000 \
    --notion_api_token={{YOUR_NOTION_TOKEN}} \
    --notion_database_id={{YOUR_DATABASE_ID}} \
    --sync_on_write=true
```

**Configuration options:**

| Parameter | Description | Required |
|-----------|-------------|----------|
| `tracking_uri` | MLflow tracking server URI (e.g., `http://localhost:5000`, `databricks`) | No* |
| `registry_uri` | MLflow registry URI (if different from tracking URI) | No |
| `notion_api_token` | Notion integration token from [notion.so/my-integrations](https://www.notion.so/my-integrations) | Yes |
| `notion_database_id` | Notion database ID (from database URL) | Yes |
| `sync_on_write` | Auto-sync to Notion on model registration (default: `true`) | No |

\* If not provided, uses `MLFLOW_TRACKING_URI` environment variable or defaults to `./mlruns`

### Step 4: Add to your stack

**Option 1: Registry only (standalone)**
```shell
zenml stack register mlflow_notion_stack \
    -r mlflow_notion_registry \
    -a default \
    -o default \
    --set
```

**Option 2: With MLflow experiment tracker (recommended)**
```shell
# Register MLflow experiment tracker
zenml experiment-tracker register mlflow_tracker \
    --flavor=mlflow \
    --tracking_uri=http://localhost:5000

# Register stack with both components
zenml stack register mlflow_notion_stack \
    -r mlflow_notion_registry \
    -e mlflow_tracker \
    -a default \
    -o default \
    --set
```

**Why use both?**
- Registry automatically uses experiment tracker's MLflow configuration
- Ensures runs and registry point to same MLflow server
- Enables experiment run → model registry workflow
- Avoids configuration duplication

## How do you use it?

### Basic usage: Register models in pipelines

The simplest way to use the MLflow-Notion registry is through ZenML's built-in Model feature with `save_models_to_registry=True`:

```python
from zenml import Model, pipeline, step
from zenml.enums import ArtifactType
from typing import Annotated
from sklearn.ensemble import RandomForestClassifier
import mlflow.sklearn

@step
def train_model() -> Annotated[RandomForestClassifier, ArtifactType.MODEL]:
    """Train and return a model."""
    from zenml.client import Client

    # Configure MLflow to use the model registry's tracking server
    # This ensures experiments and registered models go to the same server
    Client().active_stack.model_registry.configure_mlflow()

    # Enable MLflow autologging to log model artifacts
    # Now logs to the correct MLflow server
    mlflow.sklearn.autolog()

    # Train model
    model = RandomForestClassifier()
    model.fit(X_train, y_train)  # Artifact logged here by autolog

    return model

@pipeline(
    enable_cache=False,
    model=Model(
        name="customer_churn_predictor",
        description="Predicts customer churn based on usage patterns",
        tags=["classification", "production"],
        save_models_to_registry=True,  # ← Automatically registers to MLflow-Notion
    ),
)
def training_pipeline():
    model = train_model()
```

**What happens automatically:**
1. MLflow autolog saves model artifact during training
2. Model registered to MLflow registry with `zenml.mlflow_notion_managed` tag
3. Notion database entry created (if `sync_on_write=True`)
4. Notion page URL added as tag to MLflow version
5. Cross-system URLs added to ZenML Model metadata
6. All three systems now have links to each other

**Important: Artifact Logging**

The model registry creates **references** to model artifacts, not the artifacts themselves. You must log the model artifact separately using one of these methods:

- **Option 1: MLflow autolog** (recommended):
  ```python
  mlflow.sklearn.autolog()  # For scikit-learn
  mlflow.tensorflow.autolog()  # For TensorFlow
  mlflow.pytorch.autolog()  # For PyTorch
  ```

- **Option 2: Explicit logging**:
  ```python
  mlflow.sklearn.log_model(model, "model")
  mlflow.tensorflow.log_model(model, "model")
  mlflow.pytorch.log_model(model, "model")
  ```

Without artifact logging, the registry will create a version entry but won't have access to the actual model files for deployment.

### Advanced: Manual sync for external changes

If models are created/updated in MLflow UI (outside ZenML pipelines), use the sync operation to propagate changes:

```python
from zenml import pipeline, step
from zenml.client import Client
from zenml.integrations.mlflow_notion.model_registries import (
    MLFlowNotionModelRegistry,
)

@step
def sync_models(
    model_name: str | None = None,
    cleanup_orphans: bool = False,
) -> dict:
    """Sync MLflow models to Notion and ZenML."""
    client = Client()
    registry = client.active_stack.model_registry

    stats = registry.sync_to_notion(
        model_name=model_name,
        cleanup_orphans=cleanup_orphans,
    )

    return stats

@pipeline(enable_cache=False)
def sync_pipeline(model_name: str | None = None):
    """Periodic sync pipeline to handle external changes."""
    sync_models(model_name=model_name)
```

**Run sync manually:**
```shell
# Sync all models
python sync_pipeline.py

# Sync specific model
python sync_pipeline.py --model-name customer_churn_predictor

# Sync and cleanup orphaned Notion entries
python sync_pipeline.py --cleanup-orphans
```

### Recommended: Schedule periodic sync

For production deployments, schedule regular sync to catch manual MLflow UI changes:

```python
from zenml.config.schedule import Schedule

@pipeline(
    enable_cache=False,
    schedule=Schedule(cron_expression="0 * * * *"),  # Every hour
)
def hourly_sync_pipeline():
    """Scheduled sync to keep systems in sync."""
    sync_models()
```

## Integration with MLflow Experiment Tracker

The MLflow-Notion registry can work standalone or integrate with ZenML's MLflow experiment tracker component.

### Standalone mode (no experiment tracker)

When no MLflow experiment tracker is in the stack:
- Registry uses its own `tracking_uri` configuration
- You must configure MLflow connection in the registry component
- Works independently without experiment tracking

### Integrated mode (with experiment tracker) ✅ Recommended

When an MLflow experiment tracker is present in the stack:
- **Registry automatically inherits experiment tracker's configuration**
- Both components point to the same MLflow server
- No need to duplicate `tracking_uri` configuration
- Experiment runs and model registry are connected

**Example workflow:**
```python
import mlflow

@step
def train_model():
    # Experiment tracker handles run context
    mlflow.sklearn.autolog()

    model.fit(X, y)
    # ↓ Model logged to experiment run
    # ↓ Run URI: runs://run-id/model

    return model

# Pipeline with save_models_to_registry=True
# ↓ Registry registers model from run
# ↓ Links experiment run to model version ✅
```

**Benefits:**
- Single source of truth for MLflow configuration
- Automatic linking: model version → experiment run → metrics/params
- Simplified stack management

**Configuration priority:**
1. If MLflow experiment tracker exists → Use its config
2. Otherwise → Use registry's own `tracking_uri`
3. Fallback → Use `MLFLOW_TRACKING_URI` env var or `./mlruns`

## How it works

### Tagging strategy

All models registered through this integration are tagged in MLflow with:
```python
zenml.mlflow_notion_managed = "true"
```

This allows:
- Filtering sync operations to only models from this integration
- Avoiding conflicts with other MLflow models
- Clear ownership and provenance tracking

### Sync mechanisms

**1. Auto-sync on write (`sync_on_write=True`)**
- Triggers when ZenML pipelines register models via this registry
- MLflow operation always succeeds (source of truth)
- Notion sync is best-effort (logs warning if it fails)
- Adds `notion_sync_error` metadata to ZenML Model if sync fails

**2. Scheduled sync pipeline**
- Runs periodically (e.g., hourly via schedule)
- Detects changes made in MLflow UI, CLI, or other systems
- Only syncs models with `zenml.mlflow_notion_managed` tag
- Updates Notion and ZenML to match MLflow state

### Cross-system navigation

Each system stores URLs to the others, creating a complete navigation triangle:

**MLflow tags:**
```python
{
    "zenml.mlflow_notion_managed": "true",
    "notion_page_url": "https://notion.so/abc123...",
    "zenml_model_url": "https://zenml.example.com/models/my_model/3"
}
```

**ZenML Model metadata:**
```python
{
    "registry_links": {
        "mlflow_model_url": "http://localhost:5000/#/models/my_model/versions/3",
        "notion_page_url": "https://notion.so/abc123..."
    }
}
```

**Notion database properties:**
- **MLflow Model URL**: Link to MLflow model registry version page
- **ZenML Model URL**: Link to ZenML dashboard model page

This means you can navigate from any system to any other with one click!

### Stage mapping

MLflow and ZenML use different stage conventions:

| MLflow Stage | ZenML Stage | Notion Display |
|--------------|-------------|----------------|
| None | none | None |
| Staging | staging | Staging |
| Production | production | Production |
| Archived | archived | Archived |

**Stage constraint handling:**
- MLflow allows multiple versions per stage
- ZenML allows only one version per Production/Staging
- Sync automatically demotes old versions when promoting newer ones
- Uses `force=True` to override ZenML's validation (MLflow is source of truth)

## Recovery and failure handling

### Design principle: MLflow is source of truth

The integration is designed to be resilient to failures:

- **MLflow registration always succeeds or fails atomically**
- **Notion/ZenML sync failures don't block MLflow operations**
- **Recovery is idempotent** - safe to run sync multiple times

### Recoverable scenarios ✅

**1. Pipeline crashes after MLflow registration**
```
MLflow: versions 1-10 ✅
Notion: versions 1-7 ❌
```
Recovery: Run sync pipeline → Creates missing Notion entries

**2. Notion API down during training**
```
MLflow: succeeds ✅
Notion: fails ❌
ZenML: metadata includes "notion_sync_error"
```
Recovery: Run sync pipeline when Notion is back up

**3. Missing cross-system links**
```
MLflow: no notion_page_url tag ❌
Notion: entry exists ✅
ZenML: no registry_links metadata ❌
```
Recovery: Run sync pipeline → Adds all missing links

**4. Stage drift between systems**
```
MLflow: version 5, stage=Production ✅
Notion: version 5, stage=Staging ❌
ZenML: version 3, stage=Staging ❌
```
Recovery: Run sync pipeline → Updates all to Production

### Non-recoverable scenarios ❌

**1. ZenML Model version doesn't exist**
```
MLflow: version 8 (created in MLflow UI) ✅
Notion: version 8 (synced) ✅
ZenML: No version 8 ❌
```

**Why**: ZenML Model versions are pipeline artifacts and cannot be created by sync

**Workaround**: Re-register the model through a ZenML pipeline

**2. Version number misalignment**
```
MLflow: versions 1, 2, 3, 4, 5
ZenML: versions 1, 2, 3 (3 pipeline runs)
```

**Why**: MLflow and ZenML maintain independent version counters

**This is expected behavior** - they track different concepts:
- MLflow version = registered model version number
- ZenML version = pipeline run artifact version

### Best practices for production

**1. Always use ZenML pipelines for registration**

This ensures all three systems are created together:

```python
@pipeline(
    model=Model(
        name="my_model",
        save_models_to_registry=True,  # ← Creates MLflow + Notion + ZenML
    )
)
def train():
    ...
```

**2. Enable auto-sync for immediate consistency**

```shell
zenml model-registry register ... --sync_on_write=true
```

**3. Schedule periodic sync for drift detection**

```python
@pipeline(schedule=Schedule(cron_expression="0 * * * *"))
def hourly_sync():
    sync_models()
```

**4. Monitor sync stats**

Sync returns statistics to track:
```python
{
    "created": 5,      # New Notion entries
    "updated": 3,      # Modified entries
    "unchanged": 42,   # Already in sync
    "orphaned": 0,     # Removed (if cleanup_orphans=True)
    "errors": 0        # Failed operations
}
```

## Example: Complete workflow

See the full example in `examples/mlflow_notion_sync/`:

**Training pipeline** (`train.py`):
```python
from zenml import Model, pipeline, step
from sklearn.ensemble import RandomForestRegressor
import mlflow.sklearn

@step
def train_model() -> RandomForestRegressor:
    mlflow.sklearn.autolog()
    model = RandomForestRegressor(n_estimators=50)
    model.fit(X_train, y_train)
    return model

@pipeline(
    enable_cache=False,
    model=Model(
        name="aesthetic_quality_predictor",
        description="Image aesthetic quality prediction model",
        tags=["computer-vision", "aesthetic-prediction"],
        save_models_to_registry=True,
    ),
)
def training_pipeline():
    model = train_model()

if __name__ == "__main__":
    training_pipeline()
```

**Sync pipeline** (`sync.py`):
```python
from zenml import pipeline, step
from zenml.client import Client

@step
def sync_models(
    model_name: str | None = None,
    cleanup_orphans: bool = False,
) -> dict:
    client = Client()
    registry = client.active_stack.model_registry

    return registry.sync_to_notion(
        model_name=model_name,
        cleanup_orphans=cleanup_orphans,
    )

@pipeline(enable_cache=False)
def sync_pipeline(
    model_name: str | None = None,
    cleanup_orphans: bool = False,
):
    return sync_models(
        model_name=model_name,
        cleanup_orphans=cleanup_orphans,
    )

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", type=str, default=None)
    parser.add_argument("--cleanup-orphans", action="store_true")
    args = parser.parse_args()

    sync_pipeline(
        model_name=args.model_name,
        cleanup_orphans=args.cleanup_orphans,
    )
```

**Usage:**
```shell
# 1. Train model (auto-syncs to Notion)
python train.py

# 2. Make changes in MLflow UI (e.g., promote to Production)

# 3. Sync changes to Notion and ZenML
python sync.py

# Check stats in output
```

## Troubleshooting

### Sync errors

**Error: `'str' object has no attribute 'key'`**

This means the code tried to access MLflow tags incorrectly. Ensure you're using the latest version of the integration.

**Error: `Model version X is in production, but force flag is False`**

ZenML prevents multiple versions in Production. The sync automatically handles this with `force=True`, so this shouldn't occur. If it does, check your ZenML version.

### Missing Notion entries

If models exist in MLflow but not Notion:

1. Check if model has `zenml.mlflow_notion_managed` tag
2. Run sync pipeline: `python sync.py`
3. Check Notion database is shared with your integration

### Missing cross-system links

If URLs aren't appearing in metadata:

1. Run sync pipeline to add missing links
2. Check ZenML Model version exists (sync can't create them)
3. Verify `sync_on_write=true` in registry config

### Version number mismatches

**This is normal!** MLflow and ZenML use independent version counters. They track different things:
- MLflow: Model registry version (increments on every registration)
- ZenML: Pipeline artifact version (increments on every pipeline run)

The systems are linked by name and metadata, not version numbers.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
