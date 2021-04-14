# Registering a new datasource

## Overview: `BaseDatasource`

```python
class BaseDatasource:

    @abstractmethod
    def read_from_source(self):
        ...
```

### read\_from\_source

```python
def read_from_source(element, n) -> int:
```

## A quick example: the built-in `CSVDataSource`

{% hint style="info" %}
The following is an overview of the complete step. You can find the full code right [here](https://github.com/maiot-io/zenml/blob/main/zenml/steps/split/base_split_step.py).
{% endhint %}

```python
@beam.ptransform_fn
@beam.typehints.with_input_types(beam.Pipeline)
@beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
def read_files_from_disk(pipeline: beam.Pipeline,
                         base_path: Text) -> beam.pvalue.PCollection:

    wildcard_qualifier = "*"
    file_pattern = os.path.join(base_path, wildcard_qualifier)

    if path_utils.is_dir(base_path):
        csv_files = path_utils.list_dir(base_path)
        if not csv_files:
            raise RuntimeError(
                'Split pattern {} does not match any files.'.format(
                    file_pattern))
    else:
        if path_utils.file_exists(base_path):
            csv_files = [base_path]
        else:
            raise RuntimeError(f'{base_path} does not exist.')

    # weed out bad file exts with this logic
    allowed_file_exts = [".csv", ".txt"]  # ".dat"
    csv_files = [uri for uri in csv_files if os.path.splitext(uri)[1]
                 in allowed_file_exts]

    logger.info(f'Matched {len(csv_files)}: {csv_files}')

    # Always use header from file
    logger.info(f'Using header from file: {csv_files[0]}.')
    column_names = path_utils.load_csv_header(csv_files[0])
    logger.info(f'Header: {column_names}.')

    parsed_csv_lines = (
            pipeline
            | 'ReadFromText' >> beam.io.ReadFromText(file_pattern=base_path,
                                                     skip_header_lines=1)
            | 'ParseCSVLine' >> beam.ParDo(csv_decoder.ParseCSVLine(
        delimiter=','))
            | 'ExtractParsedCSVLines' >> beam.Map(
        lambda x: dict(zip(column_names, x[0]))))

    return parsed_csv_lines


class CSVDataStep(BaseDataStep):
    def read_from_source(self):
        return read_files_from_disk(self.path)
```

We can now go ahead and use this step in our pipeline:

```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.split import RandomSplit

training_pipeline = TrainingPipeline()

...

ds = CSVDatasource(name='Pima Indians Diabetes',
                   path='gs://zenml_quickstart/diabetes.csv')

training_pipeline.add_datasource(ds)

...
```

{% hint style="warning" %}
**An important note here**: As you see from the code blocks that you see above, any input given to the constructor of a datasource will translate into an instance variable. So, when you want to use it you can use **`self`**, as we did with **`self.path`**.
{% endhint %}

## What's next?

* 
