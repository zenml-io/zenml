---
jupytext:
  cell_metadata_filter: '-all'
  formats: 'md:myst'
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.12
    jupytext_version: 1.9.1
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Designing your first training pipeline

When creating a new training pipeline, the first step is to create an instance of a `zenml.pipelines.TrainingPipeline`. While creating this instance, you can give it a name and use that name to reference the pipeline later.

```text
from zenml.pipelines import TrainingPipeline

training_pipeline = TrainingPipeline(name='QuickstartPipeline')
```

In a `TrainingPipeline`, there is a fixed set of steps representing the processes, which can be found in any machine learning workflow. These steps include:

1. **Split**: responsible for splitting your dataset into smaller datasets such as train, eval, etc.
2. **Transform**: responsible for the preprocessing of your data
3. **Train**: responsible for the model creation and training process
4. **Evaluate**: responsible for the evaluation of your results

### Creating a datasource

However, before we dive into the aforementioned steps, let's briefly talk about our dataset.

For this quickstart, we will be using the _Pima Indians Diabetes Dataset_ and on it, we will train a model which will aim to predict whether a person has diabetes based on diagnostic measures.

In order to be able to use this dataset \(which is currently in CSV format\) in your **ZenML** pipeline, we first need to create a `datasource`. **ZenML** has built-in support for various types of datasources and for this example you can use the `CSVDatasource`. All you need to provide is a `name` for the datasource and the `path` to the CSV file.In \[ \]:

```text
from zenml.datasources import CSVDatasource

ds = CSVDatasource(name='Pima Indians Diabetes Dataset', 
                   path='gs://zenml_quickstart/diabetes.csv')
```

Once you are through, you will have created a tracked and versioned datasource and you can use this datasource in any pipeline. Go ahead and add it to your pipeline.In \[ \]:

```text
training_pipeline.add_datasource(ds)
```

### Configuring the split

Now, let us get back to the **four** essential steps where the first step is the **Split**.

For the sake of simplicity in this tutorial, we will be using a completely random `70-30` split into a train and evaluation dataset.In \[ \]:

```text
from zenml.steps.split import RandomSplit

training_pipeline.add_split(RandomSplit(split_map={'train': 0.7, 
                                                   'eval': 0.3}))
```

Keep in mind, in a more complicated example, it might be necessary to apply a different splitting strategy. For these cases, you can use the other built-in split configuration **ZenML** offers or even implement your own custom logic into the split step.

### Handling data preprocessing

The next step is to configure the step **Transform**, the data preprocessing.

For this example, we will use the built-in `StandardPreprocesser`. It handles the feature selection and has sane defaults of preprocessing behaviour for each data type, such as stardardization for numerical features or vocabularization for non-numerical features.

In order to use it, you need to provide a list of feature names and a list of label names. Moreover, if you do not want it use the default transformation for a feature or you want to overwrite it with a different preprocessing method, this is also possible as we do in this example.In \[ \]:

```text
from zenml.steps.preprocesser import StandardPreprocesser

training_pipeline.add_preprocesser(
    StandardPreprocesser(
        features=['times_pregnant', 
                  'pgc', 
                  'dbp', 
                  'tst', 
                  'insulin', 
                  'bmi',
                  'pedigree', 
                  'age'],
        labels=['has_diabetes'],
        overwrite={'has_diabetes': {
            'transform': [{'method': 'no_transform', 
                           'parameters': {}}]}}))
```

Much like the splitting process, you might want to work on cases, where the capabilities of the `StandardPreprocesser` do not match your task at hand. In this case, you can create your own custom preprocessing step, but we will go into that topic in a different tutorial.

### Training your model

As the data is now ready, we can move onto the step **Train**, the model creation and training.

For this quickstart, we will be using the simple built-in `FeedForwardTrainer` step and as the name suggests, it represents a feedforward neural network, which is configurable through a set of variables.In \[ \]:

```text
from zenml.steps.trainer import TFFeedForwardTrainer

training_pipeline.add_trainer(TFFeedForwardTrainer(loss='binary_crossentropy',
                                                   last_activation='sigmoid',
                                                   output_units=1,
                                                   metrics=['accuracy'],
                                                   epochs=20))
```

Of course, not every single machine learning problem is solvable by a simple feedforward neural network and most of the time, they will require a model which is tailored to the corresponding problem. That is why we created an interface where the users can implement their own custom models and integrate it in a trainer step. However this approach is not within the scope of this tutorial and you can learn more about it in our docs and the upcoming tutorials.

### Evaluation of the results

The last step to configure in our pipeline is the **Evaluate**.

For this example, we will be using the built-in `TFMAEvaluator` which uses [Tensorflow Model Analysis](https://www.tensorflow.org/tfx/model_analysis/get_started) to compute metrics based on your results \(possibly within slices\).In \[ \]:

```text
from zenml.steps.evaluator import TFMAEvaluator

training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))
```

### Running your pipeline

Now that everything is set, go ahead and run the pipeline, thus your steps.In \[ \]:

```text
training_pipeline.run()
```

With the execution of the pipeline, you should see the logs informing you about each step along the way. In more detail, you should first see that your dataset will is ingested through the component _DataGen_ and then split by the component _SplitGen_. Afterwards data preprocessing will take place with the component _Transform_ and will lead to the main training component _Trainer_. Ultimately, the results will be evaluated by the component _Evaluator_.

### Post-training functionalities

Once the training pipeline is finished, you can check the outputs of your pipeline in different ways.

#### Dataset

As the data is now ingested, you can go ahead and take a peek into your dataset. You can achieve this by simply getting the datasources registered to your repository and calling the method `sample_data`.In \[ \]:

```text
from zenml.repo import Repository

repo = Repository.get_instance()
datasources = repo.get_datasources()

datasources[0].sample_data()
```

#### Statistics

Furthermore, you can check the statistics which are yielded by your datasource and split configuration through the method `view_statistics`. By using the `magic` flag, we can even achieve this right here in this notebook.In \[ \]:

```text
training_pipeline.view_statistics(magic=True)
```

#### Evaluate

On the other hand, if you want to evalaute the results of your training process you can use the `evaluate` method of your pipeline.

Much like the `view_statistics`, if you execute `evaluate` with the `magic` flag, it will help you continue in this notebook and generate two new cells, each set up with a different evaluation tool:

1. **Tensorboard** can help you to understand the behaviour of your model during the training session
2. **TFMA** or **tensorflow\_model\_analysis** can help you assess your already trained model based on given metrics and slices on the evaluation dataset

_Note_: if you want to see the sliced results, comment in the last line and adjust it according to the slicing column. In the end it should look like this:

```text
tfma.view.render_slicing_metrics(evaluation, slicing_column='has_diabetes')
```

In \[ \]:

```text
training_pipeline.evaluate(magic=True)
```

... and this it it for the quickstart. If you came here without a hiccup, you must have successly installed ZenML, set up a ZenML repo, registered a new datasource, configured a training pipeline, executed it locally and evaluated the results. And, this is just the tip of the iceberg on the capabilities of **ZenML**.

## What's next?



