---
icon: chart-tree-map
---

# Model Management and Metrics

This section covers all aspects of managing models and tracking metrics in ZenML.

## Manual Model Logging

ZenML provides flexibility in model logging and registration through both CLI and programmatic methods, catering to different user preferences.

### CLI Method

To manually log a model using the CLI, you can use the `zenml model register` command. Here is a step-by-step guide:

```bash
zenml model register <model_name> --license=<license> --description=<description>
```

- `<model_name>`: The name of the model you want to register.
- `--license`: Specify the license for the model.
- `--description`: Provide a description of the model.

For more options, run `zenml model register --help` to see all available arguments, including the ability to add tags using the `--tag` option.

### Programmatic Method

To log a model programmatically, you can use the ZenML Python SDK. Here is an example of how to use the `Client().create_model()` method:

```python
from zenml.client import Client

Client().create_model(
    name="<model_name>",
    license="<license>",
    description="<description>",
    tags=["tag1", "tag2"]
)
```

- `name`: The name of the model.
- `license`: The license under which the model is registered.
- `description`: A brief description of the model.
- `tags`: Optional tags to categorize the model.

These methods allow you to leverage ZenML's Model Control Plane for effective model management.