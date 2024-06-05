# Reuse Docker builds

## Avoid building Docker images each time a pipeline runs

When using containerized components in your stack, ZenML needs to [build Docker images to remotely execute your code](../configure-python-environments/README.md#execution-environments). Building Docker images without [connecting a git repository](../../user-guide/production-guide/connect-code-repository.md) **includes your step code in the built Docker image**. This, however, means that new Docker images will be built and pushed whenever you make changes to any of your source files.

One way of skipping Docker builds each time is to pass in the ID of a `build` as you run the pipeline:

```python
my_pipeline = my_pipeline.with_options(build=<BUILD_ID>)
```

or when running a pipeline from the CLI:

```shell
zenml pipeline run <PIPELINE_NAME> --build=<BUILD_ID>
```

Please note, that this means specifying a custom build when running a pipeline will **not run the code on your client machine** but will use the code **included in the Docker images of the build**. As a consequence, even if you make local code changes, reusing a build will _always_ execute the code bundled in the Docker image, rather than the local code. Therefore, if you would like to reuse a Docker build AND make sure your local code changes are also downloaded into the image, you need to [connect a git repository](use-code-repositories-to-speed-up-docker-build-times.md).


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
