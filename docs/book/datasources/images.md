# Images

For image training pipelines in fields like Computer Vision.

Please refer to docstring at `ImageDatasource` until this documentation is completed.

## Example

```python
from zenml.datasources import ImageDatasource

ImageDatasource(name='name', base_path='/path/to/images')
```

An actual real-world use of this datasource can be found in [tutorials/style-transfer-using-cyclegan](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/datasources/datasources/tutorials/style-transfer-using-a-cyclegan.md). The example will walk you through a turn-by-turn application, but will be synonymous for other usecases, too.

