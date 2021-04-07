# Using Docker

Not all ZenML Pipelines \(and Steps\) are executed in a host-native environment \(e.g. your local development machine\). Some Backends rather rely on [Docker](https://www.docker.com/) images.

## When users need to think about Docker Images

Whenever a pipeline is executing non-locally, i.e., when a non-local [Backend](https://docs.zenml.io/backends/what-is-a-backend.html) is specified, there is usually an `image` parameter exposed that takes a Docker image as input.

Because ML practitioners may not be familiar with the Docker paradigm, ZenML ensures that there is a series of sane defaults that kick-in for users who do not want \(or need\) to build their own images. If no image is used a default **Base Image** is used instead. This Base Image contains [all dependencies that come bundled with ZenML](https://docs.zenml.io/getting-started/creating-custom-logic.html).

Some examples of when a Docker image is required:

* When orchestrating a pipeline on a [GCP VM instance](https://docs.zenml.io/backends/orchestrator-backends.html) or on Kubernetes.
* While specifying a GPU [training backend](https://docs.zenml.io/backends/training-backends.html) on the cloud.
* Configuring a [distributed processing backend](https://docs.zenml.io/backends/processing-backends.html) like Google Cloud Dataflow.

## Creating custom images

In cases where the dependencies specified in the base images are not enough, you can easily create a custom image based on the corresponding base image. The base images are hosted on a public Container Registry, namely `[eu.gcr.io/maiot-zenml](http://eu.gcr.io/maiot-zenml)`. The Dockerfiles of all base images can be found in the `zenml/docker` directory of the [source code](https://github.com/maiot-io/zenml).

The easiest way to create your own, custom ZenML Docker Image, is by starting a new Dockerfile, using the ZenML Base Image as `FROM` :

```text
FROM eu.gcr.io/maiot-zenml/zenml:base-0.1.5  # The ZenML Base Image

ADD . .  # adds your working directory to the resulting Docker Image
RUN pip install -r requirements.txt  # install your custom requirements
```

More seasoned readers might notice, that there is no definition of an `ENTRYPOINT` anywhere. The ZenML Docker Images are deliberately designed without an `ENTRYPOINT` , as every backend can ship with a generic or specialised pipeline entrypoint. Routing is therefore handled via container invocation, not through defaults.

Running a `docker build . -f path/to/your/dockerfile -t your-container-registry/your-image-name:your-image-tag` \(given you adjust the paths and names\) will yield you with your very own Docker image. You should push that image to your own container registry, to ensure availability for your pipeline backends, via `docker push your-container-registry/your-image-name:your-image-tag`.

This is by no means a complete guide on building, pushing, and hosting Docker images. We strongly recommend you familiarize yourself with a Container registry of your choosing \(e.g. [Google Container Registry](https://cloud.google.com/container-registry/docs) or [Docker Hub](https://docs.docker.com/docker-hub/)\), and how the backend of your choosing can interact with the individual Registry options to ensure a pipeline's backend can pull and run your newly built containers.

## Using custom images

Once you've successfully built and pushed your new Docker Image to a registry you're ready to use it in your ZenML pipelines. For this example I'll be re-using our [Tutorial on running a pipeline on GCP](https://github.com/maiot-io/zenml/tree/fc868ee5e5589ef0c09e30be9c2eab4897bfb140/tutorials/running-a-pipeline-on-a-google-cloud-vm.md).

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

