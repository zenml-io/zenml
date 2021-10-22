# Low Level API Guide

The Low Level ZenML API is defined by the primitive `@step` and `@pipeline` decorators. These should be used when the [High Level API](../high-level-api) is too inflexible for the use-case at hand, and one requires more control over individual steps and connecting them in pipelines.

A user may also mix-and-match the Low Level API with the High Level API: All standard data types and steps that are applicable in the High Level API can be used with the Low Level API as well!

In order to illustrate how the Low Level API functions, we'll do a simple exercise to create a training pipeline from scratch (without any High Level components) and take it all the way to deployment.

Here is what we'll do in this guide:

* Create a MNIST pipeline that trains using [TensorFlow (Keras)](https://www.tensorflow.org/) (similar to the [Quickstart](../../quickstart-guide.md)).
* Swap out implementations of the `trainer` and `evaluator` steps with [scikit-learn](https://scikit-learn.org/).
* Persist our interim data artifacts in SQL tables rather than on files.
* Deploy the pipeline on [Airflow](https://airflow.apache.org/).


## Run it locally

### Pre-requisites
In order to run the chapters of the guide, you need to install and initialize ZenML:

```bash
# install CLI
pip install zenml tensorflow sklearn sqlalchemy 'google-cloud-bigquery[bqstorage,pandas]'

# initialize CLI
cd ~
mkdir zenml_examples
git clone https://github.com/zenml-io/zenml.git
cp -r zenml/examples/low_level_guide zenml_examples
cd zenml_examples/low_level_guide
git init
zenml init
```

At some point, you'll also need to (optionally) install and set up [Apache Airflow](https://airflow.apache.org/), but we address that again later in the guide itself.

### Run the project
Now we're ready. Execute:

```bash
python chapter_*.py  # for the chapter of your choice (except the Airflow chapter)
```

Note before executing each chapter, make sure to clean the old chapter artifact and metadata store:

```bash
rm -rf ~/zenml_examples/low_level_guide/.zen
zenml init  # start again
```

### Clean up
In order to clean up, in the root of your repo, delete the remaining `zenml` references.

```python
rm -rf ~/zenml_examples
rm -rf ~/zenml
```