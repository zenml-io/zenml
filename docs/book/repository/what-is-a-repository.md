---
description: A ZenML repository has lots to offer
---

# What is a ZenML Repository?

Every ZenML project starts inside a ZenML repository. Think of it just like a normal Git repository, except that there are some added bonuses on top! To create a ZenML repository, do the following after [having installed ZenML](../getting-started/installation.md).

```text
zenml init
```

{% hint style="warning" %}
Please make sure to be inside a valid git repository before executing the above!
{% endhint %}

This creates a default SQLite Metadata Store and local Artifact Store inside a `.zenml` folder in the root of your repository. It also creates a `pipelines` directory at the root as well, which is the path where all your [pipeline configurations](../pipelines/what-is-a-pipeline.md) will be stored. Finally, it adds a `.zenml_config` YAML inside the `.zenml` folder that tracks all this.

If you want to change your Metadata Store, Artifact Store, or Pipelines Directory, please use the `zenml config` CLI group.

```bash
# Display the current property
zenml config PROPERTY get

# Set the current property
zenml config PROPERTY set [OPTIONS] ARGUMENTS
```

## ZenML Local Config vs ZenML Global Config

Similar to other tools like Git, ZenML both maintains a per-repository configuration as well as a global configuration on your machine. As mentioned above, the local configuration is stored in a `.zenml/` directory at the root of your repository. This configuration is written in YAML and may look like this:

```yaml
artifact_store: /path/to/zenml/repo/.zenml/local_store
metadata:
  args:
    uri: /path/to/zenml/repo/.zenml/local_store/metadata.db
  type: sqlite
pipelines_dir: /path/to/zenml/repo/pipelines
```

As you can see this file stores the `default` [Artifact Store](artifact-store.md), [Metadata Store](metadata-store.md) and [Pipelines Directory](pipeline-directory.md) which each of your pipelines will use by default when they are run.

The global config on the other hand stores `global` information such as if a unique anonymous UUID for your zenml installation as well as metadata regarding usage of your ZenML package. It can be found in most systems in the `.config` directory at the path `zenml/info.json`.

