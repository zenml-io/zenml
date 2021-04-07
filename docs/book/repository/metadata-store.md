# Metadata Store

ZenML puts a lot of emphasis on guaranteed tracking of inputs across pipeline steps. The strict, fully automated, and deeply built-in tracking enables some of our most powerful features - e.g. comparability across pipelines. To achieve this, we're using a concept we call the Metadata Store.

You have the following options to configure your Metadata Store:

* SQLite \(Default\)
* MySQL

## SQLite \(Default\)

By default, your pipelines will be tracked in a local SQLite database within your `.zenml` folder. There is not much configuration to it - it just works out of the box.

## MySQL

Using MySQL as a Metadata Store is where ZenML can become really powerful, especially in highly dynamic environments \(read: running experiments locally, in the Cloud, and across team members\). Some of the ZenML integrations even require a dedicated MySQL-based Metadata Store to unfold their true potential.

The Metadata Store can be simply configured to use any MySQL server \(=&gt;5.6\):

```text
zenml config metadata set mysql \
    --host="127.0.0.1" \ 
    --port="3306" \
    --username="USER" \
    --password="PASSWD" \
    --database="DATABASE"
```

One particular configuration our team is very fond of internally leverages Google Cloud SQL and the docker-based cloudsql proxy to track experiments across team members and environments. Stay tuned for a tutorial on that!

```text
ZenML relies on Google's [MLMetadata](https://github.com/google/ml-metadata) to track input parameters across your pipelines.
```

