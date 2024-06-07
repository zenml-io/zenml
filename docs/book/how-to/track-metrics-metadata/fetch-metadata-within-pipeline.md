---
description: How to fetch metadata during pipeline composition.
---

# Fetch metadata during pipeline composition

### Pipeline configuration using the `PipelineContext`

To find information about the pipeline configuration during pipeline composition, you
can use the `zenml.get_pipeline_context()` function to access the `PipelineContext` of
your pipeline:

```python
from zenml import get_pipeline_context, pipeline

...

@pipeline(
    extra={
        "complex_parameter": [
            ("sklearn.tree", "DecisionTreeClassifier"),
            ("sklearn.ensemble", "RandomForestClassifier"),
        ]
    }
)
def my_pipeline():
    context = get_pipeline_context()

    after = []
    search_steps_prefix = "hp_tuning_search_"
    for i, model_search_configuration in enumerate(
        context.extra["complex_parameter"]
    ):
        step_name = f"{search_steps_prefix}{i}"
        cross_validation(
            model_package=model_search_configuration[0],
            model_class=model_search_configuration[1],
            id=step_name
        )
        after.append(step_name)
    select_best_model(
        search_steps_prefix=search_steps_prefix, 
        after=after,
    )
```

{% hint style="info" %}
See the [SDK Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-new/#zenml.new.pipelines.pipeline_context.PipelineContext) for more information on which attributes and methods the `PipelineContext` provides.
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
