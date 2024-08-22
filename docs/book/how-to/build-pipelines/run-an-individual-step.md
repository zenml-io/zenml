# Run an individual step on your stack

If you want to run just an invividual step on your stack, you can simply call the step
as you would with a normal Python function. ZenML will internally create a pipeline with just your step
and run it on the active stack.

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

## Run the underlying step function directly

If you instead want to run your step function without ZenML getting involved, you
can use the `entrypoint(...)` method of a step:

```python
X_train = pd.DataFrame(...)
y_train = pd.Series(...)

model, train_acc = svc_trainer.entrypoint(X_train=X_train, y_train=y_train)
```

{% hint style="info" %}
If you want to make this the default behavior when calling a step, you
can set the `ZENML_RUN_SINGLE_STEPS_WITHOUT_STACK` environment variable to `True`.
Once you do that, calling `svc_trainer(...)` will simply call the underlying function and
not use your ZenML stack.
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>