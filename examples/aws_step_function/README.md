# Orchestrating pipelines on AWS Step Functions

This is a WIP!

This example is a showcase of the AWS Step Function integration being developed in collaboration with @minoii minoii. It orchestrateds ZenML pipelines 
on AWS Step Functions.

[XGBoost](https://xgboost.readthedocs.io/en/latest/) is an optimized distributed gradient boosting library designed to be highly efficient, flexible and portable. It implements machine learning algorithms under the Gradient Boosting framework. XGBoost provides a parallel tree boosting (also known as GBDT, GBM) that solve many data science problems in a fast and accurate way. 

This example showcases how to train a `XGBoost Booster` model in a ZenML pipeline using AWS Step Functions. The ZenML `XGBoost` integration includes a custom materializer that persists the trained `xgboost.Booster` model to and from the artifact store. It also includes materializers for the custom `XGBoost.DMatrix` data object.

The data used in this example is the quickstart XGBoost data and is available in the [demo directory of the XGBoost repository](https://github.com/dmlc/xgboost/tree/master/demo/data).

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install xgboost aws_step_function -f

# pull example
zenml example pull aws_step_function
cd zenml_examples/aws_step_function

# initialize
zenml init
```

### Create the orchestrator

```shell
zenml orchestrator register aws_step_orchestrator -t aws_step_function
zenml metadata-store register mysql_metadata_store --type=mysql 
zenml artifact-store register s3_store --type=s3 --path=<S3_BUCKET_NAME>
zenml container-registry register ecr_registry --type=default --uri=<ECR_REGISTRY_NAME>
zenml stack register step_function_stack -m mysql_metadata_store -a s3_store -o aws_step_orchestrator -c ecr_registry
zenml stack set step_function_stack
```

### Run the project
Now we're ready. Execute:

```shell
python run.py
```

### Clean up
In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

## SuperQuick `aws_step_function` run

If you're really in a hurry and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run aws_step_function
```
