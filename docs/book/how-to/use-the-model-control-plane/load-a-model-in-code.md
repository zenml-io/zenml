# Load a Model in code

```python
from zenml import step
from zenml.client import Client

@step
def model_evaluator_step()
    ...
    # Get staging model version 
    try:
        staging_zenml_model = Client().get_model_version(
            model_name_or_id="<INSERT_MODEL_NAME>",
            model_version_name_or_number_or_id=ModelStages.STAGING,
        )
    except KeyError:
        staging_zenml_model = None
    ...
```
