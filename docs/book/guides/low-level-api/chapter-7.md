---
description: Deploy pipelines to production
---

If you want to see the code for this chapter of the guide, head over to the [GitHub](https://github.com/zenml-io/zenml/tree/main/examples/low_level_guide/chapter_7.py).

# Chapter 7: Deploy pipelines to production

When developing ML models, your pipelines will, at first, most probably live in your machine with a local [Stack](../../core-concepts.md). However, at a certain point when you are finished with its design, you might want to transition to a more production-ready setting, and deploy the pipeline to a more robust environment.

## Install and configure Airflow

This part is optional, and it would depend on your pre-existing production setting. For example, for this guide we chose to deploy and install Airflow from scratch and set it to work with a local `DAG_FOLDER`, however you might want to use a manage Airflow instance like [Cloud Composer](https://cloud.google.com/composer) or [Astronomer](https://astronomer.io/) and change the `DAG_FOLDER` accordingly.

To install Airflow, please follow the [awesome official guide](https://airflow.apache.org/docs/apache-airflow/stable/start/local.html). Its just a pip install really.

## Creating an Airflow Stack

A [Stack](../../core-concepts.md) is the configuration of the surrounding infrastructure where ZenML pipelines are run and managed. For now the stack consists of:

* A metadata store: To store metadata like parameters and artifact URIs
* An artifact store: To store interim data step output.
* An orchestrator: A service that actually kicks off and runs each step of the pipeline.

When you did `zenml init` at the start of this guide, a default `local_stack` was created with local version of all of these. In order to see the stack you can check it out in the command line:

```shell
zenml stack list
```

Output:
```bash
STACKS:
key          stack_type    metadata_store_name    artifact_store_name    orchestrator_name
-----------  ------------  ---------------------  ---------------------  -------------------
local_stack  base          local_metadata_store   local_artifact_store   local_orchestrator
```

Let's stick with the `local_metadata_store` and a `local_artifact_store` for now and create an Airflow orchestrator and stack.

```shell
zenml orchestrator register airflow_orchestrator airflow
zenml stack register airflow_stack \
    -m local_metadata_store \
    -a local_artifact_store \
    -o airflow_orchestrator
zenml stack set airflow_stack
```

Output:
```bash
Orchestrator `airflow_orchestrator` successfully registered!
Stack `airflow_stack` successfully registered!
Active stack: airflow_stack
```

{% hint style="warning" %}
In the real-world we would also switch to something like a MySQL-based metadata store and a Azure/GCP/S3-based artifact store. We have just skipped that part to keep everything in one machine to make it a bit easier to run this guide.
{% endhint %}

## Run
The code from this chapter is the same as the last chapter. So run:

```python
python chapter_7.py
```

Even through the pipeline script is  the same, the output will be a lot different from last time. ZenML will detect that `airflow_stack` is the active stack, and bootstrap airflow locally for you. It will create a bunch of files in the current working directory and even create an admin with the username `admin` and store the password in the `standalone_admin_password.txt` file.

Navigate over to `https://0.0.0.0:8080` and you can enter your just generated credentials. You would then be able to see a list of Airflow DAGs, including one called `mnist`, scheduled to run every 5 minutes. You can click it and now finally see a visualization of the pipeline we've been working so hard to create in these chapters. Go ahead and trigger the DAG from the UI to see it in action.

And that's it: As long as you keep Airflow running now, this script will run every 5 minutes, pull the latest data, and train a new model!

We now have a continuously training ML pipeline training on new data every day. All the pipelines will be tracked in your production [Stack's metadata store](../../core-concepts.md), the interim artifacts will be stored in the [Artifact Store](../../core-concepts.md), and the scheduling and orchestration is being handled by the [orchestrator](../../core-concepts.md), in this case Airflow.

# Conclusion

If you made it this far, congratulations! You're one step closer to being production-ready with your ML workflows! Here is what we achieved in this entire guide:

* Experimented locally and built-up a ML pipeline.
* Transitioned to production by deploying a continuously training pipeline on newly arriving data.
* All the while retained complete lineage and tracking over parameters, data, code, and metadata.

## Coming soon

There are lot's more things you do in production that you might consider adding to your workflows:

* Adding a step to automatically deploy the models to a REST endpoint.
* Setting up a drift detection and validation step to test models before deploying.
* Creating a batch inference pipeline to get predictions.

ZenML will help with all of these and above -> Watch out for future releases and the next extension of this guide coming soon!