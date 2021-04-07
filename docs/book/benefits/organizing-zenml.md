# Organizing ML Code with ZenML

There is a good chance as a data scientist, you might already have code lying around that you would not like to re-write just to start using ZenML. The following is a step-by-step guide on how to refactor Jupyter notebook PoC model training code into a production-ready ZenML pipeline.

## Why should I do this?

Putting machine learning models in production is hard. Going from PoC quick scripting to actually having a model deployed and staying healthy is usually a long an arduous journey for any ML team. By putting your ML code in the form of ZenML pipelines, that journey is cut significantly shorter and is much easier.

## A familar story

As a data scientist the following \(pseudo-\)code might seem familiar:

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

The above, while being handy for quick results, does not really translate well in production.

## Organize legacy code into production pipelines in seven easy steps

ZenML allows you to take the above code, and organize it into [ZenML pipelines](../pipelines/what-is-a-pipeline.md). Heres how:

### Step 0: Create the pipeline

```python
from zenml.pipelines import TrainingPipeline

training_pipeline = TrainingPipeline()
```

### Step 1: Configure the datasource

```python
from zenml.datasources import CSVDatasource

ds = CSVDatasource(name='A proper name', path='/path/to/file.csv')
training_pipeline.add_datasource(ds)
```

### Step 2: Separate the split

```python
from zenml.steps.split import RandomSplit

training_pipeline.add_split(RandomSplit(
    split_map={'train': 0.7, 'eval': 0.3}))
```

### Step 3: Define the preprocessing

```python
from zenml.steps.preprocesser import StandardPreprocesser

training_pipeline.add_preprocesser(
    StandardPreprocesser(
        features=[...],
        labels=[...],
    ))
```

### Step 4: Write the trainer

```python
from zenml.steps.trainer import TFFeedForwardTrainer

training_pipeline.add_trainer(TFFeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=20))
```

### Step 5: Set the evaluation

```python
from zenml.steps.evaluator import TFMAEvaluator

training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))
```

### Step 6: Select the deployment

```python
from zenml.steps.deployer import GCAIPDeployer

training_pipeline.add_deployment(
    GCAIPDeployer(
        project_id='project',
        model_name='my_trained_awesome_model',
    )
)
```

### Step 7: Run the pipeline!

```python
training_pipeline.run()
```

## So what just happened?

By refactoring all parts of the afore-mentioned Jupyter notebook into neat little steps in a ZenML pipeline, you have gone from PoC machine learning to production-ready in minutes! Not only is the code, data, configuraiton and environment versioned, tracked, and catalogued for you, you can now reproduce your results any time, anywhere! Feel free to run the same code on powerful machines on the cloud, distribute the preprocessing step, and deploy the model straight to a cluster! This all comes for free with ZenML.

## What to do next?

Now what would be a great time to see what ZenML has to offer with standard powerful abstractions like [Pipelines](../pipelines/what-is-a-pipeline.md), [Steps](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/benefits/steps/what-is-a-step.md), [Datasources](../datasources/what-is-a-datasource.md) and [Backends](../backends/what-is-a-backend.md).

