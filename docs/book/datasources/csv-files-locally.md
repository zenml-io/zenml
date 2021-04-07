# CSV Datasource
Add a CSV file to your pipeline.  
The CSV path can be a local one, a path to a Google Cloud Storage or a AWS S3 bucket. 
    
## Example

```python
from zenml.datasources import CSVDatasource

# Add a datasource. This will automatically track and version it.
ds = CSVDatasource(name=f'Name', path='gs://path/to/csv')
```

As CSVs are frequently used you'll find our [quickstart](getting-started/quickstart.md) using the `CSVDatasource`.