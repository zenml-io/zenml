# Which files are built into the image

ZenML determines the root directory of your source files in the following order:

* If you've initialized zenml (`zenml init`) in your current working directory or one of its parent directories, the repository root directory will be used.
* Otherwise, the parent directory of the Python file you're executing will be the source root. For example, running `python /path/to/file.py`, the source root would be `/path/to`.

You can specify how the files inside this root directory are handled using the following three attributes on the [DockerSettings](https://sdkdocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.docker_settings.DockerSettings):
* `allow_download_from_code_repository`: If this is set to `True` and your files are inside a registered [code repository](../../project-setup-and-management/setting-up-a-project-repository/connect-your-git-repository.md) and the repository has no local changes, the files will be downloaded from the code repository and not included in the image.
* `allow_download_from_artifact_store`: If the previous option is disabled or no code repository without local changes exists for the root directory, ZenML will archive and upload your code to the artifact store if this is set to `True`.
* `allow_including_files_in_images`: If both previous options were disabled or not possible, ZenML will include your files in the Docker image if this option is enabled. This means a new Docker image has to be built each time you modify one of your code files.

{% hint style="warning" %}
Setting all of the above attributes to `False` is not recommended and will most likely cause unintended and unanticipated behavior when running your pipelines. If you do this, you're responsible that all your files are at the correct paths in the Docker images that will be used to run your pipeline steps.
{% endhint %}

## Control which files get downloaded

When downloading files either from a code repository or the artifact store, ZenML downloads all contents of the root directory into the Docker container. To exclude files, track your code in a Git repository use a [gitignore](https://git-scm.com/docs/gitignore/en) to specify which files should be excluded.

## Control which files get included

When including files in the image, ZenML copies all contents of the root directory into the Docker image. To exclude files and keep the image smaller, use a [.dockerignore file](https://docs.docker.com/engine/reference/builder/#dockerignore-file) in either of the following ways:

* Have a file called `.dockerignore` in your source root directory.
* Explicitly specify a `.dockerignore` file to use:

    ```python
    docker_settings = DockerSettings(build_config={"dockerignore": "/path/to/.dockerignore"})

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


