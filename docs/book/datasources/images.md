# Images

For image training pipelines in fields like Computer Vision.

Please refer to docstring at `ImageDatasource` until this documentation is completed.

## Example

```python
from zenml.datasources import ImageDatasource

ImageDatasource(name='name', base_path='/path/to/images')
```

An actual real-world use of this datasource can be found in [tutorials/style-transfer-using-cyclegan](https://github.com/maiot-io/zenml/tree/fc868ee5e5589ef0c09e30be9c2eab4897bfb140/docs/book/datasources/tutorials/style-transfer-using-a-cyclegan.md). The example will walk you through a turn-by-turn application, but will be synonymous for other usecases, too.

