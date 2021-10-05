# Artifacts

Artifacts are the data that power your data-centric ML pipelines. It is actually steps that produce artifacts, which are then stored in the artifact store.

Artifacts can be of many different types like `TFRecord`s or saved model pickles, depending on what the step produces.

## Materializers

In the very basic sense, an Artifact consists of a simple path that points to data. How to read that data is defined by `Materializers`. A Materializer how the data of a particular data is read, and one artifact can have many materializers.

## **Relation to Artifact Store**

An artifact store is a place where artifacts are stored. These artifacts may have been produced by the pipeline steps, or they may be the data first ingested into a pipeline via an ingestion step.

