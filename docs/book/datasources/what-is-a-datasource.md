# What is a datasource

Datasources come in all shapes and sizes. Even though most of the small projects use a relatively small and rarely changing \(i.e., an almost static\) datasource, as you start to work on bigger and bigger projects, there is a good chance that you will have to handle a datasource that grows in size over time and might change its nature dynamically as well.

That is exactly the point where ZenML comes into play with the concept of versioning datasources. When you create a datasource and add to a pipeline, ZenML creates a snapshot of your datasource and stores it. This way, you can collaborate with your teammates on the same version of your datasource and you end up with traceable and repeatable experiments even on dynamically changing datasources.

## Repository functionalities

You can get all your datasources using the [Repository](../repository/what-is-a-repository.md) class:

```python
from zenml.repo import Repository

repo: Repository = Repository.get_instance()

datasources = repo.get_datasources()

# use datasources
datasource = datasources[0]

# prints total number of datapoints in datasource
print(datasource.get_datapoints())

# samples data from datasource as a pandas DataFrame.
print(datasource.sample_data())
```

## Create your own datasource

```text
Before creating your own datasource, please make sure to follow the [general rules](../getting-started/creating-custom-logic.md)
for extending any first-class ZenML component.
```

If the standard datasources do not meet your needs, or your require custom logic while versioning the datasource, you can create custom datasources.

All custom datasources must extend from the base class: `zenml.core.datasources.base_datasource.BaseDatasource.`

All datasources are have class variable called `DATA_STEP` . This variable defines a custom `BaseDataStep` class that binds the logic of the initialization of the datasource with the logic of actually reading and creating a version of the data itself. Therefore, every datasource has a data step.

A `DATA_STEP` is like any other [Step](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/datasources/steps/what-is-a-step.md), however every DATA\_STEP must inherit from the `BaseDataStep` class that defines a simple interface to create a Beam Pipeline that actually does the reading and versioning of the data. This interface is simply one function:

```python
def read_from_source():
    """
    Must return a Beam PTransform that defines reading of the into a 
    Pythonic dict representation.
    """
```

For reference of how all this works, check out the [CSV Datasource](https://github.com/maiot-io/zenml/blob/main/zenml/core/datasources/csv_datasource.py) and its relation with the [CSVDataStep](https://github.com/maiot-io/zenml/blob/main/zenml/core/steps/data/csv_data_step.py). Similar logic should be implemented when implementing custom datasources.

