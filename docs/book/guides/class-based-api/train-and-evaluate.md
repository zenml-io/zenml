---
description: Train some models.
---

If you want to see the code for this chapter of the guide, head over to the 
[GitHub](https://github.com/zenml-io/zenml/tree/main/examples/class_based_api/chapter_3.py).

Finally, we can train and evaluate our model. For this we decide to utilize the two base classes, the `BaseTrainerStep` 
and the `BaseEvaluator` step.

### Trainer

We can now start thinking about training our model. For this, we will be using the `BaseTrainerStep` to design a really 
simple step for training a parameterized fully connected network using 
[Tensorflow (Keras)](https://www.tensorflow.org/).

```python
from typing import List, Tuple

import pandas as pd
import tensorflow as tf

from zenml.steps.step_interfaces.base_trainer_step import (
    BaseTrainerConfig,
    BaseTrainerStep,
)
class TensorflowBinaryClassifierConfig(BaseTrainerConfig):
    target_column: str
    layers: List[int] = [256, 64, 1]
    input_shape: Tuple[int] = (8,)
    learning_rate: float = 0.001
    metrics: List[str] = ["accuracy"]
    epochs: int = 50
    batch_size: int = 8


class TensorflowBinaryClassifier(BaseTrainerStep):
    def entrypoint(
        self,
        train_dataset: pd.DataFrame,
        validation_dataset: pd.DataFrame,
        config: TensorflowBinaryClassifierConfig,
    ) -> tf.keras.Model:
        
        model = tf.keras.Sequential()
        model.add(tf.keras.layers.InputLayer(input_shape=config.input_shape))
        model.add(tf.keras.layers.Flatten())

        last_layer = config.layers.pop()
        for layer in config.layers:
            model.add(tf.keras.layers.Dense(layer, activation="relu"))
        model.add(tf.keras.layers.Dense(last_layer, activation="sigmoid"))

        model.compile(
            optimizer=tf.keras.optimizers.Adam(config.learning_rate),
            loss=tf.keras.losses.BinaryCrossentropy(),
            metrics=config.metrics,
        )

        train_target = train_dataset.pop(config.target_column)
        validation_target = validation_dataset.pop(config.target_column)
        model.fit(
            x=train_dataset,
            y=train_target,
            validation_data=(validation_dataset, validation_target),
            batch_size=config.batch_size,
            epochs=config.epochs,
        )
        model.summary()

        return model
```

### Evaluator

We can also add a simple evaluator using the `BaseEvaluatorStep`:

```python
from typing import Any, Dict, cast

import pandas as pd
import tensorflow as tf
from sklearn.metrics import classification_report

from zenml.steps.step_interfaces.base_evaluator_step import (
    BaseEvaluatorConfig,
    BaseEvaluatorStep,
)


class SklearnEvaluatorConfig(BaseEvaluatorConfig):
    label_class_column: str


class SklearnEvaluator(BaseEvaluatorStep):
    def entrypoint( 
        self,
        dataset: pd.DataFrame,
        model: tf.keras.Model,
        config: SklearnEvaluatorConfig,
    ) -> Dict[str, Any]:
        
        labels = dataset.pop(config.label_class_column)

        predictions = model.predict(dataset)
        predicted_classes = [1 if v > 0.5 else 0 for v in predictions]

        report = classification_report(labels, predicted_classes, output_dict=True)

        return report
```

Important things to note:

* the trainer returns a `tf.keras.Model`, which ZenML takes care of storing in the artifact store. We will talk about 
how to 'take over' this storing via `Materializers` in a later [chapter](materialize-artifacts.md).

### Pipeline

The final pipeline called `TrainingPipeline` is actually a built-in pipeline in ZenML, and it looks like this:

```python
class TrainingPipeline(BasePipeline):
    """ The built-in ZenML training pipeline"""
    
    def connect(
        self,
        datasource: BaseDatasourceStep,
        splitter: BaseSplitStep,
        analyzer: BaseAnalyzerStep,
        preprocessor: BasePreprocessorStep,
        trainer: BaseTrainerStep,
        evaluator: BaseEvaluatorStep,
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

        # Training the model
        model = trainer(train_dataset=train_t, validation_dataset=validation_t)

        # Evaluating the trained model
        evaluator(model=model, dataset=test_t)
```

You can add your steps to it and run your pipeline as follows:

```python
# Create the pipeline and run it
import os

pipeline_instance = TrainingPipeline(
    datasource=PandasDatasource(PandasDatasourceConfig(path=os.getenv("data"))),
    splitter=SklearnSplitter(SklearnSplitterConfig(ratios={"train": 0.7, "test": 0.15, "validation": 0.15})),
    analyzer=PandasAnalyzer(PandasAnalyzerConfig(percentiles=[0.2, 0.4, 0.6, 0.8, 1.0])),
    preprocessor=SklearnStandardScaler(SklearnStandardScalerConfig(ignore_columns=["has_diabetes"])),
    trainer=TensorflowBinaryClassifier(TensorflowBinaryClassifierConfig(target_column="has_diabetes")),
    evaluator=SklearnEvaluator(SklearnEvaluatorConfig(label_class_column="has_diabetes"))
)

pipeline_instance.run()
```

Beautiful, now the pipeline is truly doing something. Let's run it!

### Run

You can run this as follows:

```python
python chapter_3.py
```

The output will look as follows (note: this is filtered to highlight the most important logs)

```bash
Creating pipeline: TrainingPipeline
Cache enabled for pipeline `TrainingPipeline`
Using orchestrator `local_orchestrator` for pipeline `TrainingPipeline`. Running pipeline..
Step `PandasDatasource` has started.
Step `PandasDatasource` has finished in 0.017s.
Step `SklearnSplitter` has started.
Step `SklearnSplitter` has finished in 0.013s.
Step `PandasAnalyzer` has started.
Step `PandasAnalyzer` has finished in 0.013s.
Step `SklearnStandardScaler` has started.
Step `SklearnStandardScaler` has finished in 0.021s.
Step `TensorflowBinaryClassifier` has started.
67/67 [==============================] - 0s 2ms/step - loss: 0.5448 - accuracy: 0.7444 - val_loss: 0.4539 - val_accuracy: 0.7500
Model: "sequential"
_________________________________________________________________
Layer (type)                 Output Shape              Param #   
=================================================================
flatten (Flatten)            (None, 8)                 0         
_________________________________________________________________
dense (Dense)                (None, 256)               2304      
_________________________________________________________________
dense_1 (Dense)              (None, 64)                16448     
_________________________________________________________________
dense_2 (Dense)              (None, 1)                 65        
=================================================================
Total params: 18,817
Trainable params: 18,817
Non-trainable params: 0
_________________________________________________________________
Step `TensorflowBinaryClassifier` has finished in 1.232s.
Step `SklearnEvaluator` has started.
Step `SklearnEvaluator` has finished in 0.289s.
```

### Inspect

If you add the following code to fetch the pipeline:

```python
from zenml.repository import Repository

repo = Repository()
p = repo.get_pipeline(pipeline_name="mnist_pipeline")
runs = p.runs
print(f"Pipeline `mnist_pipeline` has {len(runs)} run(s)")
run = runs[-1]
print(f"The run you just made has {len(run.steps)} steps.")
step = run.get_step('evaluator')
print(
    f"The `tf_evaluator step` returned an accuracy: {step.output.read()}"
)
```

You get the following output:

```bash
Pipeline `TrainingPipeline` has 1 run(s)
The run you just made has 6 step(s).
```
