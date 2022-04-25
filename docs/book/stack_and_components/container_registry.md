# Container Registry

A container registry is a store for (Docker) containers. A ZenML workflow involving a container registry would
automatically containerize your code to be transported across stacks running remotely. As part of the deployment to the
cluster, the ZenML base image would be downloaded (from a cloud container registry) and used as the basis for the
deployed 'run'.

For instance, when you are running a local container-based stack, you would therefore have a local container registry
which stores the container images you create that bundle up your pipeline code. You could also use a remote container
registry like the Elastic Container Registry at AWS in a more production setting.

Check out the CLI commands concerning the container registry 
[here](https://apidocs.zenml.io/latest/cli/#zenml.cli--customizing-your-container-registry).