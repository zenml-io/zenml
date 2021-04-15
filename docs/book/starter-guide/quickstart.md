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

{% hint style="warning" %}
As of **0.3.6**, for end-to-end ML workflows, we are using the **`TrainingPipeline`** which is a specialized version of the **`BasePipeline`** with a **fixed set of configurable steps**. The mechanism to create a completely customized **pipeline** with a user-defined set of configurable steps will be published in more detail soon in this space. The details of this are currently being worked out and will be made available in future releases.
{% endhint %}

## TrainingPipeline

The **`TrainingPipeline`** is a specialized pipeline built on top of the **`BasePipeline`** and it is used to run a training experiment and deploy the resulting model. It covers a fixed set of steps representing the processes, which can be found in most of the machine learning workflows:

**\[TODO: STEP VISUALIZATION\]**

* **Split**: responsible for splitting your dataset into smaller datasets such as train, eval, etc.
* **Sequence \(Optional\)**: responsible for extracting sequences from time-series data
* **Transform**: responsible for the preprocessing of your data
* **Train**: responsible for the model creation and training process
* **Evaluate**: responsible for the evaluation of your results
* **Deploy**: responsible for the model deployment

**\[TODO: IMPLEMENTATION ASPECTS\]**

Additionally, it also features a set of helper functions, which makes it easier to interact with the output artifacts once the execution of the instance is completed. For instance, after the pipeline is executed, you can use `view_statistics` to take a deeper look into the statistics of your dataset/splits or you can use `download_model` to retrieve the trained model to a specified location.

{% hint style="info" %}
The following is an overview of the complete implementation. You can find the full code right [here](https://github.com/maiot-io/zenml/blob/main/zenml/pipelines/base_pipeline.py).
{% endhint %}

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

### Building and executing your pipeline

The code snippet below shows how quickly you can wrap up a `TrainingPipeline` and get it up and running. All you have to do is: 

1. Create an instance of a `TrainingPipeline`
2. Add a datasource to your instance
3. Add the desired steps along with their configuration
4. Simply run it

Most importantly, even when executing a simple example such as this, you maintain all the advantages that **ZenML** brings to the table such as reproducibility, scalability and collaboration to their full extent.  

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

{% hint style="info" %}
A **ZenML pipeline** in the current version is a higher-level abstraction of an opinionated TFX pipeline. **ZenML steps** are in turn higher-level abstractions of TFX components. Our goal is to make it easier for the users of **ZenML** to define and run TFX pipelines. Moreover, ZenML treats pipelines as first-class citizens. We will elaborate more on the difference in this space, but for now, if you are coming from writing your own TFX pipelines, our [quickstart example](https://github.com/maiot-io/zenml/tree/main/examples/quickstart) illustrates the difference well.
{% endhint %}

## What's next?

* If you would like to learn more about how to interact with pipelines in a ZenML repository, you can go [here](../advanced-guide/inspecting-all-pipelines.md).
* If you want to learn more about how to create the aforementioned datasource and steps, you can follow up on the documentation right [here](datasource.md).

