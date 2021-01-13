# What is a datasource?

Every pipeline has a datasource

Datasources come in all shapes and sizes. Even though most of the small projects use a relatively small and rarely changing \(i.e., an almost static\) datasource, as you start to work on bigger and bigger projects, there is a good chance that you will have to handle a datasource that grows in size over time and might change its nature dynamically as well.

That is exactly the point where ZenML comes into play with the concept of versioning datasources. When you create a datasource and add to a pipeline, ZenML creates a snapshot of your datasource and stores it. This way, you can collaborate with your teammates on the same version of your datasource and you end up with traceable and repeatable experiments even on dynamically changing datasources.

You can get all your datasources using the [Repository](../repository/repository-singleton.md) class:

```python
from zenml.core.repo.repo import Repository

repo: Repository = Repository.get_instance()
# repo.compare_pipelines()
datasources = repo.get_datasources()

print(datasources)

datasource = datasources[0]

# prints total number of datapoints in datasource
print(datasource.get_datapoints())

# samples data from datasource as a pandas DataFrame.
print(datasource.sample_data())
```

