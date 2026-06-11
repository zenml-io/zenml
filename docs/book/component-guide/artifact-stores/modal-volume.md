---
description: Storing artifacts in a Modal Volume.
---

# Modal Volume Artifact Store

The Modal Volume artifact store stores ZenML artifacts in a [Modal Volume](https://modal.com/docs/guide/volumes). Its path uses this URI format:

```text
modal-volume://<volume-name>/<prefix>
```

For example, `modal-volume://zenml-artifacts/project-a` tells ZenML to use the Modal Volume named `zenml-artifacts` and to store this artifact store's files under the `project-a` prefix inside that Volume.

This artifact store is meant for Modal-native execution, especially stacks that use the [Modal orchestrator](../orchestrators/modal.md). In that setup, Modal mounts the Volume into the runtime that executes your pipeline, and ZenML reads and writes artifacts through that mounted filesystem path.

ZenML currently uses Modal's stable/default Volume behavior for this artifact store. Modal Volume v2 is not exposed as a ZenML configuration option in this release.

{% hint style="warning" %}
The Modal Volume artifact store is not a general-purpose S3-compatible cloud artifact store. Use it when your pipeline runs in Modal and should keep artifacts in Modal storage. If you need object storage that other cloud services can access through S3 APIs, use an S3-compatible artifact store instead.
{% endhint %}

## Requirements

To use the Modal Volume artifact store, you need:

* The ZenML `modal` integration installed:

  ```shell
  zenml integration install modal
  ```
* A Modal account with access to the Volume you want to use.
* Modal authentication available either through `modal setup`, Modal environment variables, or the artifact store's `token_id` and `token_secret` fields.

A ZenML service connector is not required for the Modal MVP. The artifact store talks to Modal through the Modal SDK and the credentials listed above.

## How to use it

Register the artifact store with the public `modal_volume` flavor:

```shell
zenml artifact-store register modal_artifacts \
  --flavor=modal_volume \
  --path=modal-volume://zenml-artifacts/project-a
```

Then use it in a stack with Modal execution components:

```shell
zenml stack register modal_stack \
  -a modal_artifacts \
  -o <MODAL_ORCHESTRATOR> \
  -c <REMOTE_CONTAINER_REGISTRY> \
  -i <IMAGE_BUILDER> \
  --set
```

If the Modal Volume does not already exist and you want ZenML to create it through the Modal SDK, set `create_if_missing=True`:

```shell
zenml artifact-store register modal_artifacts \
  --flavor=modal_volume \
  --path=modal-volume://zenml-artifacts/project-a \
  --create_if_missing=True
```

## Configuration options

### `path`

The `path` configures both the Modal Volume name and the prefix inside that Volume:

```text
modal-volume://<volume-name>/<prefix>
```

The Volume name is required. The prefix is optional but recommended if you want to keep ZenML artifacts separate from other files in the same Modal Volume.

### `mount_path`

`mount_path` is the absolute path where the Modal Volume is mounted inside Modal execution environments. The default is:

```text
/zenml-artifacts
```

Most users can keep the default. Change it only if your Modal runtime needs the Volume mounted at a different absolute path.

### `create_if_missing`

`create_if_missing` controls whether Modal may create the Volume if it does not already exist. It defaults to `False`.

Use `False` when you expect the Volume to be created and managed outside ZenML. Use `True` for a quick setup where ZenML is allowed to create the Modal Volume during Modal sandbox setup or SDK fallback access.

### Modal credentials

The artifact store has optional `token_id`, `token_secret`, and `modal_environment` fields:

```shell
zenml artifact-store register modal_artifacts \
  --flavor=modal_volume \
  --path=modal-volume://zenml-artifacts/project-a \
  --token_id=<MODAL_TOKEN_ID> \
  --token_secret=<MODAL_TOKEN_SECRET> \
  --modal_environment=<MODAL_ENVIRONMENT>
```

If you configure Modal tokens on the artifact store, `token_id` and `token_secret` must be configured together. If you omit them, ZenML lets the Modal SDK use its normal authentication behavior, such as credentials from `modal setup` or Modal environment variables.

`modal_environment` selects the Modal environment used for SDK access outside a mounted Modal runtime. If you omit it, Modal uses its default environment or the ambient `MODAL_ENVIRONMENT` value.

## When not to use it

Do not use the Modal Volume artifact store when your stack needs a normal cloud object store that is available outside Modal. For example, a Kubernetes orchestrator, a cloud model deployer, or external data tooling will usually expect S3, GCS, Azure Blob Storage, or another general storage backend.

A simple rule of thumb: if the artifact consumer runs in Modal, `modal_volume` can be a good fit. If the artifact consumer runs outside Modal and expects object-storage APIs, choose a cloud artifact store instead.
