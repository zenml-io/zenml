---
description: Use higher level pre-made pipelines to quickly create powerful ML workflows.
---

# Class-based API

The High Level or Class-based API documentation is being completed. It will look roughly like this:

```python
from zenml.pipelines import TrainingPipeline

pipeline = TrainingPipeline()
pipeline.add_trainer(TrainerStep())
pipeline.run()
```