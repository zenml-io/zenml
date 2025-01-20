# Use your own Docker files

In some cases, you might not want full control over the resulting Docker image but want to build a parent image dynamically each time a pipeline is executed. To make this process easier, ZenML allows you to specify a custom Dockerfile as well as `build context` directory and build options. ZenML then builds an intermediate image based on the Dockerfile you specified and uses the intermediate image as the parent image.

Here is how the build process looks like:

* **No `Dockerfile` specified**: If any of the options regarding requirements, environment variables or copying files require us to build an image, ZenML will build this image. Otherwise the `parent_image` will be used to run the pipeline.
* **`Dockerfile` specified**: ZenML will first build an image based on the specified `Dockerfile`. If any of the options regarding requirements, environment variables or copying files require an additional image built on top of that, ZenML will build a second image. If not, the image build from the specified `Dockerfile` will be used to run the pipeline.

Depending on the configuration of the [`DockerSettings`](https://sdkdocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.docker_settings.DockerSettings) object, requirements will be installed in the following order (each step optional): 

* The packages installed in your local Python environment.
* The packages specified via the `requirements` attribute.
* The packages specified via the `required_integrations` and potentially stack requirements.

{% hint style="info" %}
Depending on the configuration of your Docker settings, this intermediate image might also be used directly to execute your pipeline steps.
{% endhint %}

```python
docker_settings = DockerSettings(
    dockerfile="/path/to/dockerfile",
    build_context_root="/path/to/build/context",
    parent_image_build_config={
        "build_options": ...
        "dockerignore": ...
    }
)


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
