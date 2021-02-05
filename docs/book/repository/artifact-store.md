---
description: Store artifacts of pipelines in artifact stores
---

# Artifact Store

Closely related to the [Metadata Store](metadata-store.md) is the Artifact Store. It will store all intermediary pipeline step results, a binary representation of your source data as well as the trained model.

You have the following options to configure the Artifact Store:

* Local \(Default\)
* Remote \(Google Cloud Storage\)
  * **Soon**: S3 compatible backends

## Local \(Default\)

By default, ZenML will use the `.zenml` directory created when you run `zenml init` at the very beginning. All artifacts and inputs will be persisted there.

Using the default Artifact Store can be a limitation to the integrations you might want to use. Please check the documentation of the individual integrations to make sure they are compatible.

## Remote \(GCS/S3\)

Many experiments and many ZenML integrations require a remote Artifact Store to reliable retrieve and persist pipeline step artifacts. Especially dynamic scenarios with heterogenous environments will be only possible when using a remote Artifact Store.

Configuring a remote Artifact Store for ZenML is a one-liner using the CLI:

```text
zenml config artifacts set "gs://your-bucket/sub/dir"
```

