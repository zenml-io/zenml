---
description: Tracking your metadata.
---

# Special Metadata Types

ZenML supports several special metadata types to capture specific kinds of 
information. Here are examples of how to use the special types `Uri`, `Path`, 
`DType`, and `StorageSize`:

```python
from zenml import log_metadata
from zenml.metadata.metadata_types import StorageSize, DType, Uri, Path

log_metadata(
    metadata={
        "dataset_source": Uri("gs://my-bucket/datasets/source.csv"),
        "preprocessing_script": Path("/scripts/preprocess.py"),
        "column_types": {
            "age": DType("int"),
            "income": DType("float"),
            "score": DType("int")
        },
        "processed_data_size": StorageSize(2500000)
    },
)
```

In this example:

* `Uri` is used to indicate a dataset source URI.
* `Path` is used to specify the filesystem path to a preprocessing script.
* `DType` is used to describe the data types of specific columns.
* `StorageSize` is used to indicate the size of the processed data in bytes.

These special types help standardize the format of metadata and ensure that it 
is logged in a consistent and interpretable manner.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
