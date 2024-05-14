# Load a Model within a Step

```python
def model_evaluator_step()
    ...
    # Get staging model version 
    try:
        staging_zenml_model = zenml_client.get_model_version(
            model_name_or_id="<INSERT_MODEL_NAME>",
            model_version_name_or_number_or_id=ModelStages("staging"),
        )
    except KeyError:
        staging_zenml_model = None
    ...
```
