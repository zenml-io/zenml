---
description: Use Annotated to return multiple outputs from a step and name them for easy retrieval and dashboard display.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Return multiple outputs from a step

You can use the `Annotated` type to return multiple outputs from a step and give each output a name. Naming your step outputs will help you retrieve the specific artifact later and also improves the readability of your pipeline's dashboard.

```python
from typing import Annotated, Tuple

import pandas as pd
from zenml import step


@step
def clean_data(
    data: pd.DataFrame,
) -> Tuple[
    Annotated[pd.DataFrame, "x_train"],
    Annotated[pd.DataFrame, "x_test"],
    Annotated[pd.Series, "y_train"],
    Annotated[pd.Series, "y_test"],
]:
    from sklearn.model_selection import train_test_split

    x = data.drop("target", axis=1)
    y = data["target"]

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

    return x_train, x_test, y_train, y_test
```

In this code, the `clean_data` step takes a pandas DataFrame as input and returns a tuple of four elements: `x_train`, `x_test`, `y_train`, and `y_test`. Each element in the tuple is annotated with a specific name using the `Annotated` type.

Inside the step, we split the input data into features (`x`) and target (`y`), and then use `train_test_split` from scikit-learn to split the data into training and testing sets. The resulting DataFrames and Series are returned as a tuple, with each element annotated with its respective name.

By using `Annotated`, we can easily identify and retrieve specific artifacts later in the pipeline. Additionally, the names will be displayed on the pipeline's dashboard, making it more readable and understandable.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
