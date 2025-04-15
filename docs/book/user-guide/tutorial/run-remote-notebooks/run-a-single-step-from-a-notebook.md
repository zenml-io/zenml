# Run a single step from a notebook

If you want to run just a single step remotely from a notebook, you can simply call the step
as you would with a normal Python function. ZenML will internally create a pipeline with just your step
and run it on the active stack.

{% hint style="warning" %}
When defining a step that should be run remotely in a notebook, make sure you're
aware of all the [limitations](limitations-of-defining-steps-in-notebook-cells.md) that apply.
{% endhint %}


```python
from zenml import step
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

# Configure the step to use a step operator. If you're not using
# a step operator, you can remove this and the step will run on
# your orchestrator instead.
@step(step_operator="<STEP_OPERATOR_NAME>")
def svc_trainer(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    gamma: float = 0.001,
) -> Tuple[
    Annotated[ClassifierMixin, "trained_model"],
    Annotated[float, "training_acc"],
]:
    """Train a sklearn SVC classifier."""

    model = SVC(gamma=gamma)
    model.fit(X_train.to_numpy(), y_train.to_numpy())

    train_acc = model.score(X_train.to_numpy(), y_train.to_numpy())
    print(f"Train accuracy: {train_acc}")

    return model, train_acc


X_train = pd.DataFrame(...)
y_train = pd.Series(...)

# Call the step directly. This will internally create a
# pipeline with just this step, which will be executed on
# the active stack.
model, train_acc = svc_trainer(X_train=X_train, y_train=y_train)
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>