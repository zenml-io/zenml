---
description: Enhance and maintain the quality of your data and the performance of your models with data profiling and validation
---

Without good data, even the best machine learning models will yield questionable
results. A lot of effort goes into ensuring and maintaining data quality not
only in the initial stages of model development, but throughout the entire
machine learning project lifecycle. Data Validators are a category of ML
libraries, tools and frameworks that grant a wide range of features and best
practices that should be employed in the ML pipelines to keep data quality in
check and to prevent model performance from degrading over time.

Data profiling, data integrity testing, data and model drift detection
are all ways of employing data validation techniques at different points in your
ML pipelines where data is concerned: data ingestion, model training and
evaluation and online or batch inference. Data profiles and data quality check
results can be visualized and analyzed to detect problems and take course
correcting actions before they can negatively impact the model performance.

Related concepts:

* the Data Validator is an optional type of Stack Component that needs to be
registered as part of your ZenML [Stack](../../developer-guide/stacks-profiles-repositories/stack.md).
* Data Validators used in ZenML pipelines usually generate data profiles and
data quality check reports that are versioned and stored in the [Artifact Store](../artifact-stores/artifact-stores.md).
They can be retrieved and inspected using [the post-execution workflow API](../../developer-guide/steps-pipelines/inspecting-pipeline-runs.md).

## When to use it

[Data-centric AI practices](https://blog.zenml.io/data-centric-mlops/) are
quickly becoming mainstream and using Data Validators are an easy way to
incorporate them into your workflow. These are some common cases where you
may consider employing the use of Data Validators in your pipelines:

* early on, even if it's just to keep a log of the quality state of your
data at different stages of development.
* if you have pipelines that regularly ingest new data, you should use data
validation to run regular data integrity checks on it to signal problems before
they are propagated downstream.
* if you train models in your pipelines, you should use data validation to
run data comparison analyses of your train and test data to make sure your
model is properly evaluated.
* when you have pipelines that automate batch inference or if you regularly
collect data used as input in online inference, you should use data validation
to run data drift analyses and detect training-serving skew and model drift.

### Data Validator Flavors

Data Validator are optional stack components provided by integrations:

| Data Validator | Flavor | Integration | Notes             |
|----------------|--------|-------------|-----------------------|
| [Deepchecks](./deepchecks.md) | `deepchecks` | `deepchecks` | Add Deepchecks data validation tests to your pipelines, from data integrity checks that work with a single dataset to data+model evaluation to data drift analyses |
| [Evidently](./evidently.md) | `evidently` | `evidently` | Use Evidently to generate a variety of data quality and data drift profiles |
| [Great Expectations](./great_expectations.md) | `great_expectations` | `great_expectations` | Perform data testing, documentation and profiling with Great Expectations |
| [Whylogs/WhyLabs](./whylogs.md) | `whylogs` | `whylogs` | Generate data profiles with whylogs and upload them to WhyLabs |

If you would like to see the available flavors of Experiment Tracker, you can 
use the command:

```shell
zenml data-validator flavor list
```
## How to use it

Every Data Validator has different data profiling and testing capabilities and
uses a slightly different way of analyzing your data, but it generally works
as follows:

* first, you have to configure and add an Data Validator to your ZenML stack
* every integration includes one or more builtin data validation steps that you
can add to your pipelines. Of course, you can also use the libraries directly in
your own custom pipeline steps and simply return the results (e.g. data profiles,
test reports) as artifacts that are versioned and stored by ZenML in its Artifact
Store.
* you can access the data validation artifacts in subsequent pipeline steps or
you can load them in the [the post-execution workflow](../../developer-guide/steps-pipelines/inspecting-pipeline-runs.md) to visualize them as needed.

Consult the documentation for the particular [Data Validator flavor](#data-validator-flavors)
that you plan on using or are using in your stack for detailed information about
how to use it in your ZenML pipelines.
