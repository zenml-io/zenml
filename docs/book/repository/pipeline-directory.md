---
description: A single place to store all your pipelines
---

# Pipeline Directory

All pipelines you create in code will generate a [declarative pipeline configuration](../pipelines/what-is-a-pipeline.md). This configuration is representative of the pipeline itself, and thanks to [version-pinning](integration-with-git.md#versioning-custom-code) and a declarative style, these configurations can be executed reproducibly across environments.

The generated configurations will be persisted in a local directory at the root of your repository called `pipelines` by default. These configurations will be[ referenced in your local `.zenml_config`](repository-singleton.md#zenml-local-config-vs-zenml-global-config) , located in the `.zenml` folder within your experiment directory.

The Pipeline Directory is a critical configurable component of your ZenML repository. It is a single source of truth of all pipelines that have ever run, and therefore is the basis of all reproducibility. Therefore, make sure to treat it with caution and persist it in your version control system to be extra safe.

