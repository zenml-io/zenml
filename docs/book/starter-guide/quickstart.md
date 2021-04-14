---
jupytext:
  cell_metadata_filter: '-all'
  formats: 'md:myst'
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.12
    jupytext_version: 1.9.1
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Designing your first pipeline

In **ZenML**, a **pipeline** refers to a sequence of **steps** which represent independent entities that gets a certain set of inputs and creates the corresponding outputs as **artifacts**. These output **artifacts** can potentially be fed into other **steps** as inputs, and that’s how the order of execution is decided.

Each **artifact** that is produced along the way is stored in an **artifact store** and the corresponding execution is tracked by a **metadata store** associated with the **pipeline**. These artifacts can be fetched directly or via helper methods. For instance in a training pipeline,`view_statistics()` and `view_schema()` can be used as helper methods to easily view the artifacts from interim steps in a **pipeline**.

Finally, **ZenML** already natively separates configuration from code in its design. That means that every **step** in a **pipeline** has its parameters tracked and stored in the **declarative config file** in the selected **pipelines directory**. Therefore, pulling a pipeline and running it in another environment not only ensures that the code will be the same, but also the configuration.

## BasePipeline

All of the ideas above are brought together to construct the foundation of the `BasePipeline` in **ZenML**. As the name suggests, it is utilized as a base class to create, execute and track pipeline runs which represent a higher-order abstraction for standard ML tasks.

In many cases, the standard pipeline definitions can be used directly, and only the steps need to be manipulated. In general, you would only need to create your own Pipeline classes if you require a more flexible order of execution of the steps within the pipeline. **\[WIP\]**

{% hint style="info" %}
The mechanism to create a custom **pipeline** will be published in more detail soon in this space. However, the details of this are currently being worked out and will be made available in future releases.
{% endhint %}

## TrainingPipeline

The **`TrainingPipeline`** is a specialized pipeline built on top of the `BasePipeline` and it is used to run a training experiment and deploy the resulting model. It covers a fixed set of steps representing the processes, which can be found in most of the machine learning workflow:

\[STEP VISUALIZATION\]

* **Split**: responsible for splitting your dataset into smaller datasets such as train, eval, etc.
* **Sequence \(Optional\)**: responsible for extracting sequences from time-series data
* **Transform**: responsible for the preprocessing of your data
* **Train**: responsible for the model creation and training process
* **Evaluate**: responsible for the evaluation of your results
* **Deploy**: responsible for the model deployment

In code,

Additionally, there is a set of helper functions

```python
class TrainingPipeline(BasePipeline):
    # Step functions
    def add_split(self, split_step: BaseSplit):
        ...

    def add_sequencer(self, sequencer_step: BaseSequencerStep):
        ...

    def add_preprocesser(self, preprocessor_step: BasePreprocesserStep):
        ...

    def add_trainer(self, trainer_step: BaseTrainerStep):
        ...

    def add_evaluator(self, evaluator_step: BaseEvaluatorStep):
        ...

    def add_deployment(self, deployment_step: BaseDeployerStep):
        ...

    # Helper functions
    def view_statistics(self, magic: bool = False, port: int = 0):
        ...

    def view_schema(self):
        ...

    def evaluate(self, magic: bool = False, port: int = 0):
        ...

    def download_model(self, out_path: Text = None, overwrite: bool = False):
        ...

    def view_anomalies(self, split_name='eval'):
        ...
```

### Executing your pipeline

Now that everything is set, go ahead and run the pipeline, thus your steps.

```python
from zenml.pipelines import TrainingPipeline

training_pipeline = TrainingPipeline(name='MyFirstPipeline')

training_pipeline.add_datasource(ds)

training_pipeline.add_split(...)
training_pipeline.add_preprocesser(...)
training_pipeline.add_trainer(...)
training_pipeline.add_evaluator(...)

training_pipeline.run()
```

{% hint style="warning" %}
A ZenML pipeline in the current version is a higher-level abstraction of an opinionated TFX pipeline. ZenML Steps are in turn higher-level abstractions of TFX components. To be clear, currently ZenML is an easier way of defining and running TFX pipelines. However, unlike TFX, ZenML treats pipelines as first-class citizens. We will elaborate more on the difference in this space, but for now if you are coming from writing your own TFX pipelines, our quickstart illustrates the difference well.
{% endhint %}

## What's next?

* 
