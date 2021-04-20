---
description: Easily connect datasources.
---

# Registering a new datasource

## Overview: `BaseDatasource`

**ZenML** automatically tracks \(**metadata store**\) and versions \(**artifact store**\) all data that flows through its pipelines. The  `BaseDatasource` interface defines how to create a datasource. In the definition of this interface, there is only one method called `process`.

```python
class BaseDatasource:

    @abstractmethod
    def process(self):
        ...
```

### process

The goal of the `process` is to read from the source of the data and write to the `output_path` the data in the form of [TFRecords](https://www.tensorflow.org/tutorials/load_data/tfrecord), which is an efficient, standardized format to store ML data that **ZenML** utilizes internally. These TFRecords in turn are read downstream in **pipelines.** A schema and statistics are also automatically generated for each datasource run.

```python
def process(output_path, make_beam_pipeline):
```

## A quick example: the built-in `CSVDataSource`

{% hint style="info" %}
The following is an overview of the complete step. You can find the full code right [here](https://github.com/maiot-io/zenml/blob/main/zenml/datasources/csv_datasource.py).
{% endhint %}

```python
class CSVDatasource(BaseDatasource):

    def __init__(
            self,
            name: Text,
            path: Text,
            schema: Dict = None,
            **kwargs):
        self.path = path
        self.schema = schema
        super().__init__(name, path=path, schema=schema, **kwargs)

    def process(self, output_path: Text, make_beam_pipeline: Callable = None):
        wildcard_qualifier = "*"
        file_pattern = os.path.join(self.path, wildcard_qualifier)

        if path_utils.is_dir(self.path):
            csv_files = path_utils.list_dir(self.path)
            if not csv_files:
                raise RuntimeError(
                    'Split pattern {} does not match any files.'.format(
                        file_pattern))
        else:
            if path_utils.file_exists(self.path):
                csv_files = [self.path]
            else:
                raise RuntimeError(f'{self.path} does not exist.')

        # weed out bad file exts with this logic
        allowed_file_exts = [".csv", ".txt"]  # ".dat"
        csv_files = [uri for uri in csv_files if os.path.splitext(uri)[1]
                     in allowed_file_exts]

        logger.info(f'Matched {len(csv_files)}: {csv_files}')

        # Always use header from file
        logger.info(f'Using header from file: {csv_files[0]}.')
        column_names = path_utils.load_csv_header(csv_files[0])
        logger.info(f'Header: {column_names}.')

        with make_beam_pipeline() as p:
            p | 'ReadFromText' >> beam.io.ReadFromText(
                file_pattern=self.path,
                skip_header_lines=1) \
            | 'ParseCSVLine' >> beam.ParDo(csv_decoder.ParseCSVLine(
                delimiter=',')) \
            | 'ExtractParsedCSVLines' >> beam.Map(
                lambda x: dict(zip(column_names, x[0]))) \
            | WriteToTFRecord(self.schema, output_path)

```

{% hint style="warning" %}
**An important note here**: As you see from the code blocks that you see above, any input given to the constructor of a datasource will translate into an instance variable. So, when you want to use it you can use **`self`**, as we did with **`self.path`**.
{% endhint %}

And here is how you would use it:

```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.split import RandomSplit

training_pipeline = TrainingPipeline()

...

ds = CSVDatasource(name='Pima Indians Diabetes',
                   path='gs://zenml_quickstart/diabetes.csv')

# to create a version
ds.commit()

# if ds.commit() not called, it is later called internally.
training_pipeline.add_datasource(ds)

...
```

Each time the user calls `ds.commit()` a new version \(snapshot\) of the data is created via a **data pipeline** defined through the `process` method.

