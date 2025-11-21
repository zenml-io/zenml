---
description: Changelog for ZenML OSS and ZenML Dashboard.
icon: code-branch
layout:
  cover:
    visible: true
    size: hero
  title:
    visible: true
  description:
    visible: true
  tableOfContents:
    visible: true
  outline:
    visible: true
  pagination:
    visible: true
---

# ZenML OSS

## ZenML Framework (Core & Server)

### 0.91.2

**New Features**

* **Kubernetes Deployer:** New deployer implementation that allows you to deploy your pipelines on Kubernetes.

**Other**

* **Support for Mlflow 3.0:** Added support for the latest MLflow version.

**Bug Fixes**

* The S3 artifact store now works again with custom backends.
* Passing inline SSL certificates for the RestZenStore now works.
* The Weights & Biases experiment tracker now doesn't fail if the pipeline run name exceeds the maximum tag length.

### 0.91.1

**New Features**

* **Huggingface Deployer:** New deployer implementation that allows you to deploy your pipelines on Huggingface.
* **Kubernetes Orchestrator Enhancements:**
    * Additional configuration option to specify the container security context.
    * Additional configuration option that can be used skip creating owner references.

**Other**

* New authentication options for the HashiCorp Vault secret store.
* Support for newer Databricks versions.
* Introduced v1 of dynamic pipelines (Experimental).

**Bug Fixes**

* Fix port reuse for local deployments.
* Fix parallel deployment invocations.
* Fix keyboard interrupt handling while monitoring a synchronous run.
* Fix case-sensitivity issue when updating the name of some entities like stack components.

### 0.91.0

This release brings major deployment enhancements (Local Deployer, fully customizable deployment server, and deployment visualizations), powerful caching controls, Python 3.13 support, and more.

**New Features**

* **Deployment:**
    * Local Deployer for deploying pipelines locally.
    * Deployment server is fully customizable via settings.
    * Attach custom visualizations to deployments.
* **Caching:**
    * Specify files or Python objects that invalidate a step's cache.
    * Cache expiration to bound cache lifetime.
    * Custom cache function for advanced invalidation logic.
* **Other:**
    * MLX array materializer.
    * Python 3.13 support.
    * Customize the image tag of built Docker images.

**Breaking Changes**

* Drop Python 3.9 support.

**Bug Fixes**

* Fix incompatibility of print capturing when using numba.
* Fix the mount point configuration in the Hashicorp Vault secrets store.

### 0.90.0

This release introduces pipeline snapshots and pipeline deployments, refactors the base package dependencies, and adds runtime environment variable support.

**New Features**

* **Pipeline Snapshots:** Capture immutable snapshots of pipeline code, configuration, and container images.
* **Pipeline Deployments:** Add a new Deployer stack component (Docker, AWS, GCP implementations) to deploy pipelines as HTTP endpoints.
* **Runtime Environment Variables:** Configure environment variables when running pipelines.
* **Dependency Management:** Reduced base package dependencies (moved local database dependencies to local package extra).
* **Jax Support:** Add materializer for Jax arrays.

**Breaking Changes**

* Client-Server Compatibility: Not compatible with previous versions.
* Run Templates: Existing run templates need to be recreated.
* Base Package: The `zenml` package no longer includes local database dependencies. Install `zenml[local]` for local database support.

### 0.85.0

The 0.85.0 release delivers powerful pipeline execution enhancements and caching improvements.

**New Features**

* **Pipeline Execution Modes:** Flexible Failure Handling to configure what happens when a step fails.
* **Advanced Caching System:**
    * **Value-Based Caching:** Cache artifacts based on content/value rather than just artifact ID.
    * **Cache Policies:** Granular control over caching behavior.
* **Airflow 3.0 Support:** Compatibility with Apache Airflow 3.0.

**Breaking Changes**

* Local Orchestrator Behavior: Continues executing steps after some steps fail.
* Docker Package Installer: Default switched from pip to uv.
* Log Endpoint Format: Log endpoints return a different format.

### 0.84.3

**New Features**

* **ZenML Pro Service Account Authentication:**
    * CLI Login Support via `zenml login --api-key`.
    * Service account API keys can be used for programmatic access.
    * Organization-Level Access for automated workflows.

**Fixes**

* **Kubernetes Integration:** Fixed resource name sanitization.
* **Dependencies:** Relaxed Click dependency version constraints.

### 0.84.2

**Improvements**

* **Kubernetes Orchestrator:** Complete rework to use Jobs instead of raw pods for better robustness and restarts.
* **Faster Pipeline Compilation:** Significantly improved performance for large pipelines.

**Fixes**

