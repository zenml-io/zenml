# Use code repositories to speed up docker build times

ZenML automatically [builds and pushes Docker images](../understanding-environments/#execution-environments) when running a pipeline on a stack requiring Docker images. To run this build step separately without running the pipeline, call:

```python
my_pipeline.build(...)
```

in Python or using the CLI command:

```shell
# If running the first time, register pipeline to get name and ID
zenml pipeline register [OPTIONS] my_module.my_pipeline

# Build docker images using the image builder defined in the stack and push to the container registry defined in the stack
zenml pipeline build [OPTIONS] PIPELINE_NAME_OR_ID
```

You can see all pipeline builds with the command:

This will register the build output in the ZenML database and allow you to use the built images when running a pipeline later.

```bash
zenml pipeline builds list
```

To use a registered build when running a pipeline, pass it as an argument in Python

```python
my_pipeline = my_pipeline.with_options(build=<BUILD_ID>)
```

or when running a pipeline from the CLI

```bash
zenml pipeline run <PIPELINE_NAME> --build=<BUILD_ID>
```

### Automate build reuse by connecting a code repository

Building Docker images without [connecting a git repository](../../user-guide/production-guide/connect-code-repository.md) includes your step code. This means specifying a custom build when running a pipeline will **not run the code on your client machine** but will use the code **included in the Docker images of the build**. This allows you to make local code changes, but reusing a build from before will _always_ execute the code bundled in the Docker image, rather than the local code. This is why you also have to explicitly specify the `build_id` when running a pipeline.

To avoid this, disconnect your code from the build by [connecting a git repository](../configuring-zenml/connect-your-git-repository.md). Registering a code repository lets you avoid building images each time you run a pipeline and quickly iterate on your code. Also, ZenML will automatically figure out which builds match your pipeline and reuse the appropriate execution environment. This approach is highly recommended. Read more [here](../../user-guide/production-guide/connect-code-repository.md).
