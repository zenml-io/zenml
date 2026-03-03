# Version Large Datasets with LakeFS and ZenML

Learn how to use LakeFS for Git-like data versioning alongside ZenML for pipeline orchestration — keeping TB-scale data out of the artifact store while maintaining full lineage.

## What You'll Learn

- Pass lightweight **data references** (not data) between pipeline steps using a Pydantic model
- Read and write large datasets directly from LakeFS via its S3-compatible API
- Create immutable data snapshots with LakeFS commits for reproducible training
- Retrain on any historical data version using a single commit SHA
- Log LakeFS lineage metadata in ZenML for end-to-end traceability

## Quickstart

```bash
# Start local LakeFS
docker compose up -d

# Install dependencies
pip install -r requirements.txt
zenml init

# Run the pipeline
python run.py
```

## Prerequisites

- Docker and Docker Compose (for local LakeFS)
- Python 3.9 or higher

## The Pattern

When datasets are too large to serialize through ZenML's artifact store (50GB+), pass **references instead of data**:

```
┌─────────────────────────────────────────────────────────┐
│                    ZenML Pipeline                        │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │  ingest  │───▶│ validate │───▶│  train   │          │
│  └──────────┘    └──────────┘    └──────────┘          │
│       │  ▲            │  ▲            │  ▲              │
│       │  │            │  │            │  │              │
│    LakeFSRef       LakeFSRef      LakeFSRef            │
│    (~200 B)        (~200 B)       (~200 B)             │
│       │  │            │  │            │  │              │
└───────┼──┼────────────┼──┼────────────┼──┼──────────────┘
        │  │            │  │            │  │
        ▼  │            ▼  │            ▼  │
┌───────────────────────────────────────────────────────┐
│                  LakeFS (S3 API)                       │
│                                                        │
│  repo: robot-data                                      │
│  ├── branch: ingest-a1b2c3d4                           │
│  │   ├── raw/data.parquet          (10K+ rows)         │
│  │   └── validated/data.parquet    (9.5K rows)         │
│  └── commit: 3f8a91c2...           (immutable)         │
└───────────────────────────────────────────────────────┘
```

| What | Where | Why |
|------|-------|-----|
| Raw sensor data (parquet) | LakeFS | Too large for artifact store at scale |
| Validated data (parquet) | LakeFS | Same — stays in the data lake |
| `LakeFSRef` pointers | ZenML artifact store | Tiny JSON, enables lineage + caching |
| Trained sklearn model | ZenML artifact store | Small, benefits from versioning |
| Training metrics | ZenML metadata | Visible in dashboard |

## What's Inside

```
lakefs_data_versioning/
├── steps/
│   ├── ingest.py          - Generate synthetic data, write to LakeFS branch
│   ├── validate.py        - Clean data, commit to LakeFS, return immutable ref
│   └── train.py           - Read from LakeFS, train sklearn model
├── pipelines/
│   └── training_pipeline.py
├── utils/
│   ├── lakefs_ref.py      - LakeFSRef Pydantic model (the pointer type)
│   └── lakefs_utils.py    - LakeFS SDK + S3 gateway helpers
├── configs/
│   ├── local.yaml         - Small dataset, no caching (for quick iteration)
│   └── remote.yaml        - DockerSettings with LakeFS credentials for K8s/Vertex/etc.
├── run.py                 - CLI entry point with --config and --lakefs-commit
├── docker-compose.yml     - Local LakeFS (stores data on local disk)
└── requirements.txt
```

## Key Concepts

### LakeFSRef: Data Pointers as Artifacts

Instead of serializing large DataFrames, steps pass a small Pydantic model that points to data in LakeFS:

```python
from pydantic import BaseModel

class LakeFSRef(BaseModel):
    repo: str       # "robot-data"
    ref: str        # branch name or commit SHA
    path: str       # "validated/data.parquet"
    endpoint: str   # "http://localhost:8000"
```

ZenML's built-in Pydantic materializer handles serialization automatically — no custom materializer needed. The artifact store only ever sees ~200 bytes of JSON.

### Named Artifacts with Annotated

All step outputs use `Annotated` to give artifacts meaningful names in the ZenML dashboard:

```python
from typing import Annotated, Dict, Tuple
from sklearn.ensemble import RandomForestRegressor

@step
def train_model(validated_ref: LakeFSRef) -> Tuple[
    Annotated[RandomForestRegressor, "trained_model"],
    Annotated[Dict[str, float], "training_metrics"],
]:
    df = read_parquet_from_lakefs(validated_ref.repo, validated_ref.ref, validated_ref.path)
    # ... train model ...
    return model, metrics
```

### Immutable Commits for Reproducibility

The validate step commits its output and returns the **commit SHA**, not the branch name. This makes the downstream reference immutable — the exact same data is read regardless of when the train step runs:

```python
# After writing validated data, commit the branch
commit_sha = commit_branch(repo, branch, f"Validated: {n_valid}/{n_total} rows")

return LakeFSRef(repo=repo, ref=commit_sha, path="validated/data.parquet", endpoint=endpoint)
```

