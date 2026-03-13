# LakeFS + ZenML: Data Versioning for Large Datasets

ZenML versions your artifacts and tracks lineage. [LakeFS](https://lakefs.io) versions your data with Git-like branching, commits, and rollbacks — on top of your existing object store. They complement each other well: ZenML handles pipeline orchestration, caching, and metadata, while LakeFS handles the data layer at scales where serializing DataFrames through an artifact store stops making sense (50GB+, up to TB).

This example shows the pattern: pipeline steps exchange tiny references to data in LakeFS rather than the data itself. You get full pipeline lineage in ZenML, full data versioning in LakeFS, and the artifact store never has to touch the heavy data.

## Quickstart

```bash
docker compose up -d          # start local LakeFS
pip install -r requirements.txt
zenml init
python run.py                 # run the pipeline
```

## Prerequisites

- Docker (for local LakeFS)
- Python 3.9+

## How It Works

Instead of passing DataFrames between steps, each step passes a `LakeFSRef` — a ~200 byte JSON pointer:

```python
class LakeFSRef(BaseModel):
    repo: str       # "robot-data"
    ref: str        # branch name or commit SHA
    path: str       # "validated/data.parquet"
    endpoint: str   # "http://localhost:8000"
```

Steps read/write data directly to LakeFS via its S3-compatible API. ZenML's built-in Pydantic materializer handles the small reference object automatically.

```
  ZenML Pipeline (artifact store only sees ~200B pointers)
  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │  ingest  │───▶│ validate │───▶│  train   │
  └────┬─────┘    └────┬─────┘    └────┬─────┘
       │               │               │
       ▼               ▼               ▼
  ┌─────────────────────────────────────────┐
  │          LakeFS  (S3 API)               │
  │  raw/data.parquet → validated/ → commit │
  └─────────────────────────────────────────┘
```

| Data | Lives in | Why |
|------|----------|-----|
| Sensor data (parquet) | LakeFS | Too big for artifact store |
| `LakeFSRef` pointers | ZenML artifact store | Tiny, enables lineage + caching |
| Trained model | ZenML artifact store | Small, benefits from versioning |
| Metrics | ZenML metadata | Visible in dashboard |

## The Key Trick: Immutable Commits

After validation, the step commits the LakeFS branch and returns the **commit SHA** — not the branch name. This means the train step always reads the exact same data, no matter when it runs. Reproducibility for free.

```python
commit_sha = commit_branch(repo, branch, f"Validated: {n_valid}/{n_total} rows")
return LakeFSRef(repo=repo, ref=commit_sha, path="validated/data.parquet", ...)
```

## Project Structure

```
├── steps/
│   ├── ingest.py        - Generates synthetic sensor data, writes to LakeFS
│   ├── validate.py      - Cleans data, commits, returns immutable ref
│   └── train.py         - Reads from LakeFS, trains a RandomForest
├── pipelines/
│   └── training_pipeline.py
├── utils/
│   ├── lakefs_ref.py    - The LakeFSRef Pydantic model
│   └── lakefs_utils.py  - LakeFS SDK + S3 helpers
├── configs/
│   ├── local.yaml       - Small dataset for quick iteration
│   └── remote.yaml      - DockerSettings for K8s/Vertex/SageMaker
├── run.py               - CLI entry point
├── docker-compose.yml   - Local LakeFS
└── requirements.txt
```

## Running It

**Start LakeFS** (runs on port 8000):
```bash
docker compose up -d
```

You can check the LakeFS UI at http://localhost:8000 (user: `admin`, access key: `AKIAIOSFOLAKEFS`).

**Run the full pipeline:**
```bash
python run.py
```

**Smaller dataset for quick iteration:**
```bash
python run.py --config configs/local.yaml
```

**Retrain on a previous data snapshot** — grab the commit SHA from a previous run and pass it in. Ingest and validate get skipped, train reads directly from that commit:
```bash
python run.py --lakefs-commit 608e8fb36ca0ea9e...
```

## Running on Remote Orchestrators

On K8s, Vertex AI, SageMaker, etc., each step runs in its own container. Those containers need the LakeFS SDK and credentials. Edit `configs/remote.yaml` with your LakeFS endpoint and keys, then:

```bash
python run.py --config configs/remote.yaml
```

For production, use [ZenML secrets](https://docs.zenml.io/how-to/interact-with-secrets) instead of plain env vars.

## Going Further

- Replace `_generate_sensor_data()` in `steps/ingest.py` with your real data source
- Add a merge-to-main step to promote validated data after successful training
- Swap `pd.read_parquet()` for Spark or Ray — LakeFS's S3 API works with any S3-compatible tool
- Point LakeFS at real S3/GCS instead of local storage
- Add `@pipeline(model=Model(name="sensor-model"))` for model versioning via the Model Control Plane

## Environment Variables

Defaults match the docker-compose setup. Override for your environment:

| Variable | Default | Description |
|----------|---------|-------------|
| `LAKEFS_ENDPOINT` | `http://localhost:8000` | LakeFS URL |
| `LAKEFS_ACCESS_KEY_ID` | `AKIAIOSFOLAKEFS` | Access key |
| `LAKEFS_SECRET_ACCESS_KEY` | `wJalrXUtnFEMI/K7MDENG/...` | Secret key |
| `LAKEFS_STORAGE_NAMESPACE` | `local://data` | Blockstore namespace (`local://` for dev, `s3://bucket/path` for prod) |
| `LAKEFS_REPO` | `robot-data` | Repository name |

## Links

- [LakeFS Quickstart](https://docs.lakefs.io/latest/quickstart/index.html)
- [LakeFS S3 Gateway](https://docs.lakefs.io/latest/reference/s3/)
- [ZenML Artifact Management](https://docs.zenml.io/concepts/artifacts)
- [ZenML Docker Settings](https://docs.zenml.io/concepts/containerization)