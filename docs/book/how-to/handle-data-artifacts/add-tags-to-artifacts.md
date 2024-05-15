---
description: >-
  Use tags to attach meaningful information to your artifacts to help you keep
  track and filter.
---

# Add tags to artifacts

```python
    from typing_extensions import Annotated
    from zenml import step

    @step
    def my_step() -> Annotated[
        int, ArtifactConfig(
            name="my_artifact",  # override the default artifact name
            tags=["tag1", "tag2"],  # set custom tags
        )
    ]:
        ...
        return 1
```
