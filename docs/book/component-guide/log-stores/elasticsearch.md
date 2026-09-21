---
description: Storing and querying pipeline logs with Elasticsearch.
---

# Elasticsearch Log Store

The Elasticsearch Log Store writes pipeline logs to an Elasticsearch index or data stream and retrieves them for ZenML. Use it to keep pipeline logs in your existing Elastic deployment and explore them in Kibana.

The flavor is built into ZenML; no integration installation is required. The pipeline environment needs write access to the cluster, and the ZenML server needs read access for log retrieval.

### How to use it

#### Basic authentication

```shell
zenml secret create elasticsearch \
    --password=<YOUR_PASSWORD>

zenml log-store register elasticsearch_logs \
    --flavor=elasticsearch \
    --url=https://elasticsearch.example.com:9200 \
    --username=<YOUR_USERNAME> \
    --password='{{elasticsearch.password}}'

zenml stack register my_stack \
    -a my_artifact_store \
    -o default \
    --log_store elasticsearch_logs \
    --set
```

#### API key authentication

Use the encoded API key returned by Elasticsearch, and configure it instead of `username` and `password`:

```shell
zenml secret create elasticsearch \
    --api_key=<YOUR_ENCODED_API_KEY>

zenml log-store register elasticsearch_logs \
    --flavor=elasticsearch \
    --url=https://my-deployment.es.eu-central-1.aws.cloud.es.io:9243 \
    --api_key='{{elasticsearch.api_key}}' \
    --index=logs-zenml-production
```

The credentials need `create_doc` to write entries and `read` to retrieve them. Automatic index creation also requires an appropriate creation privilege, such as `auto_configure`. Otherwise, provision the target and its mappings before running a pipeline. See the [Elasticsearch bulk API prerequisites](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-bulk).

### Configuration options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `url` | _required_ | Base URL of the Elasticsearch cluster, including the scheme and port. |
| `index` | `"zenml-logs"` | Index or data stream used for writes and reads. |
| `api_key` | `None` | Encoded Elasticsearch API key. |
| `username` | `None` | Basic authentication username. Requires `password`. |
| `password` | `None` | Basic authentication password. |
| `service_name` | `"zenml"` | Service name attached to log records. |

The flavor also supports the [OpenTelemetry log store's export settings](otel.md#configuration-options), including batching, compression, and TLS certificates. ZenML derives the bulk ingestion endpoint from `url` and `index`. Authentication credentials are used for both writes and queries.

### Index mapping

ZenML writes each log record through Elasticsearch's bulk `create` action. Documents contain the message, severity, ZenML attributes, `@timestamp`, and the fields used to identify and order entries.

A new index with Elasticsearch's default dynamic mappings provides the required field types. If you manage mappings explicitly, preserve these fields:

| Field | Mapping | Purpose |
|-------|---------|---------|
| `timestamp_nanos` | `long` | Timestamp sorting and time filters. |
| `event_id.keyword` | `keyword` subfield of `event_id` | Unique tie-breaker for entries with the same timestamp. |
| `zenml.log.id.keyword` | `keyword` subfield of `zenml.log.id` | Exact log stream selection. |
| `severity_number` | Numeric | Minimum severity filters. |
| `message` | `text` | Message search. |
| `@timestamp` | `date` or `date_nanos` | Time field for Kibana and data streams. |

For example, the `event_id` mapping should include its keyword subfield:

```json
{
  "event_id": {
    "type": "text",
    "fields": {
      "keyword": { "type": "keyword" }
    }
  }
}
```

Use the same subfield structure for `zenml.log.id`. For a data stream, configure a matching data stream template before the first write.

### Viewing logs

Each fetch makes one Elasticsearch search request. It starts with the newest entries by default and returns a `before` cursor to continue towards older entries. Set `start="oldest"` to traverse towards newer entries using `after`. Entries within each page are chronological.

The default page size is 1000 and the maximum is 10,000, subject to `ZENML_LOGS_MAX_ENTRIES_PER_REQUEST`. Use a smaller `limit` if the index has a lower `index.max_result_window`.

Cursors retain Elasticsearch's native `search_after` values, the query filters, fixed time bounds, direction, and page size. Continue with only the returned cursor. To change the filters or direction, start a new read. Follow the cursor until it is absent; the final request may return an empty page.

If omitted, `since` starts at the log stream's creation time and `until` is fixed to the first request's current UTC time. Fixed time bounds do not freeze the index: newly indexed or changed documents within that window can affect later pages. See Elasticsearch's [pagination guidance](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/paginate-search-results).

Using the `log_store` and `logs` objects from the [Python SDK example](README.md#python-sdk):

```python
from zenml.models import LogsEntriesFilter

page = log_store.fetch(
    logs_model=logs,
    limit=100,
    filter_=LogsEntriesFilter(level="WARNING"),
)
while True:
    for entry in page.items:
        print(entry.message)
    if page.before is None:
        break
    page = log_store.fetch(logs_model=logs, before=page.before)
```

`level` is a minimum severity, and `since` and `until` are inclusive. `search` uses Elasticsearch's [`match_phrase` query](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-match-query-phrase) on the message field. Tokenization, case handling, and punctuation follow the index's analyzer; this is a phrase search rather than a literal substring match.

Each exported event has a persistent UUID used as its document ID and pagination tie-breaker. ZenML derives `LogEntry.id` from the index and document ID, so repeated reads of the same document return the same UUID.

#### In Kibana

Filter on the ZenML attributes:

```text
zenml.pipeline.run.name : "<YOUR_RUN_NAME>"
```

```text
zenml.pipeline.run.name : "<YOUR_RUN_NAME>" and zenml.step.run.name : "my_training_step"
```

### Troubleshooting

If logs do not appear, check write permissions, bulk export errors, and whether the target index or data stream exists. Elasticsearch makes writes searchable after an index refresh, so newly exported logs may take a short time to appear.

If logs appear in Kibana but not in ZenML, check read permissions and the mappings above. Existing indices with incompatible mappings need a new index or a reindexing step; changing the template only affects future indices.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
