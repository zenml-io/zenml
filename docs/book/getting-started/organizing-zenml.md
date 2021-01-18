# Organize ML code into ZenML
There is a good chance as a data scientist, you might already have code lying around that you would not like to re-write just 
to start using ZenML. The following is a step-by-step guide on how to refactor Jupyter notebook PoC model training code into a 
production-ready ZenML pipeline.

## Why should I do this?
Putting machine learning models in production is hard. Going from PoC quick scripting to actually having a model 
deployed and staying healthy is usually a long an arduous journey for any ML team. By putting your ML code in the form 
of ZenML pipelines, that journey is cut significantly shorter and is much easier.

## A familar story
As a data scientist the following (pseudo-)code might seem familiar:

```python
import libraries

# CELL 1: Read data
df = pd.read_*("/path/to/file.csv")
df.describe()

# INSERT HERE: a 100 more cells deleted and updated to explore data.

# CELL 2: Split
train, eval = split_data()

# INSERT HERE: Figure out if the split worked

# CELL 3: Preprocess
# nice, oh lets normalize
preprocess(train, eval)

# Exploring preprocessed data, same drill as before

# CELL 4: Train
model = create_model()
model = model.fit(train, eval)

# if youre lucky here, just look at some normal metrics like accuracy. otherwise:

# CELL 5: Evaluate
evaluate_model(train)

# INSERT HERE: do this a 1000 times

# CELL 6: Export (i.e. pickle it)
export_model(model)
```

## Step 1: Seperate the split
```python
from random import randint

from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.preprocesser.standard_preprocesser \
    .standard_preprocesser import StandardPreprocesser
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.trainer.feedforward_trainer.trainer import FeedForwardTrainer

training_pipeline = TrainingPipeline(
    name=f'Experiment {randint(0, 10000)}',
    enable_cache=True
)

# Add a datasource. This will automatically track and version it.
ds = CSVDatasource(name=f'My CSV Datasource {randint(0, 100000)}',
                   path='gs://zenml_quickstart/diabetes.csv')
training_pipeline.add_datasource(ds)

# Add a split
training_pipeline.add_split(RandomSplit(
    split_map={'eval': 0.3, 'train': 0.7}))

# Add a preprocessing unit
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
    epochs=3))

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))

# Run the pipeline locally
training_pipeline.run()

```


## What to do next?
Now what would be a great time to see what ZenML has to offer with standard powerful abstractions like [Pipelines](../pipelines/what-is-a-pipeline.md), 
[Steps](../steps/what-is-a-step.md), [Datasources](../datasources/what-is-a-datasource.md) and [Backends](../backends/what-is-a-backend.md).