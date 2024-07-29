# Build the pipeline without running

Pipeline builds are usually done implicitly when you run a pipeline on a docker-based orchestrator. But you are also able to just build a pipeline without running this. To do this you simply do this:

```python
from zenml import pipeline

@pipeline
def my_pipeline(...):
    ...

my_pipeline.build()
```

You can see all pipeline builds with the command:

This will register the build output in the ZenML database and allow you to use the built images when running a pipeline later.

```bash
zenml pipeline builds list
```

To [reuse a registered build](./reuse-docker-builds.md) when running a pipeline, pass it as an argument in Python

```python
my_pipeline = my_pipeline.with_options(build=<BUILD_ID>)
```

or when running a pipeline from the CLI

```bash
zenml pipeline run <PIPELINE_SOURCE_PATH> --build=<BUILD_ID>
```

{% hint style="info" %}
The source path of your pipeline will be `run.my_pipeline`. In a generalized
way, this will be `<MODULE_PATH>.<PIPELINE_FUNCTION_NAME>`. If the python file
defining the pipeline is not in your current directory, the module path consists
of the full path to the file, separated by dots, e.g.
`some_directory.some_file.my_pipeline`.
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


