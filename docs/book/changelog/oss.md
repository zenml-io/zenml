---
description: Changelog for ZenML OSS and ZenML UI.
icon: clock-rotate-left
---

# ZenML OSS Changelog

Stay up to date with the latest features, improvements, and fixes in ZenML OSS.

## 0.91.2

See what's new and improved in version 0.91.2.

<img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/1.jpg" align="left" alt="ZenML 0.91.2" width="800">

#### Kubernetes Deployer

* Deploy your pipelines directly on Kubernetes
* Full integration with Kubernetes orchestrator

[Learn more](https://docs.zenml.io/component-guide/deployers/kubernetes) | [PR #4127](https://github.com/zenml-io/zenml/pull/4127)

#### MLflow 3.0 Support

* Added support for the latest MLflow version
* Improved compatibility with modern MLflow features

[PR #4160](https://github.com/zenml-io/zenml/pull/4160)

#### S3 Artifact Store Fixes

* Fixed compatibility with custom S3 backends
* Improved SSL certificate handling for RestZenStore
* Enhanced Weights & Biases experiment tracker reliability

#### UI Updates

* Remove Video Modal ([#943](https://github.com/zenml-io/zenml-dashboard/pull/943))
* Update Dependencies (CVE) ([#945](https://github.com/zenml-io/zenml-dashboard/pull/945))
* Adjust text-color ([#947](https://github.com/zenml-io/zenml-dashboard/pull/947))
* Sanitize Dockerfile ([#948](https://github.com/zenml-io/zenml-dashboard/pull/948))

<details>
<summary>Fixed</summary>

* S3 artifact store now works with custom backends ([#4186](https://github.com/zenml-io/zenml/pull/4186))
* SSL certificate passing for RestZenStore ([#4188](https://github.com/zenml-io/zenml/pull/4188))
* Weights & Biases tag length limitations ([#4189](https://github.com/zenml-io/zenml/pull/4189))

</details>

***
## 0.91.1

See what's new and improved in version 0.91.1.

<img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/2.jpg" align="left" alt="ZenML 0.91.1" width="800">

#### Hugging Face Deployer

* Deploy pipelines directly to Hugging Face Spaces
* Seamless integration with Hugging Face infrastructure

[Learn more](https://docs.zenml.io/component-guide/deployers/huggingface) | [PR #4119](https://github.com/zenml-io/zenml/pull/4119)

#### Dynamic Pipelines (Experimental)

* Introduced v1 of dynamic pipelines
* Early feedback welcome for this experimental feature

[Read the documentation](https://docs.zenml.io/how-to/steps-pipelines/dynamic_pipelines) | [PR #4074](https://github.com/zenml-io/zenml/pull/4074)

#### Kubernetes Orchestrator Enhancements

* Container security context configuration
* Skip owner references option
* Improved deployment reliability

#### UI Updates

* Display Deployment in Run Detail ([#919](https://github.com/zenml-io/zenml-dashboard/pull/919))
* Announcements Widget ([#926](https://github.com/zenml-io/zenml-dashboard/pull/926))
* Add Resize Observer to HTML Viz ([#928](https://github.com/zenml-io/zenml-dashboard/pull/928))
* Adjust Overview Pipelines ([#914](https://github.com/zenml-io/zenml-dashboard/pull/914))
* Fix Panel background ([#882](https://github.com/zenml-io/zenml-dashboard/pull/882))
* Input Styling ([#911](https://github.com/zenml-io/zenml-dashboard/pull/911))
* Display Schedules ([#879](https://github.com/zenml-io/zenml-dashboard/pull/879))

<details>
<summary>Improved</summary>

* Enhanced Kubernetes orchestrator with container security context options ([#4142](https://github.com/zenml-io/zenml/pull/4142))
* Better handling of owner references in Kubernetes deployments ([#4146](https://github.com/zenml-io/zenml/pull/4146))
* Expanded HashiCorp Vault secret store authentication methods ([#4110](https://github.com/zenml-io/zenml/pull/4110))
* Support for newer Databricks versions ([#4144](https://github.com/zenml-io/zenml/pull/4144))

</details>

<details>
<summary>Fixed</summary>

* Port reuse for local deployments
* Parallel deployment invocations
* Keyboard interrupt handling during monitoring
* Case-sensitivity issues when updating entity names ([#4140](https://github.com/zenml-io/zenml/pull/4140))

</details>

***
## 0.91.0

See what's new and improved in version 0.91.0.

<img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/3.jpg" align="left" alt="ZenML 0.91.0" width="800">

#### Local Deployer

* Deploy pipelines locally with full control
* Perfect for development and testing workflows

[Learn more](https://docs.zenml.io/component-guide/deployers/local) | [PR #4085](https://github.com/zenml-io/zenml/pull/4085)

#### Advanced Caching System

* File and object-based cache invalidation
* Cache expiration for bounded lifetime
* Custom cache functions for advanced logic

[Read the documentation](https://docs.zenml.io/how-to/steps-pipelines/advanced_features) | [PR #4040](https://github.com/zenml-io/zenml/pull/4040)

#### Deployment Visualizations

* Attach custom visualizations to deployments
* Fully customizable deployment server settings
* Enhanced deployment management

[PR #4016](https://github.com/zenml-io/zenml/pull/4016) | [PR #4064](https://github.com/zenml-io/zenml/pull/4064)

#### Python 3.13 Support

* Full compatibility with Python 3.13
* MLX array materializer for Apple Silicon

[PR #4053](https://github.com/zenml-io/zenml/pull/4053) | [PR #4027](https://github.com/zenml-io/zenml/pull/4027)

#### UI Updates

* **Deployment Playground:** Easier to invoke and test deployments ([#861](https://github.com/zenml-io/zenml-dashboard/pull/861))
* **Global Lists:** Centralized access for deployments ([#851](https://github.com/zenml-io/zenml-dashboard/pull/851)) and snapshots ([#854](https://github.com/zenml-io/zenml-dashboard/pull/854))
* **Create Snapshots:** Create snapshots directly from the UI ([#856](https://github.com/zenml-io/zenml-dashboard/pull/856))
* GitHub-Flavored Markdown support ([#876](https://github.com/zenml-io/zenml-dashboard/pull/876))
* Resizable Panels ([#873](https://github.com/zenml-io/zenml-dashboard/pull/873))

<details>
<summary>Improved</summary>

* Customizable image tags for Docker builds ([#4025](https://github.com/zenml-io/zenml/pull/4025))
* Enhanced deployment server configuration ([#4064](https://github.com/zenml-io/zenml/pull/4064))
* Better integration with MLX arrays ([#4027](https://github.com/zenml-io/zenml/pull/4027))

</details>

<details>
<summary>Fixed</summary>

* Print capturing incompatibility with numba ([#4060](https://github.com/zenml-io/zenml/pull/4060))
* Hashicorp Vault secrets store mount point configuration ([#4088](https://github.com/zenml-io/zenml/pull/4088))

</details>

### Breaking Changes

* Dropped Python 3.9 support - upgrade to Python 3.10+ ([#4053](https://github.com/zenml-io/zenml/pull/4053))
## 0.90.0

See what's new and improved in version 0.90.0.

<img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/4.jpg" align="left" alt="ZenML 0.90.0" width="800">

#### Pipeline Snapshots & Deployments

* Capture immutable snapshots of pipeline code and configuration
* Deploy pipelines as HTTP endpoints for online inference
* Docker, AWS, and GCP deployer implementations

[Learn more about Snapshots](https://docs.zenml.io/how-to/snapshots/snapshots) | [Learn more about Deployments](https://docs.zenml.io/how-to/deployment/deployment)

[PR #3856](https://github.com/zenml-io/zenml/pull/3856) | [PR #3920](https://github.com/zenml-io/zenml/pull/3920)

#### Runtime Environment Variables

* Configure environment variables when running pipelines
* Support for ZenML secrets in runtime configuration

[PR #3336](https://github.com/zenml-io/zenml/pull/3336)

#### Dependency Management Improvements

* Reduced base package dependencies
* Local database dependencies moved to `zenml[local]` extra
* JAX array materializer support

[PR #3916](https://github.com/zenml-io/zenml/pull/3916) | [PR #3712](https://github.com/zenml-io/zenml/pull/3712)

#### UI Updates

* **Pipeline Snapshots & Deployments:** Track entities introduced in ZenML 0.90.0 ([#814](https://github.com/zenml-io/zenml-dashboard/pull/814))

<details>
<summary>Improved</summary>

* Slimmer base package for faster installations ([#3916](https://github.com/zenml-io/zenml/pull/3916))
* Better dependency management
* Enhanced JAX integration ([#3712](https://github.com/zenml-io/zenml/pull/3712))

</details>

### Breaking Changes

* Client-Server compatibility: Must upgrade both simultaneously
* Run templates need to be recreated
* Base package no longer includes local database dependencies - install `zenml[local]` if needed ([#3916](https://github.com/zenml-io/zenml/pull/3916))
## 0.85.0

See what's new and improved in version 0.85.0.

<img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/5.jpg" align="left" alt="ZenML 0.85.0" width="800">

#### Pipeline Execution Modes

* Flexible failure handling configuration
* Control what happens when steps fail
* Better pipeline resilience

[Read the documentation](https://docs.zenml.io/how-to/steps-pipelines/advanced_features) | [PR #3874](https://github.com/zenml-io/zenml/pull/3874)

#### Value-Based Caching

* Cache artifacts based on content/value, not just ID
* More intelligent cache reuse
* Cache policies for granular control

[PR #3900](https://github.com/zenml-io/zenml/pull/3900)

#### Airflow 3.0 Support

* Full compatibility with Apache Airflow 3.0
* Access to latest Airflow features and improvements

[PR #3922](https://github.com/zenml-io/zenml/pull/3922)

#### UI Updates

* **Timeline View:** New way to visualize pipeline runs alongside the DAG ([#799](https://github.com/zenml-io/zenml-dashboard/pull/799))
* Client-Side Structured Logs ([#801](https://github.com/zenml-io/zenml-dashboard/pull/801))
* Default Value for Arrays ([#798](https://github.com/zenml-io/zenml-dashboard/pull/798))

<details>
<summary>Improved</summary>

* Enhanced caching system with value-based caching ([#3900](https://github.com/zenml-io/zenml/pull/3900))
* More granular cache policy control
* Better pipeline execution control ([#3874](https://github.com/zenml-io/zenml/pull/3874))

</details>

### Breaking Changes

* Local orchestrator now continues execution after step failures
* Docker package installer default switched from pip to uv ([#3935](https://github.com/zenml-io/zenml/pull/3935))
* Log endpoint format changed ([#3845](https://github.com/zenml-io/zenml/pull/3845))
## 0.84.3

See what's new and improved in version 0.84.3.

<img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/6.jpg" align="left" alt="ZenML 0.84.3" width="800">

#### ZenML Pro Service Account Authentication

* CLI login support via `zenml login --api-key`
* Service account API keys for programmatic access
* Organization-level access for automated workflows

[PR #3895](https://github.com/zenml-io/zenml/pull/3895) | [PR #3908](https://github.com/zenml-io/zenml/pull/3908)

#### ZenML Pro Service Account Authentication

* CLI login support via `zenml login --api-key`
* Service account API keys for programmatic access
* Organization-level access for automated workflows

[PR #3895](https://github.com/zenml-io/zenml/pull/3895) | [PR #3908](https://github.com/zenml-io/zenml/pull/3908)

<details>
<summary>Improved</summary>

* Enhanced Kubernetes resource name sanitization ([#3887](https://github.com/zenml-io/zenml/pull/3887))
* Relaxed Click dependency version constraints ([#3905](https://github.com/zenml-io/zenml/pull/3905))

</details>## 0.84.2

See what's new and improved in version 0.84.2.

<img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/7.jpg" align="left" alt="ZenML 0.84.2" width="800">

#### Kubernetes Orchestrator Improvements

* Complete rework using Jobs instead of raw pods
* Better robustness and automatic restarts
* Significantly faster pipeline compilation

[PR #3869](https://github.com/zenml-io/zenml/pull/3869) | [PR #3873](https://github.com/zenml-io/zenml/pull/3873)

#### Kubernetes Orchestrator Improvements

* Complete rework using Jobs instead of raw pods
* Better robustness and automatic restarts
* Significantly faster pipeline compilation

[PR #3869](https://github.com/zenml-io/zenml/pull/3869) | [PR #3873](https://github.com/zenml-io/zenml/pull/3873)

<details>
<summary>Improved</summary>

* Enhanced Kubernetes orchestrator robustness ([#3869](https://github.com/zenml-io/zenml/pull/3869))
* Faster pipeline compilation for large pipelines ([#3873](https://github.com/zenml-io/zenml/pull/3873))
* Better logging performance ([#3872](https://github.com/zenml-io/zenml/pull/3872))

</details>## 0.84.1

See what's new and improved in version 0.84.1.

<img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/8.jpg" align="left" alt="ZenML 0.84.1" width="800">

#### Step Exception Handling

* Improved collection of exception information
* Better debugging capabilities

[PR #3838](https://github.com/zenml-io/zenml/pull/3838)

#### External Service Accounts

* Added support for external service accounts
* Improved flexibility

[PR #3793](https://github.com/zenml-io/zenml/pull/3793)

#### Kubernetes Orchestrator Enhancements

* Schedule management capabilities
* Better error handling
* Enhanced pod monitoring

[PR #3847](https://github.com/zenml-io/zenml/pull/3847)

#### Dynamic Fan-out/Fan-in

* Support for dynamic patterns with run templates
* More flexible pipeline architectures

[PR #3826](https://github.com/zenml-io/zenml/pull/3826)

#### Step Exception Handling

* Improved collection of exception information
* Better debugging capabilities

[PR #3838](https://github.com/zenml-io/zenml/pull/3838)

#### External Service Accounts

* Added support for external service accounts
* Improved flexibility

[PR #3793](https://github.com/zenml-io/zenml/pull/3793)

#### Kubernetes Orchestrator Enhancements

* Schedule management capabilities
* Better error handling
* Enhanced pod monitoring

[PR #3847](https://github.com/zenml-io/zenml/pull/3847)

#### Dynamic Fan-out/Fan-in

* Support for dynamic patterns with run templates
* More flexible pipeline architectures

[PR #3826](https://github.com/zenml-io/zenml/pull/3826)

<details>
<summary>Fixed</summary>

* Vertex step operator credential refresh ([#3853](https://github.com/zenml-io/zenml/pull/3853))
* Logging race conditions ([#3855](https://github.com/zenml-io/zenml/pull/3855))
* Kubernetes secret cleanup when orchestrator pods fail ([#3846](https://github.com/zenml-io/zenml/pull/3846))

</details>## 0.84.0

See what's new and improved in version 0.84.0.

<img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/9.jpg" align="left" alt="ZenML 0.84.0" width="800">

#### Early Pipeline Stopping

* Stop pipelines early with Kubernetes orchestrator
* Better resource management

[PR #3716](https://github.com/zenml-io/zenml/pull/3716)

#### Step Retries

* Configurable step retry mechanisms
* Improved pipeline resilience

[PR #3789](https://github.com/zenml-io/zenml/pull/3789)

#### Step Status Refresh

* Real-time status monitoring
* Enhanced step status refresh capabilities

[PR #3735](https://github.com/zenml-io/zenml/pull/3735)

#### Performance Improvements

* Thread-safe RestZenStore operations
* Server-side processing improvements
* Enhanced pipeline/step run fetching

[PR #3758](https://github.com/zenml-io/zenml/pull/3758) | [PR #3762](https://github.com/zenml-io/zenml/pull/3762) | [PR #3776](https://github.com/zenml-io/zenml/pull/3776)

#### UI Updates

* Refactor Onboarding ([#772](https://github.com/zenml-io/zenml-dashboard/pull/772)) & Survey ([#770](https://github.com/zenml-io/zenml-dashboard/pull/770))
* Stop Runs directly from UI ([#755](https://github.com/zenml-io/zenml-dashboard/pull/755))
* Step Refresh ([#773](https://github.com/zenml-io/zenml-dashboard/pull/773))
* Support multiple log origins ([#769](https://github.com/zenml-io/zenml-dashboard/pull/769))

<details>
<summary>Improved</summary>

* New ZenML login experience ([#3790](https://github.com/zenml-io/zenml/pull/3790))
* Enhanced Kubernetes orchestrator pod caching ([#3719](https://github.com/zenml-io/zenml/pull/3719))
* Easier step operator/experiment tracker configuration ([#3774](https://github.com/zenml-io/zenml/pull/3774))
* Orchestrator pod logs access ([#3778](https://github.com/zenml-io/zenml/pull/3778))

</details>

<details>
<summary>Fixed</summary>

* Fixed model version fetching by UUID ([#3777](https://github.com/zenml-io/zenml/pull/3777))
* Visualization handling improvements ([#3769](https://github.com/zenml-io/zenml/pull/3769))
* Fixed data artifact fetching ([#3811](https://github.com/zenml-io/zenml/pull/3811))
* Path and Docker tag sanitization ([#3816](https://github.com/zenml-io/zenml/pull/3816) | [#3820](https://github.com/zenml-io/zenml/pull/3820))

</details>

### Breaking Changes

* Kubernetes Orchestrator Compatibility: Client and orchestrator pod versions must match exactly
