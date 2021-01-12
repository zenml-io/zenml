# Create your own datasource

When the standard datasources are not enough

If the standard datasources do not meet your needs, or your require custom logic while versioning the datasource, you can create custom datasources. 

All custom datasources must extend from the base class: `zenml.core.datasources.base_datasource.BaseDatasource.`

All datasources are have class variable called `DATA_STEP` . This variable defines a custom `BaseDataStep` class that binds the logic of the initialization of the datasource with the logic of actually reading and creating a version of the data itself. Therefore, every datasource has a data step. 

A `DATA_STEP` is like any other [Step](../steps/what-is-a-step.md), however every DATA\_STEP must inherit from the `BaseDataStep` class that defines a simple interface to create a Beam Pipeline that actually does the reading and versioning of the data. This interface is simply one function:

```python
def read_from_source():
    """
    Must return a Beam PTransform that defines reading of the into a 
    Pythonic dict representation.
    """
```

For reference of how all this works, check out the [CSV Datasource](https://github.com/maiot-io/zenml/blob/main/zenml/core/datasources/csv_datasource.py) and its relation with the [CSVDataStep](https://github.com/maiot-io/zenml/blob/main/zenml/core/steps/data/csv_data_step.py). Similar logic should be implemented when implementing custom datasources.

