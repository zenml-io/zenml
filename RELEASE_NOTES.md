# 0.5.0
This long-awaited ZenML release marks a seminal moment in the project's history. We present to you a complete 
revamp of the internals of ZenML, with a fresh new design and API. While these changes are significant, and have been months 
in the making, the original vision of ZenML has not wavered. We hope that the ZenML community finds the new 
design choices easier to grasp and use, and we welcome feedback on the [issues board](https://github.com/zenml-io/zenml/issues).

## Warning
0.5.0 is a complete API change from the previous versions of ZenML, and is a *breaking* upgrade. Fundamental 
concepts have been changed, and therefore backwards compatability is not maintained. Please use only this version 
with fresh projects.

With such significant changes, we expect this release to also be breaking. Please report any bugs in the issue board, and 
they should be addressed in upcoming releases.

## Overview

* Introducing a new functional API for creating pipelines and steps. This is now the default mechanism for building ZenML pipelines. [read more](https://docs.zenml.io/quickstart-guide)
* Steps now use Materializers to handle artifact serialization/deserialization between steps. This is a powerful change, and will be expanded upon in the future. [read more](https://docs.zenml.io/core/materializers)
* Introducing the new `Stack` paradigm: Easily transition from one MLOps stack to the next with a few CLI commands [read more](https://docs.zenml.io/core/stacks)
* Introducing a new `Artifact`, `Typing`, and `Annotation` system, with `pydantic` (and `dataclasses`) support [read more](https://docs.zenml.io/core/artifacts)
* Deprecating the `pipelines_dir`: Now individual pipelines will be stored in their metadata stores, making the metadata store a single source of truth. [read more](https://docs.zenml.io/core/stacks)
* Deprecating the YAML config file: ZenML no longer natively compiles to an intermediate YAML-based representation. Instead, it compiles and deploys directly into the selected orchestrator's 
representation. While we do plan to support running pipelines directly through YAML in the future, it will no longer be
the default route through which pipelines are run. [read more about orchestrators here](https://docs.zenml.io/core/stacks)

## Technical Improvements
* A completely new system design, please refer to the [docs](https://docs.zenml.io/core/core-concepts).
* Better type hints and docstrings.
* Auto-completion support.
* Numerous performance improvements and bug fixes, including a smaller dependency footprint.

## What to expect in the next weeks and the new ZenML
Currently, this release is bare bones. We are missing some basic features which used to be part of ZenML 0.3.8 (the previous release):

* Standard interfaces for `TrainingPipeline`.
* Individual step interfaces like `PreprocesserStep`, `TrainerStep`, `DeployerStep` etc. need to be rewritten from within the new paradigm. They should
be included in the non-RC version of this release.
* A proper production setup with an orchestrator like Airflow.
* A post-execution workflow to analyze and inspect pipeline runs.
* The concept of `Backends` will evolve into a simple mechanism of transitioning individual steps into different runners.
* Support for `KubernetesOrchestrator`, `KubeflowOrchestrator`, `GCPOrchestrator` and `AWSOrchestrator` are also planned.
* Dependency management including Docker support is planned.

[Our roadmap](https://docs.zenml.io/support/roadmap) goes into further detail on the timeline.

We encourage every user (old or new) to start afresh with this release. Please go over our latest [docs](https://docs.zenml.io) 
and [examples](examples) to get a hang of the new system.

Onwards and upwards to 1.0.0!

# 0.5.0rc2
This long-awaited ZenML release marks a seminal moment in the project's history. We present to you a complete 
revamp of the internals of ZenML, with a fresh new design and API. While these changes are significant, and have been months 
in the making, the original vision of ZenML has not wavered. We hope that the ZenML community finds the new 
design choices easier to grasp and use, and we welcome feedback on the [issues board](https://github.com/zenml-io/zenml/issues).

## Warning
0.5.0rc0 is a complete API change from the previous versions of ZenML, and is a *breaking* upgrade. Fundamental 
concepts have been changed, and therefore backwards compatability is not maintained. Please use only this version 
with fresh projects.

With such significant changes, we expect this release to also be breaking. Please report any bugs in the issue board, and 
they should be addressed in upcoming releases.

## Overview

* Introducing a new functional API for creating pipelines and steps. This is now the default mechanism for building ZenML pipelines. [read more](https://docs.zenml.io/quickstart-guide)
* Introducing the new `Stack` paradigm: Easily transition from one MLOps stack to the next with a few CLI commands [read more](https://docs.zenml.io/core/stacks)
* Introducing a new `Artifact`, `Typing`, and `Annotation` system, with `pydantic` (and `dataclasses`) support [read more](https://docs.zenml.io/core/artifacts)
* Deprecating the `pipelines_dir`: Now individual pipelines will be stored in their metadata stores, making the metadata store a single source of truth. [read more](https://docs.zenml.io/core/stacks)
* Deprecating the YAML config file: ZenML no longer natively compiles to an intermediate YAML-based representation. Instead, it compiles and deploys directly into the selected orchestrator's 
representation. While we do plan to support running pipelines directly through YAML in the future, it will no longer be
the default route through which pipelines are run. [read more about orchestrators here](https://docs.zenml.io/core/stacks)

## Technical Improvements
* A completely new system design, please refer to the [docs](https://docs.zenml.io/core/core-concepts).
* Better type hints and docstrings.
* Auto-completion support.
* Numerous performance improvements and bug fixes, including a smaller dependency footprint.

## What to expect in the next weeks and the new ZenML
Currently, this release is bare bones. We are missing some basic features which used to be part of ZenML 0.3.8 (the previous release):

* Standard interfaces for `TrainingPipeline`.
* Individual step interfaces like `PreprocesserStep`, `TrainerStep`, `DeployerStep` etc. need to be rewritten from within the new paradigm. They should
be included in the non-RC version of this release.
* A proper production setup with an orchestrator like Airflow.
* A post-execution workflow to analyze and inspect pipeline runs.
* The concept of `Backends` will evolve into a simple mechanism of transitioning individual steps into different runners.
* Support for `KubernetesOrchestrator`, `KubeflowOrchestrator`, `GCPOrchestrator` and `AWSOrchestrator` are also planned.
* Dependency management including Docker support is planned.

[Our roadmap](https://docs.zenml.io/support/roadmap) goes into further detail on the timeline.

We encourage every user (old or new) to start afresh with this release. Please go over our latest [docs](https://docs.zenml.io) 
and [examples](examples) to get a hang of the new system.

Onwards and upwards to 1.0.0!

# 0.3.7.1
This release fixes some known bugs from previous releases and especially 0.3.7. Same procedure as always, please delete existing pipelines, metadata, and artifact stores.

```
cd zenml_enabled_repo
rm -rf pipelines/
rm -rf .zenml/
```

And then another ZenML init:

```
pip install --upgrade zenml
cd zenml_enabled_repo
zenml init
```

## New Features
* Introduced new `zenml example` CLI sub-group: Easily pull examples via zenml to check it out.

```bash
zenml example pull # pulls all examples in `zenml_examples` directory
zenml example pull EXAMPLE_NAME  # pulls specific example
zenml example info EXAMPLE_NAME  # gives quick info regarding example
```  
Thanks Michael Xu for the suggestion!

* Updated examples with new `zenml examples` paradigm for examples.

## Bug Fixes + Refactor

* ZenML now works on Windows -> Thank you @Franky007Bond for the heads up.
* Updated numerous bugs in examples directory. Also updated README's.
* Fixed remote orchestration logic -> Now remote orchestration works.
* Changed datasource `to_config` to include reference to backend, metadata, and artifact store.


# 0.3.7
0.3.7 is a much-needed, long-awaited, big refactor of the Datasources paradigm of ZenML. There are also bug fixes, improvements, and more!

For those upgrading from an older version of ZenML, we ask to please delete their old `pipelines` dir and `.zenml` folders and start afresh with a `zenml init`.

If only working locally, this is as simple as:

```
cd zenml_enabled_repo
rm -rf pipelines/
rm -rf .zenml/
```

And then another ZenML init:

```
pip install --upgrade zenml
cd zenml_enabled_repo
zenml init
```

## New Features
* The inner-workings of the `BaseDatasource` have been modified along with the concrete implementations. Now, there is no relation between a `DataStep` and a `Datasource`: A `Datasource` holds all the logic to version and track itself via the new `commit` paradigm.

* Introduced a new interface for datasources, the `process` method which is responsible for ingesting data and writing to TFRecords to be consumed by later steps.

* Datasource versions (snapshots) can be accessed directly via the `commits` paradigm: Every commit is a new version of data.

* Added `JSONDatasource` and `TFRecordsDatasource`.

## Bug Fixes + Refactor
A big thanks to our new contributer @aak7912 for the help in this release with issue #71 and PR #75.

* Added an example for [regression](https://github.com/zenml-io/zenml/tree/main/examples/regression).
* `compare_training_runs()` now takes an optional `datasource` parameter to filter by datasource.
* `Trainer` interface refined to focus on `run_fn` rather than other helper functions.
* New docs released with a streamlined vision and coherent storyline: https://docs.zenml.io
* Got rid of unnecessary Torch dependency with base ZenML version.


# 0.3.6
0.3.6 is a more inwards-facing release as part of a bigger effort to create a more flexible ZenML. As a first step, ZenML now supports arbitrary splits for all components natively, freeing us from the `train/eval` split paradigm. Here is an overview of changes:

## New Features
* The inner-workings of the `BaseTrainerStep`, `BaseEvaluatorStep` and the `BasePreprocesserStep` have been modified along with their respective components to work with the new split_mapping. Now, users can define arbitrary splits (not just train/eval). E.g. Doing a `train/eval/test` split is possible.

* Within the instance of a `TrainerStep`, the user has access to `input_patterns` and `output_patterns` which provide the required uris with respect to their splits for the input and output(test_results) examples.

* The built-in trainers are modified to work with the new changes.

## Bug Fixes + Refactor
A big thanks to our new super supporter @zyfzjsc988 for most of the feedback that led to bug fixes and enhancements for this release: 

* #63: Now one can specify which ports ZenML opens its add-on applications.
* #64 Now there is a way to list integrations with the following code:
```
from zenml.utils.requirements_utils import list_integrations.
list_integrations()
```
* Fixed #61: `view_anomalies()` breaking in the quickstart.
* Analytics is now `opt-in` by default, to get rid of the unnecessary prompt at `zenml init`. Users can still freely `opt-out` by using the CLI:

```
zenml config analytics opt-out
```

Again, the telemetry data is fully anonymized and just used to improve the product. Read more [here](https://docs.zenml.io/misc/usage-analytics.html)

# 0.3.5

## New Features
* Added a new interface into the trainer step called [`test_fn`]() which is utilized to produce model predictions and save them as test results

* Implemented a new evaluator step called [`AgnosticEvaluator`]() which is designed to work regardless of the model type as long as you run the `test_fn` in your trainer step

* The first two changes allow torch trainer steps to be followed by an agnostic evaluator step, see the example [here]().

* Proposed a new naming scheme, which is now integrated into the built-in steps, in order to make it easier to handle feature/label names

* Implemented a new adapted version of 2 TFX components, namely the [`Trainer`]() and the [`Evaluator`]() to allow the aforementioned changes to take place

* Modified the [`TorchFeedForwardTrainer`]() to showcase how to use TensorBoard in conjunction with PyTorch


## Bug Fixes + Refactor
* Refactored how ZenML treats relative imports for custom steps. Now:
```python

```

* Updated the [Scikit Example](https://github.com/zenml-io/zenml/tree/main/examples/scikit), [PyTorch Lightning Example](https://github.com/zenml-io/zenml/tree/main/examples/pytorch_lightning), [GAN Example](https://github.com/zenml-io/zenml/tree/main/examples/gan) accordingly. Now they should work according to their README's.

Big shout out to @SarahKing92 in issue #34 for raising the above issues!


# 0.3.4
This release is a big design change and refactor. It involves a significant change in the Configuration file structure, meaning this is a **breaking upgrade**. 
For those upgrading from an older version of ZenML, we ask to please delete their old `pipelines` dir and `.zenml` folders and start afresh with a `zenml init`.

If only working locally, this is as simple as:

```
cd zenml_enabled_repo
rm -rf pipelines/
rm -rf .zenml/
```

And then another ZenML init:

```
pip install --upgrade zenml
cd zenml_enabled_repo
zenml init
```

## New Features
* Introduced another higher-level pipeline: The [NLPPipeline](https://github.com/zenml-io/zenml/blob/main/zenml/pipelines/nlp_pipeline.py). This is a generic 
  NLP pipeline for a text-datasource based training task. Full example of how to use the NLPPipeline can be found [here](https://github.com/zenml-io/zenml/tree/main/examples/nlp)
* Introduced a [BaseTokenizerStep](https://github.com/zenml-io/zenml/blob/main/zenml/steps/tokenizer/base_tokenizer.py) as a simple mechanism to define how to train and encode using any generic 
tokenizer (again for NLP-based tasks).

## Bug Fixes + Refactor
* Significant change to imports: Now imports are way simpler and user-friendly. E.g. Instead of:
```python
from zenml.core.pipelines.training_pipeline import TrainingPipeline
```

A user can simple do:

```python
from zenml.pipelines import TrainingPipeline
```

The caveat is of course that this might involve a re-write of older ZenML code imports.

Note: Future releases are also expected to be breaking. Until announced, please expect that upgrading ZenML versions may cause older-ZenML 
generated pipelines to behave unexpectedly. 
