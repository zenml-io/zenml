# Use code repositories to speed up docker build times

## Automate build reuse by connecting a code repository

Building Docker images without [connecting a git repository](../../user-guide/production-guide/connect-code-repository.md) includes your step code. This means specifying a custom build when running a pipeline will **not run the code on your client machine** but will use the code **included in the Docker images of the build**. This allows you to make local code changes, but reusing a build from before will _always_ execute the code bundled in the Docker image, rather than the local code. This is why you also have to explicitly specify the `build_id` when running a pipeline.

To avoid this, disconnect your code from the build by [connecting a git repository](../setting-up-a-project-repository/connect-your-git-repository.md). Registering a code repository lets you avoid building images each time you run a pipeline and quickly iterate on your code. Also, ZenML will automatically figure out which builds match your pipeline and reuse the appropriate execution environment. This approach is highly recommended. Read more [here](../../user-guide/production-guide/connect-code-repository.md).

When using containerized components in your stack, ZenML needs to [build Docker images to remotely execute your code](../configure-python-environments/README#execution-environments). If you're not using a code repository, this code will be included in the Docker images that ZenML builds. This, however, means that new Docker images will be built and pushed whenever you make changes to any of your source files. When running a pipeline that is part of a local code repository checkout, ZenML can instead build the Docker images without including any of your source files, and download the files inside the container before running your code. This greatly speeds up the building process and also allows you to reuse images that one of your colleagues might have built for the same stack.

It is also important to take some additional points into consideration:

* The file download is only possible if the local checkout is clean (i.e. it does not contain any untracked or uncommitted files) and the latest commit has been pushed to the remote repository. This is necessary as otherwise, the file download inside the Docker container will fail.
* If you want to disable or enforce the downloading of files, check out [this docs page](../customize-docker-builds/) for the available options.

{% hint style="warning" %}
In order to benefit from the advantages of having a code repository in a project, you need to make sure that **the relevant integrations are installed for your ZenML installation.**

For instance, let's assume you are working on a project with ZenML and one of your team members has already registered a corresponding code repository of type `github` for it. If you do `zenml code-repository list`, you would also be able to see this repository. However, in order to fully use this repository, you still need to install the corresponding integration for it, in this example the `github` integration.

```sh
zenml integration install github
```
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
