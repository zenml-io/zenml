# Data versioning and lineage

In this lesson we will learn about one of the coolest features of ML pipelines: automated artifact versioning and tracking. This will give us tremendous insights into how exactly each of our models was created. Furthermore, it enables artifact caching, allowing us to switch out parts of our ML pipelines without having to rerun any previous steps.

First, if you have not done so already, run the following cell to install ZenML and it's sklearn integration.

## Artifact storage

You might now wonder how our ML pipelines can keep track of which artifacts changed and which did not. This requires several additional MLOps components that you would typically have to set up and configure yourself. Luckily, ZenML automatically set this up for us.

Under the hood, all the artifacts in our ML pipeline are automatically stored in an Artifact Store. By default, this is simply a place in your local file system, but we could also configure ZenML to store this data in a cloud bucket like Amazon S3 or any other place instead. We will see this in more detail when we migrate our MLOps stack to the cloud in a later chapter.

## Orchestrators

In addition to the artifact store, ZenML automatically set an Orchestrator for you, which is the component that defines how and where each pipeline step is executed when calling pipeline.run().

This component is not of much interest to us right now, but we will learn more about it in later chapters, when we will run our pipelines on a Kubernetes cluster using the Kubeflow orchestrator.

## ZenML MLOps Stacks

Artifact stores, together with orchestrators, build the backbone of a ZenML Stack, which defines all of the infrastructure and tools that your ML workflows are running on.

If you have the ZenML dashboard running, you can see a list of all your MLOps stacks under the "Stacks" section. Currently, you will only see the "default" stack there, which consists of a local artifact store and local orchestrator.

Under the "Stack Components" tab you can browse all stack components that you have currently registered with ZenML. You can combine those in any way you like into new stacks. Currently, you should only see a single "default" component for both "Orchestrator" and "Artifact Store", but we are going to register more stack components in subsequent lessons.