---
description: >-
  Learn how to parameterize ZenML pipelines and steps to make them more flexible and reusable.
---

# Execution Parameters

In ZenML, execution parameters allow you to configure the behavior of your pipelines and steps at runtime, making your ML workflows more flexible and reusable. This guide covers all aspects of working with parameters in ZenML.

## Pipeline and Step Parameters

### Basic Parameters

Both pipelines and steps are defined as Python functions, so they can accept parameters just like regular functions:

```python
from zenml import step, pipeline

@step
def train_model(data: dict, learning_rate: float = 0.01) -> None:
    # Use learning_rate parameter
    print(f"Training with learning rate: {learning_rate}")

@pipeline
def training_pipeline(dataset_name: str = "default_dataset"):
    data = load_data(dataset_name=dataset_name)
    train_model(data=data, learning_rate=0.01)
```

You can then run the pipeline with specific parameters:

```python
training_pipeline(dataset_name="custom_dataset")
```

### Parameter Types

ZenML step parameters can be:

1. **Primitive types**: `int`, `float`, `str`, `bool`
2. **Container types**: `list`, `dict`, `tuple` (containing primitives)
3. **Custom types**: As long as they can be serialized to JSON using Pydantic

Parameters that cannot be serialized to JSON should be passed as artifacts rather than parameters.

### Default Values

You can provide default values for parameters:

```python
@step
def preprocess_data(normalize: bool = True, drop_nulls: bool = False):
    # Use parameters with defaults
    pass
```

## Parameter vs. Artifact Inputs

When calling a step in a pipeline, inputs can be:

### Parameters

Parameters are values provided explicitly when invoking a step:

```python
@pipeline
def my_pipeline():
    train_model(learning_rate=0.01)  # 0.01 is a parameter
```

Parameters must be JSON-serializable via Pydantic.

### Artifacts

Artifacts are outputs from other steps that are passed as inputs:

```python
@pipeline
def my_pipeline():
    data = load_data()
    train_model(data=data)  # data is an artifact
```

Artifacts can be any Python object that can be handled by a materializer.

## Configuring Parameters with YAML

You can specify parameters in YAML configuration files:

```yaml
# config.yaml
parameters:
  dataset_name: "production_dataset"
  
steps:
  train_model:
    parameters:
      learning_rate: 0.001
```

To use this configuration:

```python
training_pipeline.with_options(config_path="config.yaml")()
```

## Parameter Precedence

ZenML follows this order of precedence when resolving parameter values:

1. Values provided directly in code when calling the pipeline function
2. Values specified in step-level YAML configuration
3. Values specified in pipeline-level YAML configuration
4. Default values defined in the function signatures

## Dynamic Parameters

You can use dynamic expressions for parameters:

```python
from datetime import datetime

@pipeline
def my_pipeline():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    my_step(run_id=run_id)
```

## Environment Variables in Parameters

You can reference environment variables in YAML configuration:

```yaml
# config.yaml
parameters:
  api_key: ${API_KEY}
```

This will use the value of the `API_KEY` environment variable at runtime.

## Passing Parameters Between Steps

You can pass parameters between steps in several ways:

### Via Artifacts

```python
@step
def generate_params() -> dict:
    return {"learning_rate": 0.01, "epochs": 10}

@step
def train_model(params: dict):
    learning_rate = params["learning_rate"]
    epochs = params["epochs"]
    # Use parameters
```

### Via Pipeline Parameters

```python
@pipeline
def training_pipeline(learning_rate: float):
    data = load_data()
    train_model(data=data, learning_rate=learning_rate)
```

## Accessing Run Parameters in Code

You can access the parameters of the current pipeline run using the step context:

```python
from zenml import step, get_step_context

@step
def my_step():
    context = get_step_context()
    pipeline_params = context.pipeline_run.config.parameters
    print(f"Pipeline parameters: {pipeline_params}")
```

## Parameters and Caching

Parameters affect caching behavior:

- Steps are cached based on their inputs (both parameters and artifacts)
- If any parameter value changes, the step will be re-executed
- If all parameter values remain the same, the step may be cached (unless caching is disabled)

```python
@step(enable_cache=True)
def train_model(learning_rate: float):
    # This step will be re-executed if learning_rate changes
    pass
```

## Hyperparameter Tuning

You can use parameters for hyperparameter tuning:

```python
@step
def hyperparameter_tuning() -> dict:
    import optuna
    
    def objective(trial):
        learning_rate = trial.suggest_float('learning_rate', 0.0001, 0.1, log=True)
        n_estimators = trial.suggest_int('n_estimators', 50, 300)
        
        # Evaluate model with these parameters
        # ...
        
        return accuracy
    
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=100)
    
    return study.best_params

@pipeline
def tuning_pipeline():
    best_params = hyperparameter_tuning()
    train_model(params=best_params)
```

## Best Practices for Parameters

1. **Use descriptive parameter names** that clearly communicate their purpose
2. **Provide reasonable default values** whenever possible
3. **Document parameters** with docstrings explaining their purpose and valid values
4. **Use type annotations** to make parameter types explicit
5. **Separate configuration from code** using YAML configuration files
6. **Limit the number of parameters** to keep your code maintainable
7. **Group related parameters** in dictionaries or custom classes

## Conclusion

Execution parameters in ZenML provide a powerful mechanism for making your ML workflows flexible, reusable, and configurable. By properly parameterizing your steps and pipelines, you can create modular components that can be easily adapted to different scenarios without code changes.

See also:
- [Steps & Pipelines](./steps_and_pipelines.md) - Core building blocks
- [YAML Configuration](./yaml_configuration.md) - YAML configuration
- [Logging](./logging.md) - Logging configuration 