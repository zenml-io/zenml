# Pipeline Directory

All pipelines you create in code will generate a [declarative pipeline configuration](../pipelines/what-is-a-pipeline.md). This configuration is representative of the pipeline itself, and thanks to [version-pinning](integration-with-git.md) and a declarative style, these configurations can be executed reproducibly across environments.

Similar to the [Artifact Store](artifact-store.md), you have the following options to configure the Artifact Store:

* Local \(Default\)
* Remote \(Google Cloud Storage\)
  * **Soon**: S3 compatible backends

```text
The pipeline YAML files produced by ZenML are not supposed to be edited in anyway.
```

By default, the default Pipelines Directory will be a local directory at the root of your repository called `pipelines`. The default Pipelines Directory will always be [referenced in your local `.zenml_config`](what-is-a-repository.md) , located in the `.zenml` folder within your experiment directory.

The Pipeline Directory is a critical configurable component of your ZenML repository. It is a single source of truth of all pipelines that have ever run, and therefore is the basis of all reproducibility. Therefore, make sure to treat it with caution and persist it in your version control system to be extra safe.

## Local \(Default\)

A `zenml init` creates a directory called `pipelines` in the root of the repository, which is used as the default pipelines directory. This directory may be persisted in git to ensure reproducibility.

## Remote \(GCS/S3\)

A remote Pipelines Dir can be used if a local one is not preferred. This is especially useful in cases of many pipelines being executed within the same repository, so as not to have one big directory of YAML files persisted in git.

Configuring a remote Pipelines Dir for ZenML is a one-liner using the CLI:

```text
zenml config pipelines set gs://your-bucket/sub/dir
```

