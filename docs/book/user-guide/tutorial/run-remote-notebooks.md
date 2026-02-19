---
description: Leveraging Jupyter notebooks with ZenML.
icon: notebook
---

# Running notebooks remotely

A Jupyter notebook is often the fastest way to prototype an ML experiment, but sooner or later you will want to execute heavy‑weight **ZenML steps or pipelines on a remote stack**.  This tutorial shows how to

1. Understand the limitations of defining steps inside notebook cells;
2. Execute a *single* step remotely from a notebook; and
3. Promote your notebook code to a full pipeline that can run anywhere.

---

## Why there are limitations

When you call a step or pipeline from a notebook, ZenML needs to export the cell code into a standalone Python module that gets packaged into a Docker image.  Any magic commands, cross‑cell references or missing imports break that process.  Keep your cells **pure and self‑contained** and you are good to go.

### Checklist for step cells

- Only regular **Python** code – no Jupyter magics (`%…`) or shell commands (`!…`).
- Do **not** access variables or functions defined in *other* notebook cells.  Import from `.py` files instead.
- Include **all imports** you need inside the cell (including `from zenml import step`).

---

## Run a single step remotely

You can treat a ZenML `@step` like a normal Python function call.  ZenML will automatically create a *temporary* pipeline with just this one step and run it on your active stack.

```python
from zenml import step
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

@step(step_operator=True)  # remove argument if not using a step operator
def svc_trainer(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    gamma: float = 0.001,
) -> tuple[ClassifierMixin, float]:
    """Train an SVC model and return it together with its training accuracy."""
    model = SVC(gamma=gamma)
    model.fit(X_train.to_numpy(), y_train.to_numpy())
    acc = model.score(X_train.to_numpy(), y_train.to_numpy())
    print(f"Train accuracy: {acc}")
    return model, acc

# Prepare some data …
X_train = pd.DataFrame(...)
y_train = pd.Series(...)

# ☁️  This call executes remotely on the active stack
model, train_acc = svc_trainer(X_train=X_train, y_train=y_train)
```

> **Tip:** If you prefer YAML, you can also pass a `config_path` when calling the step.

---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


## Next steps – from notebook to production

Once your logic stabilizes it usually makes sense to move code out of the notebook and into regular Python modules so that it can be version‑controlled and tested.  At that point just assemble the same steps inside a `@pipeline` function and trigger it from the CLI or a CI workflow.

For a deeper dive into how ZenML packages notebook code have a look at the [Notebook Integration docs](https://docs.zenml.io/user-guides/tutorial/run-remote-notebooks).