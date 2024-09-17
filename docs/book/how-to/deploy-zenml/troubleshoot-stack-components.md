---
description: Learn how to troubleshoot Stack Components deployed with ZenML.
---

# Troubleshoot stack components

There are two ways in which you can understand if something has gone wrong while deploying your stack or stack components.

## Error logs from the CLI

The CLI will show any errors that the deployment runs into. Most of these would be coming from the underlying terraform library and could range from issues like resources with the same name existing in your cloud to a wrong naming scheme for some resource.

Most of these are easy to fix and self-explanatory but feel free to ask any questions or doubts you may have to us on the ZenML Slack! 🙋‍

## Debugging errors with already deployed components

Sometimes, an application might fail after an initial successful deployment. This section will cover steps on how to debug failures in such a case, for Kubernetes apps, since they form a majority of all tools deployed with the CLI.

{% hint style="info" %}
Other components include cloud-specific apps like Vertex AI, Sagemaker, S3 buckets, and more. Information on what has gone wrong with them would be best found on the web console for the respective clouds.
{% endhint %}

### Getting access to the Kubernetes Cluster

The first step to figuring out the problem with a deployed Kubernetes app is to get access to the underlying cluster hosting it. When you deploy apps that require a cluster, ZenML creates a cluster for you and this is reused for all subsequent apps that need it.

{% hint style="info" %}
If you've used the `zenml stack deploy` flow to deploy your components, your local `kubectl` might already have access to the cluster. Check by running the following command:

```
kubectl get nodes
```
{% endhint %}

#### Stack Component Deploy

{% tabs %}
{% tab title="AWS" %}
1. Get the name of the deployed cluster.\
   `zenml stack recipe output eks-cluster-name`
2. Figure out the region that the cluster is deployed to. By default, the region is set to `eu-west-1` , which you should use in the next step if you haven't supplied a custom value while creating the cluster.
3. Run the following command.\
   `aws eks update-kubeconfig --name <NAME> --region <REGION>`
{% endtab %}

{% tab title="GCP" %}
1. Get the name of the deployed cluster.\
   \
   `zenml stack recipe output gke-cluster-name`\\
2. Figure out the region that the cluster is deployed to. By default, the region is set to `europe-west1`, which you should use in the next step if you haven't supplied a custom value while creating the cluster.\\
3. Figure out the project that the cluster is deployed to. You must have passed in a project ID while creating a GCP resource for the first time.\\
4. Run the following command.\
   `gcloud container clusters get-credentials <NAME> --region <REGION> --project <PROJECT_ID>`
{% endtab %}

{% tab title="K3D" %}
{% hint style="info" %}
You may already have your `kubectl` client configured with your cluster. Check by running `kubectl get nodes` before proceeding.
{% endhint %}

1. Get the name of the deployed cluster.\
   \
   `zenml stack recipe output k3d-cluster-name`\\
2. Set the `KUBECONFIG` env variable to the `kubeconfig` file from the cluster.\
   \
   `export KUBECONFIG=$(k3d kubeconfig get <NAME>)`\\
3. You can now use the `kubectl` client to talk to the cluster.
{% endtab %}
{% endtabs %}

#### Stack Recipe Deploy

The steps for the stack recipe case should be the same as the ones listed above. The only difference that you need to take into account is the name of the outputs that contain your cluster name and the default regions.

Each recipe might have its own values and here's how you can ascertain those values.

* For the cluster name, go into the `outputs.tf` file in the root directory and search for the output that exposes the cluster name.
* For the region, check out the `variables.tf` or the `locals.tf` file for the default value assigned to it.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
