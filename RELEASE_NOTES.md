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

* Updated the [Scikit Example](https://github.com/maiot-io/zenml/tree/main/examples/scikit), [PyTorch Lightning Example](https://github.com/maiot-io/zenml/tree/main/examples/pytorch_lightning), [GAN Example](https://github.com/maiot-io/zenml/tree/main/examples/gan) accordingly. Now they should work according to their README's.

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

Note: Future releases are also expected to be breaking. Until announced, please expect that upgrading ZenML versions may cause older-ZenML 
generated pipelines to behave unexpectedly. 