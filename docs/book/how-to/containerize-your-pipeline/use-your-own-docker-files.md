# Use your own docker files

In some cases, you might want full control over the resulting Docker image but want to build a Docker image dynamically each time a pipeline is executed. To make this process easier, ZenML allows you to specify a custom Dockerfile as well as `build context` directory and build options. ZenML then builds an intermediate image based on the Dockerfile you specified and uses the intermediate image as the parent image.

{% hint style="info" %}
Depending on the configuration of your Docker settings, this intermediate image might also be used directly to execute your pipeline steps.
{% endhint %}

```python
docker_settings = DockerSettings(
    dockerfile="/path/to/dockerfile",
    build_context_root="/path/to/build/context",
    build_options=...
)


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```
