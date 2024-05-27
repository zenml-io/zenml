# Use code repositories to speed up docker build times

### Automate build reuse by connecting a code repository

Building Docker images without [connecting a git repository](../../user-guide/production-guide/connect-code-repository.md) includes your step code. This means specifying a custom build when running a pipeline will **not run the code on your client machine** but will use the code **included in the Docker images of the build**. This allows you to make local code changes, but reusing a build from before will _always_ execute the code bundled in the Docker image, rather than the local code. This is why you also have to explicitly specify the `build_id` when running a pipeline.

To avoid this, disconnect your code from the build by [connecting a git repository](../setting-up-a-project-repository/connect-your-git-repository.md). Registering a code repository lets you avoid building images each time you run a pipeline and quickly iterate on your code. Also, ZenML will automatically figure out which builds match your pipeline and reuse the appropriate execution environment. This approach is highly recommended. Read more [here](../../user-guide/production-guide/connect-code-repository.md).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
