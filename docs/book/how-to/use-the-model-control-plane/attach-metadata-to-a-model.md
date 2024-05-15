---
description: >-
  Attach any metadata as key-value pairs to your models for future reference and
  auditability.
---

# Attach metadata to a model

```python
from zenml.model.model import Model
from zenml import step, log_model_metadata

  
@step()
def model_trainer() -> Tuple[
    Annotated[RegressorMixin, "model"], Annotated[float, "r2_score"]
]:  
    ...
    
    log_model_metadata(
        metadata={
            "model_name": model_name,
            "dataset_name": dataset_name,
            "accuracy": accuracy
        }
    )
    
    ...
```
