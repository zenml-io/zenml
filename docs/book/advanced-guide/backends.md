# Backends

## What is a backend?[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/what-is-a-backend.html#what-is-a-backend)

Production-ready backends when you want to scale

ZenML backends define `how` and `where` ZenML pipelines are run. They are broadly split into three categories:

* [orchestrator](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html): Orchestrator backends manage the running of each step of the pipeline
* [processing](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html): Processing backends defines the environment in which each step executes its workload
* [training](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html): Training backends are special and meant only for [Training Pipelines.](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/backends/pipelines/training-pipeline.md) They define the environment in which the training happens

By separating backends from the actual pipeline logic, ZenML achieves a [Terraform](https://www.terraform.io/)-like scalability, [extensibility](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/backends/benefits/integrations.md) and reproducibility for all its pipelines. This is achieved whilst also maintaining comparability and consistent evaluation for all pipelines.

Backends too are split into `standard` and `custom` categories. The standard ones can be found at: `zenml.core.backends.*` .

### How to use a backend?[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/what-is-a-backend.html#how-to-use-a-backend)

A backend is associated directly with a [pipeline](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/pipelines/what-is-a-pipeline.html) and can be specified in different ways using the `backends` argument:

* When constructing a pipeline.
* When executing a `pipeline.run()`.
* When executing a `pipeline.build()`.

### Create your own backend[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/what-is-a-backend.html#create-your-own-backend)

```text
Before creating your own backend, please make sure to follow the [general rules](../getting-started/creating-custom-logic.md)
for extending any first-class ZenML component.
```

![Copy to clipboard](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/_static/copy-button.svg)

The API to create custom backends is still under active development. Please see this space for updates.

If you would like to see this functionality earlier, please let us know via our [Slack Channel](https://zenml.io/slack-invite/) or [create an issue on GitHub](https://https//github.com/maiot-io/zenml).\)

### What next?[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/what-is-a-backend.html#what-next)

* Set up different [orchestration](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html) strategies for your pipelines. Execute pipelines on your local

  machine, to a large instance on the cloud, to a Kubernetes cluster.

* Leverage powerful distributed processing by using built-in [processing](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html) backends.
* Train on GPUs in the cloud with various [training](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html).

## Orchestrator Backends[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#orchestrator-backends)

The orchestrator backend is especially important, as it defines **where** the actual pipeline job runs. Think of it as the `root` of any pipeline job, that controls how and where each individual step within a pipeline is executed. Therefore, the combination of orchestrator and other backends can be used to great effect to scale jobs in production.

The _**orchestrator**_ environment can be the same environment as the _**processing**_ environment, but not neccessarily. E.g. by default a `pipeline.run()` call would result in a local orchestrator and processing backend configuration, meaning the orchestration would be local along with the actual steps. However, if lets say, a dataflow processing backend is chosen, then chosen steps would be executed not in the local enviornment, but on the cloud in Google Dataflow.

### Standard Orchestrators[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#standard-orchestrators)

Please refer to the docstrings within the source code for precise details.

#### Local orchestrator[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#local-orchestrator)

This is the default orchestrator for ZenML pipelines. It runs pipelines sequentially as a Python process in it’s local environment. You can use this orchestrator for quick experimentation and work on smaller datasets in your local environment.

#### GCP Orchestrator[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#gcp-orchestrator)

The GCPOrchestrator can be found at [`OrchestratorGCPBackend`](https://docs.zenml.io/reference/core/backends/orchestrator/gcp/index.html). It spins up a VM on your GCP projects, zips up your local code to the instance, and executes the ZenML pipeline with a Docker Image of your choice.

Best of all, the Orchestrator is capable of launching [preemtible VMs](https://cloud.google.com/compute/docs/instances/preemptible), saving a big chunk of cost along the way.

#### Kubernetes[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#kubernetes)

The KubernetesOrchestrator can be found at [`OrchestratorGCPBackend`](https://docs.zenml.io/reference/core/backends/orchestrator/kubernetes/index.html). It launches a Job on your Kubernetes cluster, zips up your local code to the Pod, and executes the ZenML pipeline with a Docker Image of your choice.

**NOTE:** This Orchestrator requires you to ensure a successful connection between your Kubernetes Cluster and your Metadata Store.

A more extensive guide on creating pipelines with Kubernetes can be found in the [Kubernetes Tutorial](https://github.com/maiot-io/zenml/tree/fc868ee5e5589ef0c09e30be9c2eab4897bfb140/tutorials/running-a-pipeline-on-kubernetes.md).

#### AWS Orchestrator[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#aws-orchestrator)

Stay tuned - we’re almost there.

#### Azure Orchestrator[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#azure-orchestrator)

Stay tuned - we’re almost there.

#### Kubeflow[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#kubeflow)

Coming soon!

### Creating a custom orchestrator[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#creating-a-custom-orchestrator)

The API to create custom orchestrators is still under active development. Please see this space for updates.

If you would like to see this functionality earlier, please let us know via our [Slack Channel](https://zenml.io/slack-invite/) or [create an issue on GitHub](https://https//github.com/maiot-io/zenml).



## Processing Backends[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html#processing-backends)

Some pipelines just need more - processing power, parallelism, permissions, you name it.

A common scenario on large datasets is distributed processing, e.g. via Apache Beam, Google Dataflow, Apache Spark, or other frameworks. In line with our integration-driven design philosophy, ZenML makes it easy to to distribute certain `Steps` in a pipeline \(e.g. in cases where large datasets are involved\). All `Steps` within a pipeline take as input a `ProcessingBackend`.

### Overview[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html#overview)

The pattern to add a backend to a step is always the same:

```text
backend = ...  # define the backend you want to use
pipeline.add_step(
    Step(...).with_backend(backend)
)
```

![Copy to clipboard](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/_static/copy-button.svg)

### Supported Processing Backends[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html#supported-processing-backends)

ZenML is built on Apache Beam. You can simple use the `ProcessingBaseBackend`, or extend ZenML with your own, custom backend.+

For convenience, ZenML supports a steadily growing number of processing backends out of the box:

#### Google Dataflow[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html#google-dataflow)

ZenML natively supports [Google Cloud Dataflow](https://cloud.google.com/dataflow) out of the box \(as it’s built on Apache Beam\).

**Prequisites:**

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* [Make sure you have permissions](https://cloud.google.com/dataflow/docs/concepts/access-control) to launch dataflow jobs, whether through service account or default credentials.

**Usage:**

```text
# Define the processing backend
processing_backend = ProcessingDataFlowBackend(
    project=GCP_PROJECT,
    staging_location=os.path.join(GCP_BUCKET, 'dataflow_processing/staging'),
)

# Reference the processing backend in steps
# Add a split
training_pipeline.add_split(
    RandomSplit(...).with_backend(
        processing_backend)
)

# Add a preprocessing unit
training_pipeline.add_preprocesser(
    StandardPreprocesser(...).with_backend(processing_backend)
)
```

## Training Backends[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html#training-backends)

ZenML has built-in support for dedicated training backends. These are backends specifically built to provide an edge for training models, e.g. through the availability of GPUs/TPUs, or other performance optimizations.

To use them, simply define your `TrainerStep` along with a `TrainingBackend` for different use-cases.

### Supported Training Backends[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html#supported-training-backends)

#### Google Cloud AI platform[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html#google-cloud-ai-platform)

Google offers a dedicated service for training models with access to GPUs and TPUs called [Google Cloud AI Platform](https://cloud.google.com/ai-platform/docs). ZenML has built-in support to run `TrainingSteps` on Google Cloud AI Platform.

**Prerequisites:**

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* Make sure you have permissions to launch a training Job on Google AI Platform.
* Make sure you enable the following APIs:
  * Google Cloud AI Platform
  * Cloud SQL
  * Cloud Storage

**Usage:**

```text
from zenml.backends.training import SingleGPUTrainingGCAIPBackend
from zenml.steps.trainer import TFFeedForwardTrainer

(...)

# Add a trainer with a GCAIP backend
training_backend = SingleGPUTrainingGCAIPBackend(
  project=GCP_PROJECT,
  job_dir=TRAINING_JOB_DIR
)

training_pipeline.add_trainer(
  TFFeedForwardTrainer(...).with_backend(training_backend))
```

![Copy to clipboard](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/_static/copy-button.svg)

#### AWS Sagemaker[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html#aws-sagemaker)

Support for AWS Sagemaker is coming soon. Stay tuned to our releases, or let us know on [Slack](https://zenml.io/slack-invite/) if you have an urgent use-case for AWS Sagemaker!

If you would like to see any of this functionality earlier, or if you’re missing a specific backend, please let us know via our [Slack Channel](https://zenml.io/slack-invite/) or [create an issue on GitHub](https://https//github.com/maiot-io/zenml).

## Using Docker[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/using-docker.html#using-docker)

Not all ZenML Pipelines \(and Steps\) are executed in a host-native environment \(e.g. your local development machine\). Some Backends rather rely on [Docker](https://www.docker.com/) images.

### When users need to think about Docker Images[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/using-docker.html#when-users-need-to-think-about-docker-images)

Whenever a pipeline is executing non-locally, i.e., when a non-local [Backend](https://docs.zenml.io/backends/what-is-a-backend.html) is specified, there is usually an `image` parameter exposed that takes a Docker image as input.

Because ML practitioners may not be familiar with the Docker paradigm, ZenML ensures that there is a series of sane defaults that kick-in for users who do not want \(or need\) to build their own images. If no image is used a default **Base Image** is used instead. This Base Image contains [all dependencies that come bundled with ZenML](https://docs.zenml.io/getting-started/creating-custom-logic.html).

Some examples of when a Docker image is required:

* When orchestrating a pipeline on a [GCP VM instance](https://docs.zenml.io/backends/orchestrator-backends.html) or on Kubernetes.
* While specifying a GPU [training backend](https://docs.zenml.io/backends/training-backends.html) on the cloud.
* Configuring a [distributed processing backend](https://docs.zenml.io/backends/processing-backends.html) like Google Cloud Dataflow.

### Creating custom images[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/using-docker.html#creating-custom-images)

In cases where the dependencies specified in the base images are not enough, you can easily create a custom image based on the corresponding base image. The base images are hosted on a public Container Registry, namely `[eu.gcr.io/maiot-zenml](http://eu.gcr.io/maiot-zenml)`. The Dockerfiles of all base images can be found in the `zenml/docker` directory of the [source code](https://github.com/maiot-io/zenml).

The easiest way to create your own, custom ZenML Docker Image, is by starting a new Dockerfile, using the ZenML Base Image as `FROM` :

```text
FROM eu.gcr.io/maiot-zenml/zenml:base-0.1.5  # The ZenML Base Image

ADD . .  # adds your working directory to the resulting Docker Image
RUN pip install -r requirements.txt  # install your custom requirements
```

![Copy to clipboard](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/_static/copy-button.svg)

More seasoned readers might notice, that there is no definition of an `ENTRYPOINT` anywhere. The ZenML Docker Images are deliberately designed without an `ENTRYPOINT` , as every backend can ship with a generic or specialised pipeline entrypoint. Routing is therefore handled via container invocation, not through defaults.

Running a `docker build . -f path/to/your/dockerfile -t your-container-registry/your-image-name:your-image-tag` \(given you adjust the paths and names\) will yield you with your very own Docker image. You should push that image to your own container registry, to ensure availability for your pipeline backends, via `docker push your-container-registry/your-image-name:your-image-tag`.

This is by no means a complete guide on building, pushing, and hosting Docker images. We strongly recommend you familiarize yourself with a Container registry of your choosing \(e.g. [Google Container Registry](https://cloud.google.com/container-registry/docs) or [Docker Hub](https://docs.docker.com/docker-hub/)\), and how the backend of your choosing can interact with the individual Registry options to ensure a pipeline’s backend can pull and run your newly built containers.

### Using custom images[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/using-docker.html#using-custom-images)

Once you’ve successfully built and pushed your new Docker Image to a registry you’re ready to use it in your ZenML pipelines. For this example I’ll be re-using our [Tutorial on running a pipeline on GCP](https://github.com/maiot-io/zenml/tree/fc868ee5e5589ef0c09e30be9c2eab4897bfb140/tutorials/running-a-pipeline-on-a-google-cloud-vm.md).

Your new orchestration backend instantiation looks like this:

```text
# Let's define the image you'll want to use:
custom_docker_image = 'your-container-registry/your-image-name:your-image-tag'

# taken straigt from the Google Cloud VM example
artifact_store = 'gs://your-bucket-name/optional-subfolder'
project = 'PROJECT'  # the project to launch the VM in
zone = 'europe-west1-b'  # the zone to launch the VM in
cloudsql_connection_name = 'PROJECT:REGION:INSTANCE'
mysql_db = 'DATABASE'
mysql_user = 'USERNAME'
mysql_pw = 'PASSWORD'

# Run the pipeline on a Google Cloud VM
training_pipeline.run(
    backend=OrchestratorGCPBackend(
        cloudsql_connection_name=cloudsql_connection_name,
        project=project,
        zone=zone,
        image=custom_docker_image,  # this is it - your pipeline will use your very own Docker image.
    ),
    metadata_store=MySQLMetadataStore(
        host='127.0.0.1',
        port=3306,
        database=mysql_db,
        username=mysql_user,
        password=mysql_pw,
    ),
    artifact_store=ArtifactStore(artifact_store)
)
```

![Copy to clipboard](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/_static/copy-button.svg)

For more information on individual backends and if they have support for Docker Images please check the corresponding documentation.

