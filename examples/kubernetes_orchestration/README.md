# :dango: Pipeline Orchestration on Kubernetes

Using the ZenML `kubernetes` integration, you can orchestrate and scale your
ML pipelines on Kubernetes without writing a single line of Kubernetes code.

This Kubernetes-native orchestrator is a minimalist, lightweight alternative 
to other distributed orchestrators like Airflow or Kubeflow.

Overall, the Kubernetes orchestrator is quite similar to the Kubeflow
orchestrator in that it runs each pipeline step in a separate
Kubernetes pod. However, the orchestration of the different pods is not done
by Kubeflow but by a separate master pod that orchestrates the step execution
via topological sort.

Compared to Kubeflow, this means that the Kubernetes-native orchestrator is
faster and much simpler to start with since you do not need to install 
and maintain Kubeflow on your cluster.
The Kubernetes-native orchestrator is an ideal choice for teams new to 
distributed orchestration that do not want to go with a fully-managed offering.

However, since Kubeflow is much more mature, you should, in most cases, aim to
move your pipelines to Kubeflow in the long run.
A smooth way to production-grade orchestration could be to set up a Kubernetes
cluster first and get started with the Kubernetes-native orchestrator.
If needed, you can then install and set up Kubeflow later and simply switch out
the orchestrator of your stack as soon as your full setup is ready.

In this example, we will build a simple, four-step pipeline and orchestrate it
in a Kubernetes cluster running in the cloud.

## :heavy_check_mark: Requirements

In this example, we will use an AWS cloud stack, consisting of an EKS cluster,
an ECR container registry, and a S3 bucket for artifact storage.

If you want to follow this example line by line, you need to spin up each of
the corresponding AWS services first.
Alternatively, you can can also use any other cloud provider and adjust all
`zenml ... register` commands below accordingly.

Regardless of your cloud provider choice, you will also need to have kubectl
and Docker installed locally.

### Setup and Register Kubernetes Orchestrator
After spinning up your Kubernetes cluster in the cloud, you will first need
to connect it to your local kubectl as a new Kubernetes context.

How to do this depends on your cloud provider. For AWS EKS, you can do the
following:

```bash
aws eks --region <AWS_REGION> update-kubeconfig
    --name <AWS_EKS_CLUSTER>
    --alias <KUBE_CONTEXT>
```

**Note:** It does not matter what you use as `KUBE_CONTEXT` here, as long as it
is a unique name.

Next, register your Kubernetes orchestrator with the respective Kubernetes 
context:

```bash
zenml orchestrator register k8s_orchestrator
    --flavor=kubernetes
    --kubernetes_context=<KUBE_CONTEXT>
    --synchronous=True
```

### Setup and Register Metadata Store

If you want to store your metadata locally within the Kubernetes cluster, you
can use the `KubernetesMetadataStore`, which automatically spins up a MySQL 
deployment in your cluster if you call `zenml stack up`.

We can register this metadata store as follows:

```bash
zenml metadata-store register k8s_store 
    --flavor=kubernetes
    --kubernetes_context==<KUBE_CONTEXT>
    --kubernetes_namespace=zenml
    --deployment_name=mysql 
    --storage_capacity=10Gi
```

### Register Container Registry
Next, we need to register a container registry where the Docker images for all
Kubernetes pods will be stored.

To do so, we first need to authorize our local Docker to access the registry.
This is again specific to your cloud provider. 
For Amazon ECR, you could do the following:

```bash
aws ecr get-login-password --region <AWS_REGION> | docker login 
    --username AWS 
    --password-stdin 
    <ECR_REGISTRY_NAME>
```

Now we can register the container registry like this:

```bash
zenml container-registry register ecr_registry 
    --flavor=default 
    --uri=<ECR_REGISTRY_NAME>
```

### Setup Artifact Store
Lastly, we also need to register a remote artifact store (e.g. Amazon S3):

```bash
zenml artifact-store register s3_store 
    --flavor=s3 
    --path=<REMOTE_ARTIFACT_STORE_PATH>
```

### Register and Spin Up Stack

Finally, let us bring everything together and register our stack:

```bash
zenml stack register k8s_stack 
    -m k8s_store 
    -a s3_store 
    -o k8s_orchestrator 
    -c ecr_registry
zenml stack set k8s_stack
```

Next, call `zenml stack up` to provision and start the metadata store.

## :computer: Run Pipeline Locally
Now that our stack is set up, all of our ML code will automatically be executed
on the Kubernetes cluster in the cloud. Let's run the example pipeline:

```bash
python run.py
```

If all went well, you should now see the logs of all Kubernetes pods in your
terminal, similar to what is shown below.

For the output below, note that the `skew_comparison` and `svc_trainer` steps
are run in parallel, so the order of messages might differ when you run it
yourself.

```
Using stack k8s_stack to run pipeline kubernetes_example_pipeline...
Waiting for Kubernetes orchestrator pod...
Kubernetes orchestrator pod started.
Waiting for pod of step importer to start...
Step importer has started.
Step importer has finished in 8.501s.
Pod of step importer completed.
Waiting for pod of step svc_trainer to start...
Waiting for pod of step skew_comparison to start...
Step skew_comparison has started.
Step svc_trainer has started.
Step svc_trainer has finished in 5.178s.
Pod of step svc_trainer completed.
Step skew_comparison has finished in 7.154s.
Waiting for pod of step evaluator to start...
Pod of step skew_comparison completed.
Step evaluator has started.
Test accuracy: 0.9688542825361512
Step evaluator has finished in 6.219s.
Pod of step evaluator completed.
Orchestration pod completed.
Pipeline run finished.
Pipeline run kubernetes_example_pipeline-07_Jun_22-14_26_14_450641 has finished in 1m57s.
```

### Interacting with pods via kubectl

For debugging, it can sometimes be handy to interact with the Kubernetes pods
directly via kubectl. 
To make this easier, we have added the following labels to all pods:
- `run`: the name of the ZenML run.
- `pipeline`: the name of the ZenML pipeline associated with this run.

E.g., you can use these labels to get a list of all pods related to the 
pipeline used in this example by running the following:

```
kubectl get pods -l pipeline=kubernetes_example_pipeline
```

## :sponge: Clean Up

### Delete Run Pods
```bash
kubectl delete pod -l pipeline=kubernetes_example_pipeline
```

### Deprovision Stack

**WARNING**: This will permanently delete your metadata store, so all metadata
will be lost. Never do this for production settings!

```bash
zenml stack down --force
```
