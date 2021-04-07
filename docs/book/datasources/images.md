# Images

For image training pipelines in fields like Computer Vision.

Please refer to docstring at `ImageDatasource` until this documentation is completed.

## Example

```python
from zenml.datasources import ImageDatasource

ImageDatasource(name='name', base_path='/path/to/images')
```

An actual real-world use of this datasource can be found in [tutorials/style-transfer-using-cyclegan](https://github.com/maiot-io/zenml/tree/e395e52ab42a2bfcabffb907329bcae09674b40b/docs/book/datasources/tutorials/style-transfer-using-a-cyclegan.md). The example will walk you through a turn-by-turn application, but will be synonymous for other usecases, too.

