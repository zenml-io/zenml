---
description: Store artifacts in an AWS S3 or compatible bucket
---

The S3 Artifact Store is an [Artifact Store](./overview.md) flavor provided with
the `s3` ZenML integration that uses [the AWS S3 managed object storage service](https://aws.amazon.com/s3/)
or one of the self-hosted S3 alternatives, such as [MinIO](https://min.io/) or
[Ceph RGW](https://ceph.io/en/discover/technology/#object).
to store artifacts in an S3 compatible object storage backend.

## When would you want to use it?

Running ZenML pipelines with [the local Artifact Store](./local.md) is usually
sufficient if you just want to evaluate ZenML or get started quickly without
incurring the trouble and the cost of employing cloud storage services in your
stack. However, the local Artifact Store becomes insufficient or unsuitable if
you have more elaborate needs for your project:

* if you want to share your pipeline run results with other team members or
stakeholders inside or outside your organization
* if you have other components in your stack that are running remotely (e.g. a
Kubeflow or Kubernetes Orchestrator running in public cloud).
* if you outgrow what your local machine can offer in terms of storage space and
need to use some form of private or public storage service that is shared with
others
* if you are running pipelines at scale and need an Artifact Store that can
handle the demands of production grade MLOps

In all these cases, you need an Artifact Store that is backed by a form of
public cloud or self-hosted shared object storage service.

You should use the S3 Artifact Store when you decide to keep your ZenML
artifacts in a shared object storage and if you have access to the AWS S3
managed service or one of the S3 compatible alternatives (e.g. Minio, Ceph RGW).
You should consider one of the other [Artifact Store flavors](./overview.md#artifact-store-flavors)
if you don't have access to an S3 compatible service.

## How do you deploy it?

The S3 Artifact Store flavor is provided by the S3 ZenML integration.

...

For more, up-to-date information on the Artifact Store implementation, you can
have a look at [the API docs](https://apidocs.zenml.io/0.10.0/api_docs/integrations/#zenml.integrations.s3.artifact_stores.s3_artifact_store).

## How do you use it?

Aside from the fact that the artifacts are stored in an S3 compatible backend,
using the S3 Artifact Store is no different than [using any other flavor of Artifact Store](./overview.md#how-to-use-it).
