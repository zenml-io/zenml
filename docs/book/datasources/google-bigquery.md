# Google Bigquery

Connect public and private Google BigQuery tables.

Please refer to docstring at `BigQueryDatasource` for details.

## Example

```python
from zenml.datasources import BigQueryDatasource

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

If you would like ZenMl to support more data types, then ping us on our [Slack](https://zenml.io/slack-invite) or [create an issue on GitHub](https://https://github.com/maiot-io/zenml) so that we know about it!

