---
description: Use higher level pre-made pipelines to quickly create powerful ML workflows.
---

# High Level API

The High Level API documentation is being completed. It will look roughly like this:

```python
from zenml.pipelines import TrainingPipeline

pipeline = TrainingPipeline()
pipeline.add_trainer(TrainerStep())
pipeline.run()
```