# Changelogs

## 0.3.7

0.3.7 is a much-needed, long-awaited, big refactor of the Datasources paradigm of ZenML. There are also bug fixes, improvements, and more!

For those upgrading from an older version of ZenML, we ask to please delete their old `pipelines` dir and `.zenml` folders and start afresh with a `zenml init`.

If only working locally, this is as simple as:

```text
cd zenml_enabled_repo
rm -rf pipelines/
rm -rf .zenml/
```

And then another ZenML init:

```text
pip install --upgrade zenml
cd zenml_enabled_repo
zenml init
```

### New Features

* The inner-workings of the `BaseDatasource` have been modified along with the concrete implementations. Now, there is no relation between a `DataStep` and a `Datasource`: A `Datasource` holds all the logic to version and track itself via the new `commit` paradigm.
* Introduced a new interface for datasources, the `process` method which is responsible for ingesting data and writing to TFRecords to be consumed by later steps.
* Datasource versions \(snapshots\) can be accessed directly via the `commits` paradigm: Every commit is a new version of data.
* Added `JSONDatasource` and `TFRecordsDatasource`.

### Bug Fixes + Refactor

A big thanks to our new contributer @aak7912 for the help in this release with issue \#71 and PR \#75.

* Added an example for [regression](https://github.com/maiot-io/zenml/tree/main/examples/regression).
* `compare_training_runs()` now takes an optional `datasource` parameter to filter by datasource.
* `Trainer` interface refined to focus on `run_fn` rather than other helper functions.
* New docs released with a streamlined vision and coherent storyline: [https://docs.zenml.io](https://docs.zenml.io)
* Got rid of unnecessary Torch dependency with base ZenML version.

## 0.3.6

0.3.6 is a more inwards-facing release as part of a bigger effort to create a more flexible ZenML. As a first step, ZenML now supports arbitrary splits for all components natively, freeing us from the `train/eval` split paradigm. Here is an overview of changes:

### New Features

* The inner-workings of the `BaseTrainerStep`, `BaseEvaluatorStep` and the `BasePreprocesserStep` have been modified along with their respective components to work with the new split\_mapping. Now, users can define arbitrary splits \(not just train/eval\). E.g. Doing a `train/eval/test` split is possible.
* Within the instance of a `TrainerStep`, the user has access to `input_patterns` and `output_patterns` which provide the required uris with respect to their splits for the input and output\(test\_results\) examples.
* The built-in trainers are modified to work with the new changes.

### Bug Fixes + Refactor

A big thanks to our new super supporter @zyfzjsc988 for most of the feedback that led to bug fixes and enhancements for this release:

* **63: Now one can specify which ports ZenML opens its add-on applications.**
* **64 Now there is a way to list integrations with the following code:**

  ```text
  from zenml.utils.requirements_utils import list_integrations.
  list_integrations()
  ```

* Fixed \#61: `view_anomalies()` breaking in the quickstart.
* Analytics is now `opt-in` by default, to get rid of the unnecessary prompt at `zenml init`. Users can still freely `opt-out` by using the CLI:

```text
zenml config analytics opt-out
```

Again, the telemetry data is fully anonymized and just used to improve the product. Read more [here](https://docs.zenml.io/misc/usage-analytics.html)

## 0.3.5

### New Features

* Added a new interface into the trainer step called [`test_fn`](release_notes.md) which is utilized to produce model predictions and save them as test results
* Implemented a new evaluator step called [`AgnosticEvaluator`](release_notes.md) which is designed to work regardless of the model type as long as you run the `test_fn` in your trainer step
* The first two changes allow torch trainer steps to be followed by an agnostic evaluator step, see the example [here](release_notes.md).
* Proposed a new naming scheme, which is now integrated into the built-in steps, in order to make it easier to handle feature/label names
* Implemented a new adapted version of 2 TFX components, namely the [`Trainer`](release_notes.md) and the [`Evaluator`](release_notes.md) to allow the aforementioned changes to take place
* Modified the [`TorchFeedForwardTrainer`](release_notes.md) to showcase how to use TensorBoard in conjunction with PyTorch

### Bug Fixes + Refactor

* Refactored how ZenML treats relative imports for custom steps. Now:

  \`\`\`python

```text
* Updated the [Scikit Example](https://github.com/maiot-io/zenml/tree/main/examples/scikit), [PyTorch Lightning Example](https://github.com/maiot-io/zenml/tree/main/examples/pytorch_lightning), [GAN Example](https://github.com/maiot-io/zenml/tree/main/examples/gan) accordingly. Now they should work according to their README's.

Big shout out to @SarahKing92 in issue #34 for raising the above issues!


# 0.3.4
This release is a big design change and refactor. It involves a significant change in the Configuration file structure, meaning this is a **breaking upgrade**. 
For those upgrading from an older version of ZenML, we ask to please delete their old `pipelines` dir and `.zenml` folders and start afresh with a `zenml init`.

If only working locally, this is as simple as:
```

cd zenml\_enabled\_repo rm -rf pipelines/ rm -rf .zenml/

```text
And then another ZenML init:
```

pip install --upgrade zenml cd zenml\_enabled\_repo zenml init

```text
## New Features
* Introduced another higher-level pipeline: The [NLPPipeline](https://github.com/maiot-io/zenml/blob/main/zenml/pipelines/nlp_pipeline.py). This is a generic 
  NLP pipeline for a text-datasource based training task. Full example of how to use the NLPPipeline can be found [here](https://github.com/maiot-io/zenml/tree/main/examples/nlp)
* Introduced a [BaseTokenizerStep](https://github.com/maiot-io/zenml/blob/main/zenml/steps/tokenizer/base_tokenizer.py) as a simple mechanism to define how to train and encode using any generic 
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

Note: Future releases are also expected to be breaking. Until announced, please expect that upgrading ZenML versions may cause older-ZenML generated pipelines to behave unexpectedly.

