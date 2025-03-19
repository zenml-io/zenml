---
description: >-
  Step outputs are stored in your artifact store. Annotate and name them to make
  more explicit.
---

# Step output typing and annotation

## Type annotations

Your functions will work as ZenML steps even if you don't provide any type annotations for their inputs and outputs. However, adding type annotations to your step functions gives you lots of additional benefits:

* **Type validation of your step inputs**: ZenML makes sure that your step functions receive an object of the correct type from the upstream steps in your pipeline.
* **Better serialization**: Without type annotations, ZenML uses [Cloudpickle](https://github.com/cloudpipe/cloudpickle) to serialize your step outputs. When provided with type annotations, ZenML can choose a [materializer](https://docs.zenml.io/getting-started/core-concepts#materializers) that is best suited for the output. In case none of the builtin materializers work, you can even [write a custom materializer](https://docs.zenml.io/how-to/data-artifact-management/handle-data-artifacts/handle-custom-data-types).

{% hint style="warning" %}
ZenML provides a built-in [CloudpickleMaterializer](https://sdkdocs.zenml.io/latest/core_code_docs/core-materializers.html#zenml.materializers.cloudpickle_materializer) that can handle any object by saving it with [cloudpickle](https://github.com/cloudpipe/cloudpickle). However, this is not production-ready because the resulting artifacts cannot be loaded when running with a different Python version. In such cases, you should consider building a [custom Materializer](https://docs.zenml.io/how-to/data-artifact-management/handle-data-artifacts/handle-custom-data-types#custom-materializers) to save your objects in a more robust and efficient format.

Moreover, using the `CloudpickleMaterializer` could allow users to upload of any kind of object. This could be exploited to upload a malicious file, which could execute arbitrary code on the vulnerable system.
{% endhint %}

```python
from typing import Tuple
from zenml import step

@step
def square_root(number: int) -> float:
    return number ** 0.5

# To define a step with multiple outputs, use a `Tuple` type annotation
@step
def divide(a: int, b: int) -> Tuple[int, int]:
    return a // b, a % b
```

If you want to make sure you get all the benefits of type annotating your steps, you can set the environment variable `ZENML_ENFORCE_TYPE_ANNOTATIONS` to `True`. ZenML will then raise an exception in case one of the steps you're trying to run is missing a type annotation.

### Tuple vs multiple outputs

It is impossible for ZenML to detect whether you want your step to have a single output artifact of type `Tuple` or multiple output artifacts just by looking at the type annotation.

We use the following convention to differentiate between the two: When the `return` statement is followed by a tuple literal (e.g. `return 1, 2` or `return (value_1, value_2)`) we treat it as a step with multiple outputs. All other cases are treated as a step with a single output of type `Tuple`.

```python
from zenml import step
from typing_extensions import Annotated
from typing import Tuple

# Single output artifact
@step
def my_step() -> Tuple[int, int]:
    output_value = (0, 1)
    return output_value

# Single output artifact with variable length
@step
def my_step(condition) -> Tuple[int, ...]:
    if condition:
        output_value = (0, 1)
    else:
        output_value = (0, 1, 2)

    return output_value

# Single output artifact using the `Annotated` annotation
@step
def my_step() -> Annotated[Tuple[int, ...], "my_output"]:
    return 0, 1


# Multiple output artifacts
@step
def my_step() -> Tuple[int, int]:
    return 0, 1


# Not allowed: Variable length tuple annotation when using
# multiple output artifacts
@step
def my_step() -> Tuple[int, ...]:
    return 0, 1
```

## Step output names

By default, ZenML uses the output name `output` for single output steps and `output_0, output_1, ...` for steps with multiple outputs. These output names are used to display your outputs in the dashboard and [fetch them after your pipeline is finished](fetching-pipelines.md).

If you want to use custom output names for your steps, use the `Annotated` type annotation:

```python
from typing_extensions import Annotated  # or `from typing import Annotated on Python 3.9+
from typing import Tuple
from zenml import step

@step
def square_root(number: int) -> Annotated[float, "custom_output_name"]:
    return number ** 0.5

@step
def divide(a: int, b: int) -> Tuple[
    Annotated[int, "quotient"],
    Annotated[int, "remainder"]
]:
    return a // b, a % b
```

{% hint style="info" %}
If you do not give your outputs custom names, the created artifacts will be named `{pipeline_name}::{step_name}::output` or `{pipeline_name}::{step_name}::output_{i}` in the dashboard. See the [documentation on artifact versioning and configuration](https://docs.zenml.io/user-guides/starter-guide/manage-artifacts) for more information.
{% endhint %}


***

### See Also:


<table data-view="cards">
    <thead>
    <tr>
        <th></th>
        <th></th>
        <th></th>
        <th data-hidden data-card-target data-type="content-ref"></th>
    </tr>
    </thead>
    <tbody>
    <tr>
        <td>Learn more about output annotation here</td>
        <td></td>
        <td></td>
        <td><a href="https://docs.zenml.io/how-to/data-artifact-management/handle-data-artifacts/return-multiple-outputs-from-a-step">return-multiple-outputs-from-a-step.md</a></td>
    </tr>
    <tr>
        <td>For custom data types you should check these docs out</td>
        <td></td>
        <td></td>
        <td><a href="https://docs.zenml.io/how-to/data-artifact-management/handle-data-artifacts/handle-custom-data-types">handle-custom-data-types.md</a></td>
    </tr>
    </tbody>
</table>


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
