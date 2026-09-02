---
description: Exporting logs to Elasticsearch or OpenSearch.
---

# Elasticsearch Log Store

The Elasticsearch Log Store is a log store flavor that writes logs to an [Elasticsearch](https://www.elastic.co/elasticsearch) cluster and queries them back, so pipeline logs are available both in the ZenML dashboard and in Kibana. It works against [OpenSearch](https://opensearch.org/) too, whose bulk and search APIs agree with the Elasticsearch ones on everything this log store uses.

### When would you want to use it?

The Elasticsearch Log Store is a good fit when:

- You already run an Elastic or OpenSearch cluster, self-hosted or as Elastic Cloud, AWS OpenSearch Service or a similar managed service
- You want pipeline logs in the same place as the rest of your application logs, searchable in Kibana
- You want long retention with index lifecycle management deciding what gets rolled over or deleted
- You want exact paging: unlike backends with only a timestamp to page by, a page here never overlaps another

### How it works

1. **Log capture**: All stdout, stderr, and Python logging output is captured during pipeline execution.

2. **Bulk export**: A custom `ElasticsearchLogExporter` writes log records to the cluster's `_bulk` API as newline-delimited JSON, one flat document per entry.

3. **Document shape**: Each document carries the message, the OTEL severity as both text and number, every ZenML attribute, and `@timestamp` for Kibana. Two extra fields exist purely so that reading is exact:

   | Field             | Purpose                                                                                          |
   |-------------------|--------------------------------------------------------------------------------------------------|
   | `timestamp_nanos` | The entry's timestamp in nanoseconds, avoiding the millisecond truncation of a mapped date field  |
   | `sequence_number` | A counter that orders entries written within the same nanosecond                                 |

4. **Log retrieval**: Reads go to `_search`, sorted on those two fields and paged with `search_after`, filtered to one log stream by its ZenML log ID.

### How to use it

#### A self-hosted cluster

```shell
zenml secret create elasticsearch \
    --password=<YOUR_PASSWORD>

zenml log-store register elasticsearch_logs \
    --flavor=elasticsearch \
    --url=http://elasticsearch.observability.svc.cluster.local:9200 \
    --username=elastic \
    --password='{{elasticsearch.password}}'

zenml stack register my_stack \
    -a my_artifact_store \
    -o default \
    -ls elasticsearch_logs \
    --set
```

#### Elastic Cloud, with an API key

```shell
zenml secret create elasticsearch \
    --api_key=<YOUR_ENCODED_API_KEY>

zenml log-store register elasticsearch_logs \
    --flavor=elasticsearch \
    --url=https://my-deployment.es.eu-central-1.aws.cloud.es.io:9243 \
    --api_key='{{elasticsearch.api_key}}' \
    --index=logs-zenml-production
```

The API key is the `encoded` value returned by Elasticsearch's create API key endpoint. It needs the `create_doc` privilege to write and `read` to fetch logs back.

### Configuration options

| Parameter               | Default          | Description                                                     |
|-------------------------|------------------|-----------------------------------------------------------------|
| `url`                   | _required_       | Base URL of the cluster, including scheme and port              |
| `index`                 | `"zenml-logs"`   | Index or data stream that log entries are written to and read from |
| `api_key`               | `None`           | Encoded API key, instead of basic authentication                |
| `username`              | `None`           | Username for basic authentication                               |
| `password`              | `None`           | Password for basic authentication                               |
| `service_name`          | `"zenml"`        | Service name attached to log records                            |
| `service_version`       | ZenML version    | Service version attached to log records                         |
| `max_export_batch_size` | `500`            | Number of entries per bulk request                              |
| `max_queue_size`        | `100000`         | Maximum queue size for the batch processor                      |
| `schedule_delay_millis` | `5000`           | Delay between batch exports (milliseconds)                      |
| `export_timeout_millis` | `15000`          | Timeout for each export batch (milliseconds)                    |

Whichever credentials are configured authenticate both writes and reads.

### The index

With automatic index creation enabled, which is the default, nothing needs to be set up in advance: the first batch of logs creates the index and dynamic mapping infers the fields. The two sort fields must stay numeric for paging to work, which dynamic mapping does on its own as long as the first document it sees for them is a number.

An explicit template is worth adding on a cluster where dynamic mapping is off, or where you want the fields to be mapped deliberately:

```shell
curl -X PUT "$ES_URL/_index_template/zenml-logs" -H 'Content-Type: application/json' -d '{
  "index_patterns": ["zenml-logs*"],
  "template": {
    "mappings": {
      "properties": {
        "timestamp_nanos": { "type": "long" },
        "sequence_number": { "type": "long" },
        "severity_number": { "type": "long" },
        "@timestamp": { "type": "date" },
        "message": { "type": "text" }
      }
    }
  }
}'
```

{% hint style="info" %}
Documents are written with the bulk `create` action and no document ID, which a data stream requires and a plain index accepts, so either kind of `index` target works.
{% endhint %}

### Viewing logs

#### In the ZenML dashboard

Logs are fetched from Elasticsearch when viewing step details. Each fetch is a single search. Omit `start` to read from the oldest end of the stream; pass `start=newest` for the last page. Entries on a page are always oldest to newest.

Because the nanosecond timestamp and the sequence number together are a total order over a log stream, paging uses Elasticsearch's `search_after` on those sort values — the cluster's own continuation, not a timestamp we invented. `before` and `after` both work. An empty page has no cursor.

Searching and filtering by level or time is done by the cluster. A search term becomes a `wildcard` on the message, so it matches a substring. A page holds at most 10000 entries, which is the default `index.max_result_window`.

#### In Kibana

Filter on the ZenML attributes, which are written as flat dotted fields:

```
zenml.pipeline.run.name : "<YOUR_RUN_NAME>"
```

```
zenml.pipeline.run.name : "<YOUR_RUN_NAME>" and zenml.step.run.name : "my_training_step"
```

### Troubleshooting

#### Logs not appearing in the cluster

1. Check that the credentials may write to the index; a bulk request that is rejected wholesale leaves nothing behind.
2. Check whether automatic index creation is disabled on the cluster, in which case the index or data stream has to exist before the first run.

#### Logs are in Kibana but not in the ZenML dashboard

1. Confirm that `timestamp_nanos` and `sequence_number` are mapped as numbers. A search cannot sort on a field mapped as text, and the index template above fixes the mapping deliberately.
2. Confirm that the credentials also grant read access to the index.

#### A step's logs are incomplete

The sequence number is counted per writing process, which is what orders entries sharing a nanosecond. Entries written by different processes into one log stream can therefore interleave differently to how they were emitted, but only within a single nanosecond.

For more information and a full list of configurable attributes, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-log_stores.html#zenml.log_stores.elasticsearch.elasticsearch_log_store).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
