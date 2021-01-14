# Introduction

## What is ZenML?
**ZenML** is an extensible, open-source MLOps framework for using production-ready Machine Learning pipelines - in a simple way. 

## Why do I need ZenML?
ZenML exists to solve the following problems in Machine Learning development. This includes facing difficulties with:

* **Reproducing** training results in production.
* Managing ML **metadata**, including data, code, and model versioning.
* Getting (and keeping) ML models in **production**.
* **Reusing** code/data and reducing waste.
* Maintaining **comparability** between ML models.
* **Scaling ML** training/inference to large datasets.
* Retaining code **quality** alongside development velocity.
* Keeping up with the ML **tooling landscape** in a coherent manner.

## When should use ZenML?
Talk here about the timing in the ML journey. Whether at the very start or at 'day 2'.

## Key Features
If you/your team struggle with ZenML struggle with the above problems, ZenML solves them via:

* **Guaranteed reproducibility** of your training experiments. Your pipelines are versioned from data to model, 
  experiments automatically tracked and all pipeline configs are **declarative** by default.
* **Automatic tracking** of ML metadata. All runs are tracked in a human-readable, immutable, declarative config.
* **Version** data, code, and models in one simple interface.
* **Re-use** code and interim artifacts across experiments and users.
* Guaranteed **comparability** between experiments.
* Ability to quickly switch between **local and cloud environments \(e.g. Kubernetes\)**.
* Easily **integrate** with all popular tools including Git, Apache Beam, Kubernetes, PyTorch, TensorFlow.


## Detailed list of benefits
If the above benefits were too high-level or vague, here is a list of all benefits in concrete terms.

### The Data science side
* Run ML code in the cloud with one command.
  * Run preprocessing and training on big VM's on the cloud without setting it up.
  * Train automatically on GPUs just by setting a flag.
  * Launch preemptible/spot instances to reduce cost of experimentation by 1/4.
* Distribute preprocessing without having to learn complex distributed paradigms.
  * ZenML automatically scales your code to potentially hundreds of workers for millions of datapoints.
* Organize and version code.
  * Re-use code steps between pipeline steps.
* Version data automatically. Each step automatically produces a snapshot of the result.
* Track metadata like hyper-parameters of a model automatically.
  * Persisted in the SQL ML Metadata database defined by Google.
  * Complete provenance of what processing step results in what step.
  * Never lose track of where interim artifacts are stored.
* Combining above two points allows for warm-starting pipeline with caching of pipeline steps.
* Compare results of pipeline runs using the compare tool.
* Automatically evaluate models using integrations such as Tensorboard and Tensorflow Model Analysis.

### The Ops side
* Infrastructure is a first-class citizen defined within the system.
  * Backends to define `where` and `how` pipelines are executed.
* Separate code from configuration.
* Each ML experiment is stored in a human-friendly, declarative YAMl config, that is natively executable via CLI.
* All pipelines are reproducible. All code is versioned and pipeline artifacts are linked directly to commit sha's.
* Scale to the cloud using easy template docker images.
* Easy integration into CI/CD paradigm with CLI capability.

## What to do next?
* Get up and running with your first pipeline [with the Quickstart](getting-started/quickstart.md).
* Read more about [core concepts](getting-started/core-concepts.md) to inform your decision about using ZenML.
* Check out how to [convert your old ML code](getting-started/organizing-zenml.md) into ZenML pipelines, or start from scratch with our [tutorials](tutorials/creating-first-pipeline.ipynb)
* If you are working as a team, see how to [collaborate using ZenML in a team setting](repository/team-collaboration-with-zenml.md).
