---
description: Validate data as it flows through your pipelines
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


In academia and research, the focus of ML is usually to build the best possible models for a given dataset. However, in practical applications, the overall performance of our application is often determined primarily by data quality, not by the model. That is why many ML practitioners advocate for **Data-Centric** ML approaches, where we focus on improving the data while keeping the ML model (mostly) fixed. See [this great article](https://neptune.ai/blog/data-centric-vs-model-centric-machine-learning) by neptune.ai for more details on model-centric vs. data-centric ML.

One of the most critical parts of data-centric ML is to monitor data quality.
With ZenML's data validators, we
can check many potential data issues, such as train-test skew, training-serving skew, data
drift, and more. Being aware of these issues, and having respective safety
mechanisms in place, is essential when serving ML models to real users.

To give one example, we can automatically check for **Data Skew** within our ML pipelines. Since the performance of ML models on unseen data can be unpredictable, we should always try to design our training data to match the actual environment where our model will later be deployed. The difference between those data distributions is called **Training-Serving Skew**. Similarly, differences in distribution between our training and testing datasets are called **Train-Test Skew**.

In the following, we will use the open-source data monitoring tool
[Evidently](https://evidentlyai.com/) to measure distribution differences
between our datasets. See this [blog
post](https://blog.zenml.io/zenml-loves-evidently/) of ours that explains the
Evidently integration in more detail.

## Detect Train-Test Skew

We can use Evidently, one of our data validator stack components, to check for skew between our training and test datasets. To do so, we will define a new pipeline with an Evidently step, into which we will then pass our training and test datasets.

At its core, Evidently’s distribution difference calculation functions take in a
reference dataset and compare it with a separate comparison dataset. These are
both passed in as [pandas
DataFrames](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html),
though CSV inputs are also possible. ZenML implements this functionality in the
form of several standardized steps along with an easy way to use the
visualization tools also provided along with Evidently as ‘Dashboards’.

For data distribution comparison, we can simply use the predefined step of
ZenML's Evidently integration:

```python
from zenml.integrations.evidently.steps import EvidentlyProfileConfig

# configure the Evidently step
evidently_profile_config = EvidentlyProfileConfig(
    profile_sections=["datadrift"]
)
```

We already have a standard datadrift skew or data drift step defined in ZenML,
so to use this in your pipelines, simply pass the step in as required. You can
see an example of this in the following pipeline initialization:

```python
from zenml.integrations.evidently.steps import evidently_profile_step

evidently_pipeline = digits_pipeline_with_train_test_checks(
    importer=importer(),
    trainer=svc_trainer(),
    evaluator=evaluator(),
    get_reference_data=get_reference_data(),
    skew_detector=evidently_profile_step( # here we use the pre-defined step
        step_name="evidently_skew_detector",
        config=evidently_profile_config,
    ),
)
```

Before we can run the pipeline, we still need to add Evidently into our ZenML
MLOps stack as a data validator:

```shell
zenml data-validator register evidently_validator --flavor=evidently
zenml stack update <OUR_STACK_NAME> -dv evidently_validator
```

Other ways of validating our data include the use of the following integrations:

- Deepchecks ([example](https://github.com/zenml-io/zenml/tree/main/examples/deepchecks_data_validation))
- Great Expectations ([example](https://github.com/zenml-io/zenml/tree/main/examples/great_expectations_data_validation))
- Whylogs ([example](https://github.com/zenml-io/zenml/tree/main/examples/whylogs_data_profiling))

See the respective examples to get to know how they each work and what they can
be used for.

{% hint style="info" %}
To read a more detailed guide about how Data Validators function in ZenML,
[click here](../../component-gallery/data-validators).
{% endhint %}

