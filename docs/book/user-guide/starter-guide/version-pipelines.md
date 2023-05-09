---
description: Understand how and when the version of a pipeline is incremented.
---

# Version Pipelines

You might have noticed that when you run a pipeline in ZenML with the same name, but with different steps, it creates a new _version_ of the pipeline. Consider our example pipeline:

```python
@pipeline
def first_pipeline(gamma: float = 0.002):
    X_train, X_test, y_train, y_test = digits_data_loader()
    svc_trainer(gamma=gamma, X_train=X_train, y_train=y_train)
    
if __name__ == "__main__":
    first_pipeline(gamma=0.0015)
```

Running this the first time will create a single `run` for `version 1` of the pipeline called `first_pipeline`.

```
$python main.py
...
Registered pipeline first_pipeline (version 1).
...
```

If you now do it again with different [runtime parameters](parameters.md):

```python
@pipeline
def first_pipeline(gamma: float = 0.002):
    X_train, X_test, y_train, y_test = digits_data_loader()
    svc_trainer(gamma=gamma, X_train=X_train, y_train=y_train)
    
if __name__ == "__main__":
    first_pipeline(gamma=0.0016)
```

This will create _yet another_ `run` for `version 1` of the pipeline called `first_pipeline`. So now the same pipeline has two runs. You can also verify this in the dashboard.

However, now let's change the pipeline configuration itself. You can do this by either modifying the step connections within the `@pipeline` function or by replacing a concrete step with another one. For example lets create an alternative trainer step called `custom_trainer`.

```python
@pipeline
def first_pipeline(gamma: float = 0.002):
    X_train, X_test, y_train, y_test = digits_data_loader()
    custom_trainer(gamma=gamma, X_train=X_test, y_train=y_test)
    
if __name__ == "__main__":
    first_pipeline(gamma=0.0016)
```

```python
$python main.py
...
Registered pipeline first_pipeline (version 1).
...
```

This will now create a single `run` for `version 2` of the pipeline called `first_pipeline`.&#x20;

```bash
//PLACEHOLDER Dashboard Screenshot
```
