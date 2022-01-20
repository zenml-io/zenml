---
description: Split and preprocess your dataset
---

If you want to see the code for this chapter of the guide, head over to the [GitHub](https://github.com/zenml-io/zenml/tree/main/examples/class_based_api/chapter_2.py).

# Split, analyze and preprocess your dataset

Now before writing any trainers, we can actually split our dataset into train, test and validation splits and analyze 
the train split and preprocess our splits accordingly to make sure we get better results. To do this let's add three 
more steps and make the pipeline a bit more complex.

### Splitter

First, we can inherit from the `BaseSplitStep` which takes a single data artifact as input and splits it into 
three different output data artifacts for each split based on a given configuration:

```python
from typing import Dict

import pandas as pd
from sklearn.model_selection import train_test_split

from zenml.steps.step_interfaces.base_split_step import (
    BaseSplitStep,
    BaseSplitStepConfig,
)
from zenml.steps import Output


class SklearnSplitterConfig(BaseSplitStepConfig):
    ratios: Dict[str, float]
    
class SklearnSplitter(BaseSplitStep):
    def entrypoint(self,
                   dataset: pd.DataFrame,
                   config: SklearnSplitterConfig
                   ) -> Output(train=pd.DataFrame, 
                               test=pd.DataFrame, 
                               validation=pd.DataFrame):
        
        train_dataset, test_dataset = train_test_split(dataset, 
                                                       test_size=config.ratios["test"])

        test_size = config.ratios["validation"] / (config.ratios["validation"] + config.ratios["train"])
        train_dataset, val_dataset = train_test_split(train_dataset,
                                                      test_size=test_size)

        return train_dataset, test_dataset, val_dataset

```

### Analyzer
Next, we can think of a way to analyze the dataset to generate statistics and schema. For this purpose, we will inherit 
from the `BaseAnalyzerStep` and overwrite the entrypoint method:

```python
from typing import Any, List, Optional, Type, Union

import pandas as pd

from zenml.artifacts import SchemaArtifact, StatisticsArtifact
from zenml.steps import Output
from zenml.steps.step_interfaces.base_analyzer_step import (
    BaseAnalyzerConfig,
    BaseAnalyzerStep,
)


class PandasAnalyzerConfig(BaseAnalyzerConfig):
    percentiles: List[float] = [0.25, 0.5, 0.75]
    include: Optional[Union[str, List[Type[Any]]]] = None
    exclude: Optional[Union[str, List[Type[Any]]]] = None


class PandasAnalyzer(BaseAnalyzerStep):
    OUTPUT_SPEC = {"statistics": StatisticsArtifact, "schema": SchemaArtifact}

    def entrypoint(self,
                   dataset: pd.DataFrame,
                   config: PandasAnalyzerConfig,
                   ) -> Output(statistics=pd.DataFrame, 
                               schema=pd.DataFrame):
        
        statistics = dataset.describe(
            percentiles=config.percentiles,
            include=config.include,
            exclude=config.exclude,
        ).T
        schema = dataset.dtypes.to_frame().T.astype(str)
        return statistics, schema
```

### Preprocessor

Finally, we can write a step which would preprocess all the splits based on the statistics extracted from the train 
split. Let's use the `BasePreprocessorStep` to achieve that:

```python
from typing import List

import pandas as pd
from sklearn.preprocessing import StandardScaler

from zenml.steps import Output
from zenml.steps.step_interfaces.base_preprocessor_step import (
    BasePreprocessorConfig,
    BasePreprocessorStep,
)

class SklearnStandardScalerConfig(BasePreprocessorConfig):
    ignore_columns: List[str] = []
    exclude_columns: List[str] = []


class SklearnStandardScaler(BasePreprocessorStep):
    def entrypoint(self,
                   train_dataset: pd.DataFrame,
                   test_dataset: pd.DataFrame,
                   validation_dataset: pd.DataFrame,
                   statistics: pd.DataFrame,
                   schema: pd.DataFrame,
                   config: SklearnStandardScalerConfig,
                   ) -> Output(train_transformed=pd.DataFrame,
                               test_transformed=pd.DataFrame,
                               validation_transformed=pd.DataFrame):
        
        schema_dict = {k: v[0] for k, v in schema.to_dict().items()}

        feature_set = set(train_dataset.columns) - set(config.exclude_columns)
        for feature, feature_type in schema_dict.items():
            if feature_type != "int64" and feature_type != "float64":
                feature_set.remove(feature)

        transform_feature_set = feature_set - set(config.ignore_columns)
        
        scaler = StandardScaler()
        scaler.mean_ = statistics["mean"][transform_feature_set]
        scaler.scale_ = statistics["std"][transform_feature_set]

        train_dataset[transform_feature_set] = scaler.transform(train_dataset[transform_feature_set])
        test_dataset[transform_feature_set] = scaler.transform(test_dataset[transform_feature_set])
        validation_dataset[transform_feature_set] = scaler.transform(validation_dataset[transform_feature_set])

        return train_dataset, test_dataset, validation_dataset
```

There are some important things to note:

- As we are dealing with three splits, all of these steps have multiple outputs. That is why we need to use the 
`zenml.steps.Output` class to indicate the names of each output. If there was only one, we would not need to do this.
- In the `PandasAnalyzer`, the outputs are annotated as `pd.DataFrame`s and on default, `pd.DataFrames` are interpreted 
as `DataArtifact`s. As this is not the case within this step, we can overwrite the `OUTPUT_SPEC` of the class to point 
our step to the correct artifact types, namely the `StatisticsArtifact` and the `SchemaArtifact`.

### Pipeline

And that's it. Now, we can make these steps a part of our pipeline which would then look like this:

```python
from zenml.pipelines import BasePipeline
from zenml.steps import step_interfaces


class Chapter2Pipeline(BasePipeline):
    """Class for Chapter 2 of the class-based API"""
    
    def connect(self,
                datasource: step_interfaces.BaseDatasourceStep,
                splitter: step_interfaces.BaseSplitStep,
                analyzer: step_interfaces.BaseAnalyzerStep,
                preprocessor: step_interfaces.BasePreprocessorStep
                ) -> None:
        
        # Ingesting the datasource
        dataset = datasource()

        # Splitting the data
        train, test, validation = splitter(dataset=dataset)

        # Analyzing the train dataset
        statistics, schema = analyzer(dataset=train)  

        # Preprocessing the splits
        train_t, test_t, validation_t = preprocessor(  
            train_dataset=train,
            test_dataset=test,
            validation_dataset=validation,
            statistics=statistics,
            schema=schema,
        )


# Create the pipeline and run it
import os 

pipeline_instance = Chapter2Pipeline(
    datasource=PandasDatasource(PandasDatasourceConfig(path=os.getenv("data"))),
    splitter=SklearnSplitter(SklearnSplitterConfig(ratios={"train": 0.7, "test": 0.15, "validation": 0.15})),
    analyzer=PandasAnalyzer(PandasAnalyzerConfig(percentiles=[0.2, 0.4, 0.6, 0.8, 1.0])),
    preprocessor=SklearnStandardScaler(SklearnStandardScalerConfig(ignore_columns=["has_diabetes"]))
)

pipeline_instance.run()
```

## Run

You can run this as follows:

```python
python chapter_2.py
```

The output will look as follows (note: this is filtered to highlight the most important logs)

```bash
Creating pipeline: Chapter2Pipeline
Cache enabled for pipeline `Chapter2Pipeline`
Using orchestrator `local_orchestrator` for pipeline `Chapter2Pipeline`. Running pipeline..
Step `PandasDatasource` has started.
Step `PandasDatasource` has finished in 0.045s.
Step `SklearnSplitter` has started.
Step `SklearnSplitter` has finished in 0.432s.
Step `PandasAnalyzer` has started.
Step `PandasAnalyzer` has finished in 0.092s.
Step `SklearnStandardScaler` has started.
Step `SklearnStandardScaler` has finished in 0.151s.
```

## Inspect

You can add the following code to fetch the pipeline:

```python
from zenml.repository import Repository

repo = Repository()
p = repo.get_pipeline(pipeline_name="Chapter2Pipeline")
runs = p.runs
print(f"Pipeline `Chapter2Pipeline` has {len(runs)} run(s)")
run = runs[-1]
print(f"The run you just made has {len(run.steps)} step(s).")
```

You will get the following output:

```bash
Pipeline `Chapter2Pipeline` has 1 run(s)
The run you just made has 4 step(s).
```