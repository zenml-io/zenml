---
description: Accessing meta information during pipeline composition.
---

# Fetch metadata during pipeline composition

### Pipeline configuration using the `PipelineContext`

To find information about the pipeline configuration during pipeline composition, you
can use the `zenml.get_pipeline_context()` function to access the `PipelineContext` of
your pipeline:

```python
from zenml import get_pipeline_context, pipeline

...

@pipeline(extra={"complex_parameter": ("sklearn.tree","DecisionTreeClassifier")})
def my_pipeline():
    context = get_pipeline_context()

    model = load_model_step(model_config=context.extra["complex_parameter"])

    trained_model = train_model(model=model)

    ...
```

{% hint style="info" %}
See the [API Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-new/#zenml.new.pipelines.pipeline_context.PipelineContext) for more information on which attributes and methods the `PipelineContext` provides.
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
