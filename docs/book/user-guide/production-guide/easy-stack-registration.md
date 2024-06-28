---
description: One-click stack deployments + easy stack registration wizard
---

# Connecting remote storage



## Running a pipeline on a cloud stack

Now that we have our remote artifact store registered, we can [register a new stack](understand-stacks.md#registering-a-stack) with it, just like we did in the previous chapter:

{% tabs %}
{% tab title="CLI" %}
```shell
zenml stack register local_with_remote_storage -o default -a cloud_artifact_store
```
{% endtab %}

{% tab title="Dashboard" %}
<figure><img src="../../.gitbook/assets/CreateStack.png" alt=""><figcaption><p>Register a new stack.</p></figcaption></figure>
{% endtab %}
{% endtabs %}

Now, using the [code from the previous chapter](understand-stacks.md#run-a-pipeline-on-the-new-local-stack), we run a training pipeline:

Set our `local_with_remote_storage` stack active:

```shell
zenml stack set local_with_remote_storage
```

Let us continue with the example from the previous page and run the training pipeline:

```shell
python run.py --training-pipeline
```

When you run that pipeline, ZenML will automatically store the artifacts in the specified remote storage, ensuring that they are preserved and accessible for future runs and by your team members. You can ask your colleagues to connect to the same [ZenML server](deploying-zenml.md), and you will notice that if they run the same pipeline, the pipeline would be partially cached, **even if they have not run the pipeline themselves before**.

You can list your artifact versions as follows:

{% tabs %}
{% tab title="CLI" %}
```shell
# This will give you the artifacts from the last 15 minutes
zenml artifact version list --created="gte:$(date -d '15 minutes ago' '+%Y-%m-%d %H:%M:%S')"
```
{% endtab %}

{% tab title="Cloud Dashboard" %}
[ZenML Pro](https://zenml.io/pro) features an [Artifact Control Plane](../starter-guide/manage-artifacts.md) to visualize artifact versions:

<figure><img src="../../.gitbook/assets/dcp_artifacts_versions_list.png" alt=""><figcaption><p>See artifact versions in the cloud.</p></figcaption></figure>
{% endtab %}
{% endtabs %}

You will notice above that some artifacts are stored locally, while others are stored in a remote storage location.

By connecting remote storage, you're taking a significant step towards building a collaborative and scalable MLOps workflow. Your artifacts are no longer tied to a single machine but are now part of a cloud-based ecosystem, ready to be shared and built upon.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
