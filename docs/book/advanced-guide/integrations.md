---
description: 'Environment, docker, dependencies'
---

# Managing the environment

## Environment and custom dependencies

ZenML comes pre-installed with some common ML libraries. These include:

* `tfx` &gt;= 0.25.0
* `tensorflow` &gt;= 2.3.0
* `apache-beam` &gt;= 2.26.0
* `plotly` &gt;= 4.0.0
* `numpy` &gt;= 1.18.0

The full list can be found [here](https://github.com/maiot-io/zenml/blob/main/setup.py).

You can install any other dependencies alongisde of ZenML and use them in your code as long as they do not conflict with the dependencies listed above. E.g `torch`, `scikit-learn`, `pandas` etc are perfectly fine. However, using `tensoflow` &lt; 2.3.0 currently is not supported.

### Extensibility with integrations

The Machine Learning landscape is evolving at a rapid pace. ZenML decouples the experiment workflow from the tooling by providing integrations to solutions for specific aspects of your ML pipelines. It is designed with extensibility in mind. This means that the goal of ZenML is to be able to work with any ML tool in the eco-system seamlessly. 

ZenML uses the `extra_requires` field provided in Python [setuptools](https://setuptools.readthedocs.io/en/latest/setuptools.html) which allows for defining plugin-like dependencies for integrations. These integrations can then accessed via pip at installation time with the `[]` operators. E.g.

```bash
pip install zenml[pytorch]
```

Will unlock the `pytorch` integration for ZenML, allowing users to use the `PyTorchTrianerStep` for example.

To install all dependencies, use:

```bash
pip install zenml[all]
```

{% hint style="warning" %}
Using the \[all\] keyword will result in a significantly bigger package installation.
{% endhint %}

In order to see the full list of integrations available, see the [setup.py on GitHub](https://github.com/maiot-io/zenml/blob/main/setup.py).

We would be happy to see [your contributions for more integrations](https://github.com/maiot-io/zenml/) if the ones we have currently support not fulfill your requirements. Also let us know via [slack](https://zenml.io/slack-invite) what integrations to add!

### Types of integrations

Integrations can be in the form of `backends` and `steps`. One group of integrations might bring multiple of these. E.g. The `gcp` integration brings orchestrator backends, dataflow processing backend and Google Cloud AI Platform training backend.

#### Orchestration

When you configure an orchestration backend for your pipeline, the environment you execute actual `pipeline.run()` will launch all pipeline steps at the configured orchestration backend, not the local environment. ZenML will attempt to use credentials for the orchestration backend in question from the current environment. **NOTE:** If no further pipeline configuration if provided \(e.g. processing or training backends\), the orchestration backend will also run all pipeline steps.

A quick overview of the currently supported backends:

| **Orchestrator** | **Status** |
| :--- | :--- |
| Google Cloud VMs | &gt;= 0.1.5 |
| Kubernetes | &gt;0.2.0 |
| AWS VMs | &gt;0.3.2 |
| Azure VMs | WIP |
| Kubeflow | WIP |

Integrating custom orchestration backends is fairly straightforward. Check out our example implementation of [Google Cloud VMs](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/tutorials/running-a-pipeline-on-a-google-cloud-vm.html) to learn more about building your own integrations.

#### \(Distributed\) Processing

Sometimes, pipeline steps just need more scalability than what your orchestration backend can offer. That’s when the natively distributable codebase of ZenML can shine - it’s straightforward to run pipeline steps on processing backends like Google Dataflow or Apache Spark.

ZenML is using Apache Beam for its pipeline steps, therefore backends rely on the functionality of Apache Beam. A processing backend will execute all pipeline steps before the actual training.

Processing backends can be used to great effect in conjunction with an orchestration backend. To give a practical example: You can orchestrate your pipelines using Google Cloud VMs and configure to use a service account with permissions for Google Dataflow and Google Cloud AI Platform. That way you don’t need to have very open permissions on your personal IAM user, but can relay authority to service-accounts within Google Cloud.

We’re adding support for processing backends continuously:

| **Backend** | **Status** |
| :--- | :--- |
| Google Cloud Dataflow | &gt;= 0.1.5 |
| Apache Spark | WIP |
| AWS EMR | WIP |
| Flink | planned: Q3/2021 |

#### Training

Many ML use-cases and model architectures require GPUs/TPUs. ZenML offers integrations to Cloud-based ML training offers and provides a way to extend the training interface to allow for self-built training backends.

Some of these integrations rely on Docker containers or other methods of transmitting code. Please see the documentation for a specific training backend for further details.

| **Backend** | **Status** |
| :--- | :--- |
| Google Cloud AI Platform | &gt;= 0.1.5 |
| PyTorch | &gt;= 0.2.0 |
| AWS Sagemaker | WIP |
| Azure Machine Learning | planned: Q3/2021 |

#### Serving

Every ZenML pipeline yields a servable model, ready to be used in your existing architecture - for example as additional input for your CI/CD pipelines. To accommodate other architectures, ZenML has support for a growing number of dedicated serving integrations, with clear linkage and lineage from data to deployment. These serving integrations come mostly in the form of `DeployerStep`’s to be used inside ZenML pipelines.

| **Backend** | **Status** |
| :--- | :--- |
| Google Cloud AI Platform | &gt;= 0.1.5 |
| Cortex | &gt;0.2.1 |
| AWS Sagemaker | WIP |
| Seldon | planned: Q1/2021 |
| Azure Machine Learning | planned: Q3/2021 |

### Other libraries

If the integrations above do not fulfill your requirements and more dependencies are required, then there is always the option to simply install the dependencies alongside ZenML in your repository. If going down this route, one must ensure that the added dependencies do not clash with any [dependency bundled with ZenML](https://github.com/maiot-io/zenml/blob/main/setup.py). 

## Using Docker

Not all ZenML Pipelines \(and Steps\) are executed in a host-native environment \(e.g. your local development machine\). Some Backends rather rely on [Docker](https://www.docker.com/) images.

### When users need to think about Docker Images

Whenever a pipeline is executing non-locally, i.e., when a non-local [Backend](https://docs.zenml.io/backends/what-is-a-backend.html) is specified, there is usually an `image` parameter exposed that takes a Docker image as input.

Because ML practitioners may not be familiar with the Docker paradigm, ZenML ensures that there is a series of sane defaults that kick-in for users who do not want \(or need\) to build their own images. If no image is used a default **Base Image** is used instead. This Base Image contains [all dependencies that come bundled with ZenML](https://docs.zenml.io/getting-started/creating-custom-logic.html).

Some examples of when a Docker image is required:

* When orchestrating a pipeline on a [GCP VM instance](https://docs.zenml.io/backends/orchestrator-backends.html) or on Kubernetes.
* While specifying a GPU [training backend](https://docs.zenml.io/backends/training-backends.html) on the cloud.
* Configuring a [distributed processing backend](https://docs.zenml.io/backends/processing-backends.html) like Google Cloud Dataflow.

### Creating custom images

In cases where the dependencies specified in the base images are not enough, you can easily create a custom image based on the corresponding base image. The base images are hosted on a public Container Registry, namely `[eu.gcr.io/maiot-zenml](http://eu.gcr.io/maiot-zenml)`. The Dockerfiles of all base images can be found in the `zenml/docker` directory of the [source code](https://github.com/maiot-io/zenml).

The easiest way to create your own, custom ZenML Docker Image, is by starting a new Dockerfile, using the ZenML Base Image as `FROM` :

```python
FROM eu.gcr.io/maiot-zenml/zenml:base-0.1.5  # The ZenML Base Image

ADD . .  # adds your working directory to the resulting Docker Image
RUN pip install -r requirements.txt  # install your custom requirements
```

More seasoned readers might notice, that there is no definition of an `ENTRYPOINT` anywhere. The ZenML Docker Images are deliberately designed without an `ENTRYPOINT` , as every backend can ship with a generic or specialised pipeline entrypoint. Routing is therefore handled via container invocation, not through defaults.

Running a `docker build . -f path/to/your/dockerfile -t your-container-registry/your-image-name:your-image-tag` \(given you adjust the paths and names\) will yield you with your very own Docker image. You should push that image to your own container registry, to ensure availability for your pipeline backends, via `docker push your-container-registry/your-image-name:your-image-tag`.

This is by no means a complete guide on building, pushing, and hosting Docker images. We strongly recommend you familiarize yourself with a Container registry of your choosing \(e.g. [Google Container Registry](https://cloud.google.com/container-registry/docs) or [Docker Hub](https://docs.docker.com/docker-hub/)\), and how the backend of your choosing can interact with the individual Registry options to ensure a pipeline’s backend can pull and run your newly built containers.

### Using custom images

Once you’ve successfully built and pushed your new Docker Image to a registry you’re ready to use it in your ZenML pipelines. For this example I’ll be re-using our [Tutorial on running a pipeline on GCP](https://github.com/maiot-io/zenml/tree/fc868ee5e5589ef0c09e30be9c2eab4897bfb140/tutorials/running-a-pipeline-on-a-google-cloud-vm.md).

Your new orchestration backend instantiation looks like this:

```python
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

For more information on individual backends and if they have support for Docker Images please check the corresponding documentation.

