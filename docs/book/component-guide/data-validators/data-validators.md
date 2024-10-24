---
icon: chart-column
description: >-
  How to enhance and maintain the quality of your data and the performance of
  your models with data profiling and validation
---

# Data Validators

Without good data, even the best machine learning models will yield questionable results. A lot of effort goes into ensuring and maintaining data quality not only in the initial stages of model development, but throughout the entire machine learning project lifecycle. Data Validators are a category of ML libraries, tools and frameworks that grant a wide range of features and best practices that should be employed in the ML pipelines to keep data quality in check and to monitor model performance to keep it from degrading over time.

Data profiling, data integrity testing, data and model drift detection are all ways of employing data validation techniques at different points in your ML pipelines where data is concerned: data ingestion, model training and evaluation and online or batch inference. Data profiles and model performance evaluation results can be visualized and analyzed to detect problems and take preventive or correcting actions.

Related concepts:

* the Data Validator is an optional type of Stack Component that needs to be registered as part of your ZenML [Stack](broken-reference).
* Data Validators used in ZenML pipelines usually generate data profiles and data quality check reports that are versioned and stored in the [Artifact Store](../artifact-stores/artifact-stores.md) and can be [retrieved and visualized](broken-reference) later.

### When to use it

[Data-centric AI practices](https://blog.zenml.io/data-centric-mlops/) are quickly becoming mainstream and using Data Validators are an easy way to incorporate them into your workflow. These are some common cases where you may consider employing the use of Data Validators in your pipelines:

* early on, even if it's just to keep a log of the quality state of your data and the performance of your models at different stages of development.
* if you have pipelines that regularly ingest new data, you should use data validation to run regular data integrity checks to signal problems before they are propagated downstream.
* in continuous training pipelines, you should use data validation techniques to compare new training data against a data reference and to compare the performance of newly trained models against previous ones.
* when you have pipelines that automate batch inference or if you regularly collect data used as input in online inference, you should use data validation to run data drift analyses and detect training-serving skew, data drift and model drift.

#### Data Validator Flavors

Data Validator are optional stack components provided by integrations. The following table lists the currently available Data Validators and summarizes their features and the data types and model types that they can be used with in ZenML pipelines:

| Data Validator                              | Validation Features                                                   | Data Types                                                                                               | Model Types                                                                                   | Notes                                                                                               | Flavor/Integration   |
| ------------------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------- |
| [Deepchecks](deepchecks.md)                 | <p>data quality<br>data drift<br>model drift<br>model performance</p> | <p>tabular: <code>pandas.DataFrame</code><br>CV: <code>torch.utils.data.dataloader.DataLoader</code></p> | <p>tabular: <code>sklearn.base.ClassifierMixin</code><br>CV: <code>torch.nn.Module</code></p> | Add Deepchecks data and model validation tests to your pipelines                                    | `deepchecks`         |
| [Evidently](evidently.md)                   | <p>data quality<br>data drift<br>model drift<br>model performance</p> | tabular: `pandas.DataFrame`                                                                              | N/A                                                                                           | Use Evidently to generate a variety of data quality and data/model drift reports and visualizations | `evidently`          |
| [Great Expectations](great-expectations.md) | <p>data profiling<br>data quality</p>                                 | tabular: `pandas.DataFrame`                                                                              | N/A                                                                                           | Perform data testing, documentation and profiling with Great Expectations                           | `great_expectations` |
| [Whylogs/WhyLabs](whylogs.md)               | data drift                                                            | tabular: `pandas.DataFrame`                                                                              | N/A                                                                                           | Generate data profiles with whylogs and upload them to WhyLabs                                      | `whylogs`            |

If you would like to see the available flavors of Data Validator, you can use the command:

```shell
zenml data-validator flavor list
```

### How to use it

Every Data Validator has different data profiling and testing capabilities and uses a slightly different way of analyzing your data and your models, but it generally works as follows:

* first, you have to configure and add a Data Validator to your ZenML stack
* every integration includes one or more builtin data validation steps that you can add to your pipelines. Of course, you can also use the libraries directly in your own custom pipeline steps and simply return the results (e.g. data profiles, test reports) as artifacts that are versioned and stored by ZenML in its Artifact Store.
* you can access the data validation artifacts in subsequent pipeline steps, or [fetch them afterwards](broken-reference) to process them or visualize them as needed.

Consult the documentation for the particular [Data Validator flavor](data-validators.md#data-validator-flavors) that you plan on using or are using in your stack for detailed information about how to use it in your ZenML pipelines.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
