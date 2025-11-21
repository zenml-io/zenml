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

* **Kubernetes Deployer:** New deployer implementation that allows you to deploy your pipelines on Kubernetes ([#4127](https://github.com/zenml-io/zenml/pull/4127)).

**Other**

* **Support for Mlflow 3.0:** Added support for the latest MLflow version ([#4160](https://github.com/zenml-io/zenml/pull/4160)).

**Bug Fixes**

* The S3 artifact store now works again with custom backends ([#4186](https://github.com/zenml-io/zenml/pull/4186)).
* Passing inline SSL certificates for the RestZenStore now works ([#4188](https://github.com/zenml-io/zenml/pull/4188)).
* The Weights & Biases experiment tracker now doesn't fail if the pipeline run name exceeds the maximum tag length ([#4189](https://github.com/zenml-io/zenml/pull/4189)).

### 0.91.1

**New Features**

* **Huggingface Deployer:** New deployer implementation that allows you to deploy your pipelines on Huggingface ([#4119](https://github.com/zenml-io/zenml/pull/4119)).
* **Kubernetes Orchestrator Enhancements:**
    * Additional configuration option to specify the container security context ([#4142](https://github.com/zenml-io/zenml/pull/4142)).
    * Additional configuration option that can be used skip creating owner references ([#4146](https://github.com/zenml-io/zenml/pull/4146)).

**Other**

* New authentication options for the HashiCorp Vault secret store ([#4110](https://github.com/zenml-io/zenml/pull/4110)).
* Support for newer Databricks versions ([#4144](https://github.com/zenml-io/zenml/pull/4144)).
* Introduced v1 of dynamic pipelines (Experimental) ([#4074](https://github.com/zenml-io/zenml/pull/4074)).

**Bug Fixes**

* Fix port reuse for local deployments.
* Fix parallel deployment invocations.
* Fix keyboard interrupt handling while monitoring a synchronous run.
* Fix case-sensitivity issue when updating the name of some entities like stack components ([#4140](https://github.com/zenml-io/zenml/pull/4140)).

### 0.91.0

This release brings major deployment enhancements (Local Deployer, fully customizable deployment server, and deployment visualizations), powerful caching controls, Python 3.13 support, and more.

**New Features**

* **Deployment:**
    * Local Deployer for deploying pipelines locally ([#4085](https://github.com/zenml-io/zenml/pull/4085)).
    * Deployment server is fully customizable via settings ([#4064](https://github.com/zenml-io/zenml/pull/4064)).
    * Attach custom visualizations to deployments ([#4016](https://github.com/zenml-io/zenml/pull/4016)).
* **Caching:**
    * Specify files or Python objects that invalidate a step's cache ([#4040](https://github.com/zenml-io/zenml/pull/4040)).
    * Cache expiration to bound cache lifetime.
    * Custom cache function for advanced invalidation logic.
* **Other:**
    * MLX array materializer ([#4027](https://github.com/zenml-io/zenml/pull/4027)).
    * Python 3.13 support ([#4053](https://github.com/zenml-io/zenml/pull/4053)).
    * Customize the image tag of built Docker images ([#4025](https://github.com/zenml-io/zenml/pull/4025)).

**Breaking Changes**

* Drop Python 3.9 support ([#4053](https://github.com/zenml-io/zenml/pull/4053)).

**Bug Fixes**

* Fix incompatibility of print capturing when using numba ([#4060](https://github.com/zenml-io/zenml/pull/4060)).
* Fix the mount point configuration in the Hashicorp Vault secrets store ([#4088](https://github.com/zenml-io/zenml/pull/4088)).

### 0.90.0

This release introduces pipeline snapshots and pipeline deployments, refactors the base package dependencies, and adds runtime environment variable support.

**New Features**

* **Pipeline Snapshots:** Capture immutable snapshots of pipeline code, configuration, and container images ([#3856](https://github.com/zenml-io/zenml/pull/3856)).
* **Pipeline Deployments:** Add a new Deployer stack component (Docker, AWS, GCP implementations) to deploy pipelines as HTTP endpoints ([#3920](https://github.com/zenml-io/zenml/pull/3920)).
* **Runtime Environment Variables:** Configure environment variables when running pipelines ([#3336](https://github.com/zenml-io/zenml/pull/3336)).
* **Dependency Management:** Reduced base package dependencies (moved local database dependencies to local package extra) ([#3916](https://github.com/zenml-io/zenml/pull/3916)).
* **Jax Support:** Add materializer for Jax arrays ([#3712](https://github.com/zenml-io/zenml/pull/3712)).

**Breaking Changes**

* Client-Server Compatibility: Not compatible with previous versions.
* Run Templates: Existing run templates need to be recreated.
* Base Package: The `zenml` package no longer includes local database dependencies. Install `zenml[local]` for local database support.

### 0.85.0

The 0.85.0 release delivers powerful pipeline execution enhancements and caching improvements.

**New Features**

* **Pipeline Execution Modes:** Flexible Failure Handling to configure what happens when a step fails ([#3874](https://github.com/zenml-io/zenml/pull/3874)).
* **Advanced Caching System:**
    * **Value-Based Caching:** Cache artifacts based on content/value rather than just artifact ID ([#3900](https://github.com/zenml-io/zenml/pull/3900)).
    * **Cache Policies:** Granular control over caching behavior.
* **Airflow 3.0 Support:** Compatibility with Apache Airflow 3.0 ([#3922](https://github.com/zenml-io/zenml/pull/3922)).

**Breaking Changes**

* Local Orchestrator Behavior: Continues executing steps after some steps fail.
* Docker Package Installer: Default switched from pip to uv ([#3935](https://github.com/zenml-io/zenml/pull/3935)).
* Log Endpoint Format: Log endpoints return a different format ([#3845](https://github.com/zenml-io/zenml/pull/3845)).

### 0.84.3

**New Features**

* **ZenML Pro Service Account Authentication:**
    * CLI Login Support via `zenml login --api-key` ([#3895](https://github.com/zenml-io/zenml/pull/3895)).
    * Service account API keys can be used for programmatic access.
    * Organization-Level Access for automated workflows ([#3908](https://github.com/zenml-io/zenml/pull/3908)).

**Fixes**

* **Kubernetes Integration:** Fixed resource name sanitization ([#3887](https://github.com/zenml-io/zenml/pull/3887)).
* **Dependencies:** Relaxed Click dependency version constraints ([#3905](https://github.com/zenml-io/zenml/pull/3905)).

### 0.84.2

**Improvements**

* **Kubernetes Orchestrator:** Complete rework to use Jobs instead of raw pods for better robustness and restarts ([#3869](https://github.com/zenml-io/zenml/pull/3869)).
* **Faster Pipeline Compilation:** Significantly improved performance for large pipelines ([#3873](https://github.com/zenml-io/zenml/pull/3873)).

**Fixes**

* Fixed deadlock in run creation ([#3876](https://github.com/zenml-io/zenml/pull/3876)).
* Enhanced path materializer security ([#3870](https://github.com/zenml-io/zenml/pull/3870)).
* Improved logging performance ([#3872](https://github.com/zenml-io/zenml/pull/3872)).
* Fixed WandB experiment tracker flavor initialization ([#3871](https://github.com/zenml-io/zenml/pull/3871)).

### 0.84.1

**New Features & Improvements**

* **Step Exception Handling:** Improved collection of exception info ([#3838](https://github.com/zenml-io/zenml/pull/3838)).
* **External Service Accounts:** Added support for external service accounts ([#3793](https://github.com/zenml-io/zenml/pull/3793)).
* **Kubernetes Orchestrator:** Added schedule management and better error handling ([#3847](https://github.com/zenml-io/zenml/pull/3847)).
* **Dynamic Fan-out/Fan-in:** Support for dynamic patterns with run templates ([#3826](https://github.com/zenml-io/zenml/pull/3826)).

**Fixes**

* Vertex step operator credential refresh ([#3853](https://github.com/zenml-io/zenml/pull/3853)).
* Logging race conditions ([#3855](https://github.com/zenml-io/zenml/pull/3855)).

### 0.84.0

This release delivers significant architectural improvements and orchestration enhancements.

**New Features**

* **Orchestration:**
    * Early Pipeline Stopping (Kubernetes orchestrator) ([#3716](https://github.com/zenml-io/zenml/pull/3716)).
    * Step Retries: Configurable retry mechanisms ([#3789](https://github.com/zenml-io/zenml/pull/3789)).
    * Step Status Refresh: Real-time status monitoring ([#3735](https://github.com/zenml-io/zenml/pull/3735)).
* **Kubernetes Orchestrator:**
    * Run steps using Jobs.
    * Enhanced Pod Management and Caching.
    * Orchestrator pod logs access ([#3778](https://github.com/zenml-io/zenml/pull/3778)).

**Breaking Changes**

* Kubernetes Orchestrator Compatibility: Client and orchestrator pod versions must match exactly.

### 0.83.1

**Performance Improvements**

* Separated step configurations from deployment ([#3739](https://github.com/zenml-io/zenml/pull/3739)).
* Idempotent POST requests with request caching ([#3738](https://github.com/zenml-io/zenml/pull/3738)).
* Enhanced artifact loading performance ([#3721](https://github.com/zenml-io/zenml/pull/3721)).

**Fixes**

* Fixed race conditions during pipeline run status updates ([#3720](https://github.com/zenml-io/zenml/pull/3720)).
* Fixed missing artifact nodes in DAG visualization ([#3727](https://github.com/zenml-io/zenml/pull/3727)).
* Fixed run template fetching issues ([#3726](https://github.com/zenml-io/zenml/pull/3726)).

### 0.83.0

Major Performance Release with significant response optimizations ([#3675](https://github.com/zenml-io/zenml/pull/3675)).

**Performance Improvements**

* Optimized API Responses: Reduced response sizes for large pipelines.
* Database Query Optimization.
* Reduced Response Payloads.

**Breaking Changes**

* Client/Server Compatibility: Not compatible with earlier versions.
* API Response Changes: Run responses no longer include unpaginated step lists or full metadata.

### 0.82.1

**Features**

* `pyproject.toml` support for configuring `DockerSettings` ([#3292](https://github.com/zenml-io/zenml/pull/3292)).
* Unique instance label in Helm chart ([#3639](https://github.com/zenml-io/zenml/pull/3639)).
* New stress-test example ([#3663](https://github.com/zenml-io/zenml/pull/3663)).

**Improvements**

* Cascading tags for cached step runs ([#3655](https://github.com/zenml-io/zenml/pull/3655)).
* Configurable Kubernetes job clean-up options ([#3644](https://github.com/zenml-io/zenml/pull/3644)).
* Limit to maximum number of concurrent template runs ([#3627](https://github.com/zenml-io/zenml/pull/3627)).

### 0.82.0

**Features**

* Max parallelism option for Kubernetes orchestrator ([#3606](https://github.com/zenml-io/zenml/pull/3606)).
* Customizable pod name prefixes and scheduler options ([#3591](https://github.com/zenml-io/zenml/pull/3591)).
* Private service connect option for Vertex AI ([#3613](https://github.com/zenml-io/zenml/pull/3613)).
* Configurable runner timeout ([#3589](https://github.com/zenml-io/zenml/pull/3589)).

**Improvements**

* Improved build invalidation when parent Dockerfile changes ([#3607](https://github.com/zenml-io/zenml/pull/3607)).
* Enhanced directory handling during code download ([#3609](https://github.com/zenml-io/zenml/pull/3609)).

### 0.81.0

**Features**

* **Path Materializer:** Upload directories and files ([#3496](https://github.com/zenml-io/zenml/pull/3496)).
* **Resource Sharing:** Enable sharing for teams and external users ([#3461](https://github.com/zenml-io/zenml/pull/3461)).
* **Client-side Logs Storage:** Store pipeline run logs in the artifact store ([#3498](https://github.com/zenml-io/zenml/pull/3498)).
* **Artifact Visualization:** Added `save_visualizations` method ([#3520](https://github.com/zenml-io/zenml/pull/3520)).

**Breaking Changes**

* Client-side log storage breaks pydantic model compatibility. Run templates must be rebuilt.

### 0.80.2

**Features**

* Added `poetry add` support for CLI ([#3470](https://github.com/zenml-io/zenml/pull/3470)).
* Added retry option on `step.with_options` ([#3499](https://github.com/zenml-io/zenml/pull/3499)).
* Added service annotations to helm chart ([#3482](https://github.com/zenml-io/zenml/pull/3482)).

**Fixes**

* Fixed yanked fsspec pip resolution issue ([#3493](https://github.com/zenml-io/zenml/pull/3493)).
* Fixed Kubernetes Orchestrator step pod failure status updates ([#3497](https://github.com/zenml-io/zenml/pull/3497)).

---

## ZenML Dashboard (OSS UI)

### v0.39.1

* **Fixes:** Remove Video Modal ([#943](https://github.com/zenml-io/zenml-dashboard/pull/943)), Update Dependencies (CVE) ([#945](https://github.com/zenml-io/zenml-dashboard/pull/945)), Adjust text-color ([#947](https://github.com/zenml-io/zenml-dashboard/pull/947)), Sanitize Dockerfile ([#948](https://github.com/zenml-io/zenml-dashboard/pull/948)).

### v0.39.0

* **Features:**
    * Display Deployment in Run Detail ([#919](https://github.com/zenml-io/zenml-dashboard/pull/919)).
    * Announcements Widget ([#926](https://github.com/zenml-io/zenml-dashboard/pull/926)).
    * Add Resize Observer to HTML Viz ([#928](https://github.com/zenml-io/zenml-dashboard/pull/928)).
    * Adjust Overview Pipelines ([#914](https://github.com/zenml-io/zenml-dashboard/pull/914)).
* **Fixes:** Fix Panel background ([#882](https://github.com/zenml-io/zenml-dashboard/pull/882)), Input Styling ([#911](https://github.com/zenml-io/zenml-dashboard/pull/911)), Display Schedules ([#879](https://github.com/zenml-io/zenml-dashboard/pull/879)).

### v0.38.0

* **New Features:**
    * **Deployment Playground:** Easier to invoke and test deployments ([#861](https://github.com/zenml-io/zenml-dashboard/pull/861)).
    * **Global Lists:** Centralized access for deployments ([#851](https://github.com/zenml-io/zenml-dashboard/pull/851)) and snapshots ([#854](https://github.com/zenml-io/zenml-dashboard/pull/854)).
    * **Create Snapshots:** Create snapshots directly from the dashboard ([#856](https://github.com/zenml-io/zenml-dashboard/pull/856)).
* **Misc:** GitHub-Flavored Markdown support ([#876](https://github.com/zenml-io/zenml-dashboard/pull/876)), Resizable Panels ([#873](https://github.com/zenml-io/zenml-dashboard/pull/873)).

### v0.37.0

* **New Features:**
    * **Pipeline Snapshots & Deployments:** Track entities introduced in ZenML 0.90.0 ([#814](https://github.com/zenml-io/zenml-dashboard/pull/814)).

### v0.36.0

* **New Features:**
    * **Timeline View:** New way to visualize pipeline runs alongside the DAG ([#799](https://github.com/zenml-io/zenml-dashboard/pull/799)).
* **Improvements:** Client-Side Structured Logs ([#801](https://github.com/zenml-io/zenml-dashboard/pull/801)), Default Value for Arrays ([#798](https://github.com/zenml-io/zenml-dashboard/pull/798)).

### v0.35.2

* **Fixes:** Default values ([#794](https://github.com/zenml-io/zenml-dashboard/pull/794)).

### v0.35.1

* **Fixes:** Fix Completed State ([#779](https://github.com/zenml-io/zenml-dashboard/pull/779)), Add First & Last Button to Logs ([#780](https://github.com/zenml-io/zenml-dashboard/pull/780)), Display Authors ([#782](https://github.com/zenml-io/zenml-dashboard/pull/782)), Refactor Node Details ([#783](https://github.com/zenml-io/zenml-dashboard/pull/783)).

### v0.35.0

* **Features:**
    * Refactor Onboarding ([#772](https://github.com/zenml-io/zenml-dashboard/pull/772)) & Survey ([#770](https://github.com/zenml-io/zenml-dashboard/pull/770)).
    * Stop Runs directly from dashboard ([#755](https://github.com/zenml-io/zenml-dashboard/pull/755)).
    * Step Refresh ([#773](https://github.com/zenml-io/zenml-dashboard/pull/773)).
    * Support multiple log origins ([#769](https://github.com/zenml-io/zenml-dashboard/pull/769)).
