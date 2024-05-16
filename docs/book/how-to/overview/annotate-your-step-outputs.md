---
description: >-
  Step outputs are stored in your artifact store. Annotate and name them to make
  more explicit.
---

# Annotate your step outputs

## Step output names

By default, ZenML uses the output name `output` for single output steps and `output_0, output_1, ...` for steps with multiple outputs. These output names are used to display your outputs in the dashboard and [fetch them after your pipeline is finished](../../user-guide/starter-guide/fetching-pipelines.md).

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
If you do not give your outputs custom names, the created artifacts will be named `{pipeline_name}::{step_name}::output` or `{pipeline_name}::{step_name}::output_{i}` in the dashboard. See the [documentation on artifact versioning and configuration](../../user-guide/starter-guide/manage-artifacts.md) for more information.
{% endhint %}
