---
description: >
  Learn how to reuse builds to speed up your pipeline runs.
---

# How to reuse builds

When you run a pipeline, ZenML will check if a build with the same pipeline and stack exists. If it does, it will reuse that build. If it doesn't, ZenML will create a new build. This guide explains what a build is and the best practices around reusing builds.

## What is a build?

A pipeline build is an encapsulation of a pipeline and the stack it was run on. It contains the Docker images that were built for the pipeline with all the requirements from the stack, integrations and the user. Optionally, it also contains the pipeline code.

You can list all the builds for a pipeline using the CLI:

```bash
zenml pipeline builds list --pipeline_id='startswith:ab53ca'
```

You can also create a build manually using the CLI:

```bash
zenml pipeline build --stack vertex-stack my_module.my_pipeline_instance
```

You can use the options to specify the configuration file and the stack to use for the build. The source should be a path to a pipeline instance. Learn more about the build function [here](https://sdkdocs.zenml.io/latest/core_code_docs/core-new/#zenml.new.pipelines.pipeline.Pipeline.build).

## Reusing builds

As already mentioned, ZenML will find an existing build if it matches your pipeline and stack, by itself. However, you can also force it to use a specific build by [passing the build ID](../../pipeline-development/use-configuration-files/what-can-be-configured.md#build-id) to the `build` parameter of the pipeline configuration.

While reusing Docker builds is useful, it can be limited. This is because specifying a custom build when running a pipeline will **not run the code on your client machine** but will use the code **included in the Docker images of the build**. As a consequence, even if you make local code changes, reusing a build will _always_ execute the code bundled in the Docker image, rather than the local code. Therefore, if you would like to reuse a Docker build AND make sure your local code changes are also downloaded into the image, you need to disconnect your code from the build. You can do this either by registering a code repository or by letting ZenML use the artifact store to upload your code.

## Use the artifact store to upload your code

You can also let ZenML use the artifact store to upload your code. This is the default behavior if no code repository is detected and the `allow_download_from_artifact_store` flag is not set to `False` in your `DockerSettings`.

## Use code repositories to speed up Docker build times

One way to speed up Docker builds is to connect a git repository. Registering a [code repository](../../../user-guide/production-guide/connect-code-repository.md) lets you avoid building images each time you run a pipeline **and** quickly iterate on your code. When running a pipeline that is part of a local code repository checkout, ZenML can instead build the Docker images without including any of your source files, and download the files inside the container before running your code. This greatly speeds up the building process and also allows you to reuse images that one of your colleagues might have built for the same stack.

ZenML will **automatically figure out which builds match your pipeline and reuse the appropriate build id**. Therefore, you **do not** need to explicitly pass in the build id when you have a clean repository state and a connected git repository. This approach is **highly recommended**. See an end to end example [here](../../../user-guide/production-guide/connect-code-repository.md).

{% hint style="warning" %}
In order to benefit from the advantages of having a code repository in a project, you need to make sure that **the relevant integrations are installed for your ZenML installation.**. For instance, let's assume you are working on a project with ZenML and one of your team members has already registered a corresponding code repository of type `github` for it. If you do `zenml code-repository list`, you would also be able to see this repository. However, in order to fully use this repository, you still need to install the corresponding integration for it, in this example the `github` integration.

```sh
zenml integration install github
```
{% endhint %}

### Detecting local code repository checkouts

Once you have registered one or more code repositories, ZenML will check whether the files you use when running a pipeline are tracked inside one of those code repositories. This happens as follows:

* First, the [source root](./which-files-are-built-into-the-image.md) is computed
* Next, ZenML checks whether this source root directory is included in a local checkout of one of the registered code repositories

### Tracking code versions for pipeline runs

If a [local code repository checkout](#detecting-local-code-repository-checkouts) is detected when running a pipeline, ZenML will store a reference to the current commit for the pipeline run, so you'll be able to know exactly which code was used. Note that this reference is only tracked if your local checkout is clean (i.e. it does not contain any untracked or uncommitted files). This is to ensure that your pipeline is actually running with the exact code stored at the specific code repository commit.

### Tips and best practices

It is also important to take some additional points into consideration:

* The file download is only possible if the local checkout is clean (i.e. it does not contain any untracked or uncommitted files) and the latest commit has been pushed to the remote repository. This is necessary as otherwise, the file download inside the Docker container will fail.
* If you want to disable or enforce the downloading of files, check out [this docs page](./docker-settings-on-a-pipeline.md) for the available options.


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
