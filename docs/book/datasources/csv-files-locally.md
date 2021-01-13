# CSV Datasource
Add a CSV file to your pipeline.
Details to be found at `zenml.core.datasources.csv_datasource`.
    
## Example
```python
from zenml.core.datasources.csv_datasource import CSVDatasource

# Add a datasource. This will automatically track and version it.
ds = CSVDatasource(name=f'Name', path='gs://path/to/csv')
```
