# Tag your pipeline runs

You can specify tags for your pipeline runs in the following places

- in the configuration file:
```yaml
# config.yaml
tags:
  - tag_in_config_file
```

- in code on the `@pipeline` decorator or using the `with_options` method:
```python
@pipeline(tags=["tag_on_decorator"])
def my_pipeline():
  ...

my_pipeline = my_pipeline.with_options(tags=["tag_on_with_options"])
```

If you now run this pipeline, tags from all these places will be merged and applied to the pipeline run.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


