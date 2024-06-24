---
description: How to migrate from ZenML 0.58.2 to 0.60.0 (Pydantic 2 edition).
---

# Release Notes

ZenML now uses Pydantic v2. 🥳

This upgrade comes with a set of critical updates. While your user experience
mostly remains unaffected, you might see unexpected behavior due to the
changes in our dependencies. Moreover, since Pydantic v2 provides a slightly
stricter validation process, you might end up bumping into some validation
errors which was not caught before, but it is all for the better 🙂 If
you run into any other errors, please let us know either on
[GitHub](https://github.com/zenml-io/zenml) or on
our [Slack](https://zenml.io/slack-invite).

## Changes in some of the critical dependencies

- SQLModel is one of the core dependencies of ZenML and prior to this upgrade,
  we were utilizing version `0.0.8`. However, this version is relatively
  outdated and incompatible with Pydantic v2. Within the scope of this upgrade,
  we upgraded it to `0.0.18`.
- Due to the change in the SQLModel version, we also had to upgrade our
  SQLAlchemy dependency from V1 to v2. While this does not affect the way
  that you are using ZenML, if you are using SQLAlchemy in your environment,
  you might have to migrate your code as well. For a detailed list of changes,
  feel free to
  check [their migration guide](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html).

## Changes in `pydantic`

Pydantic v2 brings a lot of new and exciting changes to the table. The core
logic now uses Rust and it is much faster and more efficient in terms of
performance. On top of it, the main concepts like model design, configuration,
validation, or serialization now include a lot of new cool features. If you are
using `pydantic` in your workflow and are interested in the new changes, you can
check [the brilliant migration guide](https://docs.pydantic.dev/2.7/migration/)
provided by the `pydantic` team to see the full list of changes.

## Changes in our integrations changes

Much like ZenML, `pydantic` is an important dependency in many other Python
packages. That’s why conducting this upgrade helped us unlock a new version for
several ZenML integration dependencies. Additionally, in some instances, we had
to adapt the functionality of the integration to keep it compatible
with `pydantic`. So, if you are using any of these integrations, please go
through the changes.

### Airflow

As mentioned above upgrading our `pydantic` dependency meant we had to upgrade
our `sqlmodel` dependency. Upgrading our `sqlmodel` dependency meant we had to
upgrade our `sqlalchemy` dependency as well. Unfortunately, `apache-airflow`
is still using `sqlalchemy` v1 and is incompatible with pydantic v2. As a
solution, we have removed the dependencies of the `airflow` integration. Now,
you can use ZenML to create your Airflow pipelines and use a separate
environment to run them with Airflow. You can check the updated docs
[right here](https://docs.zenml.io/stack-components/orchestrators/airflow).

### AWS

Some of our integrations now require `protobuf` 4. Since our
previous `sagemaker` version (`2.117.0`) did not support `protobof` 4, we could
not pair it with these new integrations. Thankfully `sagemaker` started
supporting `protobuf` 4 with version `2.172.0` and relaxing its dependency
solved the compatibility issue.

### Evidently

The old version of our `evidently` integration was not compatible with Pydantic
v2. They started supporting it starting from version `0.4.16`. As their latest
version is `0.4.22`, the new dependency of the integration is limited between
these two versions.

### Feast

Our previous implementation of the `feast` integration was not compatible with
Pydantic v2 due to the extra `redis` dependency we were using. This extra
dependency is now removed and the `feast` integration is working as intended.

### GCP

The previous version of the Kubeflow dependency (`kfp==1.8.22`) in our GCP
integration required Pydantic V1 to be installed. While we were upgrading our
Pydantic dependency, we saw this as an opportunity and wanted to use this chance
to upgrade the `kfp` dependency to v2 (which has no dependencies on the Pydantic
library). This is why you may see some functional changes in the vertex step
operator and orchestrator. If you would like to go through the changes in
the `kfp` library, you can
find [the migration guide here](https://www.kubeflow.org/docs/components/pipelines/v2/migration/).

### Great Expectations

Great Expectations started supporting Pydantic v2 starting from
version `0.17.15` and they are closing in on their `1.0` release. Since this
release might include a lot of big changes, we adjusted the dependency in our
integration to `great-expectations>=0.17.15,<1.0`. We will try to keep it
updated in the future once they release the `1.0` version

### Kubeflow

Similar to the GCP integration, the previous version of the kubeflow
dependency (`kfp==1.8.22`) in our `kubeflow` integration required Pydantic V1 to
be installed. While we were upgrading our Pydantic dependency, we saw this as an
opportunity and wanted to use this chance to upgrade the `kfp` dependency to
v2 (which has no dependencies on the Pydantic library). If you would like to go
through the changes in the `kfp` library, you can
find [the migration guide here](https://www.kubeflow.org/docs/components/pipelines/v2/migration/). (
We also are considering adding an alternative version of this integration so our
users can keep using `kfp` V1 in their environment. Stay tuned for any updates.)

### MLflow

`mlflow` is compatible with both Pydantic V1 and v2. However, due to a known
issue, if you install `zenml` first and then
do `zenml integration install mlflow -y`, it downgrades `pydantic` to V1. This
is why we manually added the same duplicated `pydantic` requirement in the
integration definition as well. Keep in mind that the `mlflow` library is still
using some features of `pydantic` V1 which are deprecated. So, if the
integration is installed in your environment, you might run into some
deprecation warnings.

### Label Studio

While we were working on updating our `pydantic` dependency,
the `label-studio-sdk` has released its 1.0 version. In this new
version, `pydantic` v2 is also supported. The implementation and documentation
of our Label Studio integration have been updated accordingly.

### Skypilot

With the switch to `pydantic` v2, the implementation of our `skypilot`
integration mostly remained untouched. However, due to an incompatibility
between the new version `pydantic` and the `azurecli`, the `skypilot[azure]`
flavor can not be installed at the same time, thus our `skypilot_azure`
integration is currently deactivated. We are working on fixing this issue and if
you are using this integration in your workflows, we recommend staying on the
previous version of ZenML until we can solve this issue.

### Tensorflow

The new version of `pydantic` creates a drift between `tensorflow`
and  `typing_extensions`  packages and relaxing the dependencies here resolves
the issue. At the same time, the upgrade to `kfp` v2 (in integrations
like `kubeflow`, `tekton`, or `gcp`) bumps our `protobuf` dependency from `3.X`
to `4.X`. To stay compatible with this requirement, the installed version
of `tensorflow` needs to be `>=2.12.0`. While this change solves the dependency
issues in most settings, we have bumped into some errors while
using `tensorflow` 2.12.0 on Python 3.8 on Ubuntu. If you would like to use this
integration, please consider using a higher Python version.

### Tekton

Similar to the `gcp` and `kubeflow` integrations, the old version of
our `tekton` integration was not compatible with `pydantic` V1 due to its `kfp`
dependency. With the switch from `kfp` V1 to v2, we have adapted our
implementation to use the new version of `kfp` library and updated our
documentation accordingly.

{% hint style="warning" %}
Due to all aforementioned changes, when you upgrade ZenML to 0.60.0, you might 
run into some dependency issues, especially if you were previously using an 
integration which was not supporting Pydantic v2 before. In such cases, we 
highly recommend setting up a fresh Python environment.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