* Fixed deadlock in run creation.
* Enhanced path materializer security.
* Improved logging performance.
* Fixed WandB experiment tracker flavor initialization.

### 0.84.1

**New Features & Improvements**

* **Step Exception Handling:** Improved collection of exception info.
* **External Service Accounts:** Added support for external service accounts.
* **Kubernetes Orchestrator:** Added schedule management and better error handling.
* **Dynamic Fan-out/Fan-in:** Support for dynamic patterns with run templates.

**Fixes**

* Vertex step operator credential refresh.
* Logging race conditions.

### 0.84.0

This release delivers significant architectural improvements and orchestration enhancements.

**New Features**

* **Orchestration:**
    * Early Pipeline Stopping (Kubernetes orchestrator).
    * Step Retries: Configurable retry mechanisms.
    * Step Status Refresh: Real-time status monitoring.
* **Kubernetes Orchestrator:**
    * Run steps using Jobs.
    * Enhanced Pod Management and Caching.
    * Orchestrator pod logs access.

**Breaking Changes**

* Kubernetes Orchestrator Compatibility: Client and orchestrator pod versions must match exactly.

### 0.83.1

**Performance Improvements**

* Separated step configurations from deployment.
* Idempotent POST requests with request caching.
* Enhanced artifact loading performance.

**Fixes**

* Fixed race conditions during pipeline run status updates.
* Fixed missing artifact nodes in DAG visualization.
* Fixed run template fetching issues.

### 0.83.0

Major Performance Release with significant response optimizations.

**Performance Improvements**

* Optimized API Responses: Reduced response sizes for large pipelines.
* Database Query Optimization.
* Reduced Response Payloads.

**Breaking Changes**

* Client/Server Compatibility: Not compatible with earlier versions.
* API Response Changes: Run responses no longer include unpaginated step lists or full metadata.

### 0.82.1

**Features**

* `pyproject.toml` support for configuring `DockerSettings`.
* Unique instance label in Helm chart.
* New stress-test example.

**Improvements**

* Cascading tags for cached step runs.
* Configurable Kubernetes job clean-up options.
* Limit to maximum number of concurrent template runs.

### 0.82.0

**Features**

* Max parallelism option for Kubernetes orchestrator.
* Customizable pod name prefixes and scheduler options.
* Private service connect option for Vertex AI.
* Configurable runner timeout.

**Improvements**

* Improved build invalidation when parent Dockerfile changes.
* Enhanced directory handling during code download.

### 0.81.0

**Features**

* **Path Materializer:** Upload directories and files.
* **Resource Sharing:** Enable sharing for teams and external users.
* **Client-side Logs Storage:** Store pipeline run logs in the artifact store.
* **Artifact Visualization:** Added `save_visualizations` method.

**Breaking Changes**

* Client-side log storage breaks pydantic model compatibility. Run templates must be rebuilt.

### 0.80.2

**Features**

* Added `poetry add` support for CLI.
* Added retry option on `step.with_options`.
* Added service annotations to helm chart.

**Fixes**

* Fixed yanked fsspec pip resolution issue.
* Fixed Kubernetes Orchestrator step pod failure status updates.

---

## ZenML Dashboard (OSS UI)

### v0.39.1

* **Fixes:** Remove Video Modal, Update Dependencies (CVE), Adjust text-color, Sanitize Dockerfile.

### v0.39.0

* **Features:**
    * Display Deployment in Run Detail.
    * Announcements Widget.
    * Add Resize Observer to HTML Viz.
    * Adjust Overview Pipelines.
* **Fixes:** Fix Panel background, Input Styling, Display Schedules.

### v0.38.0

* **New Features:**
    * **Deployment Playground:** Easier to invoke and test deployments.
    * **Global Lists:** Centralized access for deployments and snapshots.
    * **Create Snapshots:** Create snapshots directly from the dashboard.
* **Misc:** GitHub-Flavored Markdown support, Resizable Panels.

### v0.37.0

* **New Features:**
    * **Pipeline Snapshots & Deployments:** Track entities introduced in ZenML 0.90.0.

### v0.36.0

* **New Features:**
    * **Timeline View:** New way to visualize pipeline runs alongside the DAG.
* **Improvements:** Client-Side Structured Logs, Default Value for Arrays.

### v0.35.2

* **Fixes:** Default values.

### v0.35.1

* **Fixes:** Fix Completed State, Add First & Last Button to Logs, Display Authors, Refactor Node Details.

### v0.35.0

* **Features:**
    * Refactor Onboarding & Survey.
    * Stop Runs directly from dashboard.
    * Step Refresh.
    * Support multiple log origins.