### LakeFS Data Lineage in ZenML Metadata

The train step logs the LakeFS commit as ZenML metadata so you can trace any model back to its exact data snapshot:

```python
from zenml import log_metadata

log_metadata({
    "lakefs_commit": validated_ref.ref,
    "lakefs_repo": validated_ref.repo,
    "training_metrics": {"rmse": 0.42, "r2": 0.95},
})
```

## Run the Example

### Local (default)

1. **Start LakeFS**
   ```bash
   docker compose up -d
   ```
   Wait for LakeFS to be healthy (port 8000). Verify at http://localhost:8000 (login: admin / AKIAIOSFOLAKEFS).

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   zenml init
   ```

3. **Run the full pipeline**
   ```bash
   python run.py
   ```

   Expected output:
   ```
   Created LakeFS repository 'robot-data'.
   Generating 10000 rows of synthetic sensor data
   Created branch 'ingest-a1b2c3d4' from 'main'
   Wrote 10000 rows to LakeFS
   Validation stats: {'total_rows': 10000, 'valid_rows': 9500, ...}
   Committed branch: 3f8a91c2e4...
   Training RandomForestRegressor on 7600 samples
   Training metrics: {'rmse': 0.42, 'r2': 0.95, ...}
   ```

4. **Quick iteration with small dataset**
   ```bash
   python run.py --config configs/local.yaml
   ```

5. **Retrain on the same data snapshot**

   Copy the commit SHA from the validate step's output, then:
   ```bash
   python run.py --lakefs-commit 3f8a91c2e4...
   ```

   The ingest and validate steps detect the existing commit and pass the reference through without generating or processing data. The train step reads directly from the committed snapshot.

### Remote (Kubernetes, Vertex AI, SageMaker, etc.)

When running on a remote orchestrator, each step executes in a separate container. Those containers need pip packages and LakeFS credentials. The `configs/remote.yaml` config handles this via `DockerSettings`:

1. **Edit `configs/remote.yaml`** with your LakeFS deployment details:
   ```yaml
   settings:
     docker:
       requirements:
         - lakefs-sdk>=1.0.0
         - boto3>=1.28.0
         - pandas>=2.0.0
         - scikit-learn>=1.3.0
         - pyarrow>=14.0.0
       environment:
         LAKEFS_ENDPOINT: https://your-lakefs.example.com
         LAKEFS_ACCESS_KEY_ID: your-access-key
         LAKEFS_SECRET_ACCESS_KEY: your-secret-key
         LAKEFS_STORAGE_NAMESPACE: s3://your-bucket/lakefs
   ```

   For production, consider using [ZenML secrets](https://docs.zenml.io/how-to/interact-with-secrets) instead of plain environment variables in the config.

2. **Run with the remote config**
   ```bash
   python run.py --config configs/remote.yaml
   ```

## Customization Ideas

- **Swap synthetic data for real data**: Replace `_generate_sensor_data()` in `steps/ingest.py` with a loader that reads from your NAS, database, or cloud storage
- **Add a merge-to-main step**: After successful training, merge the ingest branch into `main` to promote validated data
- **Use Spark or Ray inside steps**: Replace `pd.read_parquet()` with distributed reads — the LakeFS S3 API works with any S3-compatible tool
- **Use real S3/GCS as LakeFS blockstore**: Set `LAKEFS_STORAGE_NAMESPACE=s3://your-bucket/lakefs` and configure LakeFS to use S3 blockstore
- **Track model versions**: Add `@pipeline(model=Model(name="sensor-model"))` to link artifacts to a model in ZenML's Model Control Plane

## Environment Variables

All default to the docker-compose setup. Override for production:

| Variable | Default | Description |
|----------|---------|-------------|
| `LAKEFS_ENDPOINT` | `http://localhost:8000` | LakeFS server URL |
| `LAKEFS_ACCESS_KEY_ID` | `AKIAIOSFOLAKEFS` | LakeFS access key |
| `LAKEFS_SECRET_ACCESS_KEY` | `wJalrXUtnFEMI/K7MDENG/...` | LakeFS secret key |
| `LAKEFS_STORAGE_NAMESPACE` | `local://data` | LakeFS blockstore namespace (`local://` for docker-compose, `s3://bucket/path` for production) |
| `LAKEFS_REPO` | `robot-data` | LakeFS repository name |

## Learn More

- [ZenML Artifact Management](https://docs.zenml.io/how-to/data-artifact-management) — artifact naming, metadata, and lineage
- [ZenML Docker Settings](https://docs.zenml.io/how-to/customize-docker-builds) — configuring containers for remote orchestrators
- [ZenML Secrets Management](https://docs.zenml.io/how-to/interact-with-secrets) — secure credential handling
- [LakeFS Quickstart](https://docs.lakefs.io/quickstart/) — LakeFS setup and branching model
- [LakeFS S3 Gateway](https://docs.lakefs.io/reference/s3.html) — how the S3-compatible API works
- [ZenML Model Control Plane](https://docs.zenml.io/how-to/model-control-plane) — versioning and promoting models
