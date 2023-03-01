# 🏎 Explore Data Profiling and Validation with Evidently
Data profiling and validation is the process of examining and analyzing data to understand its characteristics, patterns, and quality. The goal of this process is to gain insight into the data, identify potential issues or errors, and ensure that the data is fit for its intended use.

Evidently is a Python package that provides tools for data profiling and validation. Evidently makes it easy to generate reports on your data, which can provide insights into its distribution, missing values, correlation, and other characteristics. These reports can be visualized and examined to better understand the data and identify any potential issues or errors.

Data validation involves testing the quality and consistency of the data. This can be done using a variety of techniques, such as checking for missing values, duplicate records, and outliers, as well as testing the consistency and accuracy of the data. Evidently provides a suite of tests that can be used to evaluate the quality of the data, and provides scores and metrics for each test, as well as an overall data quality score.

## 🗺 Overview
This example uses [`evidently`](https://github.com/evidentlyai/evidently), a
useful open-source library to painlessly check for missing values (among other
features). 

ZenML implements some standard steps that you can use to get reports or test your
data for quality and other purposes. These steps are:

* `EvidentlyReportStep` and `EvidentlySingleDatasetReportStep`: These steps generate
a report for one or two given datasets. Similar to how you configure an Evidently
Report, you can configure a list of metrics, metric presets or metrics generators
for the step as parameters. The full list of metrics can be found
[here](https://docs.evidentlyai.com/reference/all-metrics/).

* `EvidentlyTestStep` and `EvidentlySingleDatasetTestStep`: These step test one
or two given datasets using various Evidently tests. Similar to how you configure
an Evidently TestSuite, you can configure a list of tests, a test presets or
test generators for the step as parameters. The full list of tests can be found
[here](https://docs.evidentlyai.com/reference/all-tests/).

## 🧰 How the example is implemented
In this example, we compare two separate slices of the same dataset as an easy
way to get an idea for how `evidently` is making the comparison between the two
dataframes. We chose some text data to illustrate how this works.

```python
text_data_report = evidently_report_step(
    step_name="text_data_report",
    params=EvidentlyReportParameters(
        column_mapping=EvidentlyColumnMapping(
            target="Rating",
            numerical_features=["Age", "Positive_Feedback_Count"],
            categorical_features=[
                "Division_Name",
                "Department_Name",
                "Class_Name",
            ],
            text_features=["Review_Text", "Title"],
            prediction="class",
        ),
        metrics=[
            "DataQualityPreset",
            ["TextOverviewPreset", {"column_name": "Review_Text"}],
            {
                "metric": "ColumnRegExpMetric",
                "parameters": {"reg_exp": "^[0..9]"},
                "columns": ["Review_Text", "Title"],
            },
        ],
    ),
)
```

Here you can see that defining the step is extremely simple using our
builtin steps and included utility, and then you just have to pass in the two
dataframes for the comparison to take place.

We even allow you to use the Evidently visualization tool easily to display data
drift diagrams in your browser or within a Jupyter notebook:

![Evidently drift visualization 1](assets/drift-visualization-01.png)
![Evidently drift visualization 2](assets/drift-visualization-02.png)


# ☁️ Run in Colab
If you have a Google account, you can get started directly with Google colab 
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/evidently_data_validation/evidently.ipynb)

# 🖥 Run it locally

## 👣 Step-by-Step
### 📄 Prerequisites 
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install "zenml[server]"

# install ZenML integrations and example dependencies
zenml integration install evidently sklearn -y
pip install nltk

# pull example
zenml example pull evidently_data_validation
cd zenml_examples/evidently_data_validation

# Initialize ZenML repo
zenml init

# Start the ZenServer to enable dashboard access
zenml up
```

### 🥞 Set up your stack for Evidently

You need to have an Evidently Data Validator component to your stack to be able
to use Evidently data profiling in your ZenML pipelines. Creating such a stack 
is easily accomplished:

```shell
zenml data-validator register evidently -f evidently
zenml stack register evidently_stack -o default -a default -dv evidently --set
```

### ▶️ Run the Code
Now we're ready. Execute:

```bash
python run.py
```

Alternatively, if you want to run based on the config.yaml you can run with:

```bash
zenml pipeline run pipelines/text_report_test_pipeline/text_report_test.py -c config.yaml
```

### 🧽 Clean up
In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```
