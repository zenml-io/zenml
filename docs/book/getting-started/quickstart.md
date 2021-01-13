# Quickstart
Get up and running in (almost) 3 steps.
Let’s get you started with a simple pipeline. Please make sure to also check out the [advanced concepts.](core-concepts.md) This quickstart uses some built-ins and a very simple model.

```{hint}
If you are here just to see the code, you can find it on [GitHub](https://github.com/maiot-io/zenml#quickstart).
```

## **For visual learners**

If you don't feel like reading right now, please watch this video for a visual explanation of the quickstart:

<iframe width="560" height="315" src="https://www.youtube.com/embed/Stg5rA_0oa8" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

### **Step 0: Installation**

ZenML is available for easy installation into your environment via PyPI:

```bash
pip install zenml
```

Alternatively, if you’re feeling brave, feel free to install the bleeding edge: **NOTE:** Do so on your own risk, no guarantees given!

```bash
pip install git+https://github.com/maiot-io/zenml.git@main --upgrade
```

### Step 1: Initialize a ZenML repo from within a git repo

```python
zenml init
```

### **Step 2: Assemble, run and evaluate your pipeline locally**

```python
from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.preprocesser.standard_preprocesser.standard_preprocesser import StandardPreprocesser
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.trainer.feedforward_trainer import FeedForwardTrainer

training_pipeline = TrainingPipeline(name='Quickstart')

# Add a datasource. This will automatically track and version it.
ds = CSVDatasource(name='Pima Indians Diabetes Dataset', 
                   path='gs://zenml_quickstart/diabetes.csv')
training_pipeline.add_datasource(ds)

# Add a random 70/30 train-eval split
training_pipeline.add_split(RandomSplit(split_map={'train': 0.7, 'eval': 0.3}))

# StandardPreprocesser() has sane defaults for normal preprocessing methods
training_pipeline.add_preprocesser(
    StandardPreprocesser(
        features=['times_pregnant', 'pgc', 'dbp', 'tst', 'insulin', 'bmi',
                  'pedigree', 'age'],
        labels=['has_diabetes'],
        overwrite={'has_diabetes': {
            'transform': [{'method': 'no_transform', 'parameters': {}}]}}
    ))

# Add a trainer
training_pipeline.add_trainer(FeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=20))


# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))

# Run the pipeline locally
training_pipeline.run()
```

### **Step 3: Leverage powerful integrations**

```python
# See schema of data
training_pipeline.view_schema()

# See statistics of train and eval
training_pipeline.view_statistics()

# Creates a notebook for evaluation
training_pipeline.evaluate()
```

Of course, each of these steps can be [extended quite easily](../steps/what-is-a-step.md) to accommodate more complex scenarios and use-cases. There is a steadily-growing number of integrations available, for example, Google Dataflow for [distributed preprocessing](https://github.com/maiot-io/zenml/tree/staging#...) or Google Cloud AI Platform as a [training](https://github.com/maiot-io/zenml/tree/staging#...)  backend.

