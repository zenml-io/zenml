---
description: Stacks define where and how your pipelines run
---

# Stacks

A stack is made up of the following three core components:

* An Artifact Store
* A Metadata Store
* An Orchestrator \(backend\)

A ZenML stack also happens to be a Pydantic `BaseSettings` class, which means that there are multiple ways to use it.

```bash
zenml stack register MY_NEW_STACK
    --metadata_store my-new-metadata-store \
    --artifact_store my-new-artifact-store \ 
    --orchestrator my-new-orchestrator

```

{% hint style="info" %}
See [CLI reference](../support/cli-command-reference.md) for more help.
{% endhint %}

## Metadata Stores

ZenML puts a lot of emphasis on guaranteed tracking of inputs across pipeline steps. The strict, fully automated, and deeply built-in tracking enables some of our most powerful features - e.g. comparability across pipelines. To achieve this, we're using a concept we call the Metadata Store.

You have the following options to configure your Metadata Store:

* SQLite \(Default\)
* MySQL

### SQLite \(Default\)

By default, your pipelines will be tracked in a local SQLite database within your `.zenml` folder. There is not much configuration to it - it just works out of the box.

### MySQL

Using MySQL as a Metadata Store is where ZenML can become really powerful, especially in highly dynamic environments \(read: running experiments locally, in the Cloud, and across team members\). Some of the ZenML integrations even require a dedicated MySQL-based Metadata Store to unfold their true potential.

The Metadata Store can be simply configured to use any MySQL server \(=&gt;5.6\):

```text
zenml config metadata set mysql \
    --host 127.0.0.1 \ 
    --port 3306 \
    --username USER \
    --passwd PASSWD \
    --database DATABASE
```

One particular configuration our team is very fond of internally leverages Google Cloud SQL and the docker-based cloudsql proxy to track experiments across team members and environments. Stay tuned for a tutorial on that!

```text
ZenML relies on Google's [MLMetadata](https://github.com/google/ml-metadata) to track input parameters across your pipelines. 
```

## Artifact Stores

Closely related to the [Metadata Store](https://github.com/zenml-io/zenml/blob/1b32b50007ef781b39c2525c3ca31ee03026c2b5/docs/book/repository/metadata-store.md) is the Artifact Store. It will store all intermediary pipeline step results, a binary representation of your source data as well as the trained model.

You have the following options to configure the Artifact Store:

* Local \(Default\)
* Remote \(Google Cloud Storage\)
  * **Soon**: S3 compatible backends

### Local \(Default\)

By default, ZenML will use the `.zenml` directory created when you run `zenml init` at the very beginning. All artifacts and inputs will be persisted there.

Using the default Artifact Store can be a limitation to the integrations you might want to use. Please check the documentation of the individual integrations to make sure they are compatible.

### Remote \(GCS/S3\)

Many experiments and many ZenML integrations require a remote Artifact Store to reliable retrieve and persist pipeline step artifacts. Especially dynamic scenarios with heterogenous environments will be only possible when using a remote Artifact Store.

Configuring a remote Artifact Store for ZenML is a one-liner using the CLI:

```text
zenml config artifacts set gs://your-bucket/sub/dir
```

## Orchestrator

