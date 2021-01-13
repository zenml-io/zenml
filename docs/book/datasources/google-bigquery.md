# Google BigQuery
Connect public and private Google BigQuery tables.

Please refer to docstring at `zenml.core.datasources.bq_datasource` for details.

## Example
```python
from zenml.core.datasources.bq_datasource import BigQueryDatasource

ds = BigQueryDatasource(
    name=f'Name',
    query_dataset='chicago_taxi_trips',
    query_table='taxi_trips',
    query_project='bigquery-public-data',
    dest_project='gcp-project',
    gcs_location='gs://path/to/dump/directory',
)
```



## Supported data types

| BigQuery Data Type | Supported |
| :--- | :---: |
| INTEGER | YES |
| FLOAT | YES |
| STRING | YES |
| TIMESTAMP | YES |
| BOOLEAN | YES |
| RECORD | NO |
| DATETIME | NO |
| ARRAY | NO |
| STRUCT | NO |
| BYTES | NO |
| GEOGRAPHY | NO |

We are working hard to bring the more supported data types to the Core Engine. Please give us feedback at `support@zenml.io` so that we can prioritize the most important ones quicker!

## 

