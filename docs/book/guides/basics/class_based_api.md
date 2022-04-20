---
description: Create your first step.
---

If you want to see the code for this chapter of the guide, head over to the [GitHub](https://github.com/zenml-io/zenml/tree/main/examples/class_based_api/chapter_1.py).

# Create an importer step to load data

The first thing to do is to load our data. We create a step that can load data from an external source (in this case 
a csv file representing the [Pima Indians Diabetes Database](https://www.kaggle.com/uciml/pima-indians-diabetes-database). 
This can be done by inheriting from the `BaseDatasourceStep` definition and overwriting the entrypoint function.

### Datasource

```python
from typing import List, Optional, Union

import pandas as pd

from zenml.steps.step_interfaces.base_datasource_step import (
    BaseDatasourceConfig,
    BaseDatasourceStep,
)

class PandasDatasourceConfig(BaseDatasourceConfig):
    path: str
    sep: str = ","
    header: Union[int, List[int], str] = "infer"
    names: Optional[List[str]] = None
    index_col: Optional[Union[int, str, List[Union[int, str]], bool]] = None


class PandasDatasource(BaseDatasourceStep):
    def entrypoint(
        self,
        config: PandasDatasourceConfig,
    ) -> pd.DataFrame:
        return pd.read_csv(
            filepath_or_buffer=config.path,
            sep=config.sep,
            header=config.header,
            names=config.names,
            index_col=config.index_col,
        )
```

Importing: things to note:

- The annotations in the signature of the entrypoint method of the `BaseDatasourceStep` is being overwritten with the 
actual data types. This is a necessary step for the step to work.
- The step is using a specific config object designed with this step in mind.

### Pipeline

Now we can go ahead and create a pipeline by inheriting from the `BasePipeline` and add a single step to ingest from our
datasource:

```python
import os

from zenml.pipelines import BasePipeline
from zenml.steps import step_interfaces


class Chapter1Pipeline(BasePipeline):
    """Class for Chapter 1 of the class-based API"""

    def connect(self, datasource: step_interfaces.BaseDatasourceStep,) -> None:
        datasource()

pipeline_instance = Chapter1Pipeline(
    datasource=PandasDatasource(PandasDatasourceConfig(path=os.getenv("data")))
)

pipeline_instance.run()
```

## Run

You can run this as follows:

```python
python chapter_1.py
```

The output will look as follows (note: this is filtered to highlight the most important logs)

```bash
Creating pipeline: Chapter1Pipeline
Cache enabled for pipeline `Chapter1Pipeline`
Using orchestrator `local_orchestrator` for pipeline `Chapter1Pipeline`. Running pipeline..
Step `PandasDatasource` has started.
Step `PandasDatasource` has finished in 0.016s.
```

## Inspect

You can add the following code to fetch the pipeline:

```python
from zenml.repository import Repository

repo = Repository()
p = repo.get_pipeline(pipeline_name="Chapter1Pipeline")
runs = p.runs
print(f"Pipeline `Chapter1Pipeline` has {len(runs)} run(s)")
run = runs[-1]
print(f"The run you just made has {len(run.steps)} step(s).")
step = run.get_step("datasource")
print(f"That step has {len(step.outputs)} output artifacts.")
```

You will get the following output:

```bash
Pipeline `Chapter1Pipeline` has 3 run(s)
The run you just made has 1 step(s).
That step has 1 output artifacts.
```