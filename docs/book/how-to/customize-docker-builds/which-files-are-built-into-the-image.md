# Which files are built into the image

ZenML determines the root directory of your source files in the following order:

* If you've initialized zenml (`zenml init`), the repository root directory will be used.
* Otherwise, the parent directory of the Python file you're executing will be the source root. For example, running `python /path/to/file.py`, the source root would be `/path/to`.

You can specify how these files are handled using the `source_files` attribute on the [DockerSettings](https://sdkdocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.docker_settings.DockerSettings):

* The default behavior `download_or_include`: The files will be downloaded if they're inside a registered [code repository](../setting-up-a-project-repository/connect-your-git-repository.md) and the repository has no local changes, otherwise, they will be included in the image.
* If you want your files to be included in the image in any case, set the `source_files` attribute to `include`.
* If you want your files to be downloaded in any case, set the `source_files` attribute to `download`. If this is specified, the files must be inside a registered code repository and the repository must have no local changes, otherwise the Docker build will fail.
* If you want to prevent ZenML from copying or downloading any of your source files, you can do so by setting the `source_files` attribute on the Docker settings to `ignore`. This is an advanced feature and will most likely cause unintended and unanticipated behavior when running your pipelines. If you use this, make sure to copy all the necessary files to the correct paths yourself.

**Which files get included**

When including files in the image, ZenML copies all contents of the root directory into the Docker image. To exclude files and keep the image smaller, use a [.dockerignore file](https://docs.docker.com/engine/reference/builder/#dockerignore-file) in either of the following ways:

* Have a file called `.dockerignore` in your source root directory.
*   Explicitly specify a `.dockerignore` file to use:

    ```python
    docker_settings = DockerSettings(dockerignore="/path/to/.dockerignore")

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


