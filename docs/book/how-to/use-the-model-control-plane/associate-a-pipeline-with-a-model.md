# Associate a pipeline with a Model

The most common use-case for a Model is to associate it with a pipeline.

<pre class="language-python"><code class="lang-python"><strong>from zenml import pipeline
</strong>from zenml import Model

<strong>@pipeline(
</strong><strong>    model=Model(
</strong><strong>        name="ClassificationModel",  # Give your models unique names
</strong><strong>        tags=["MVP", "Tabular"]  # Use tags for future filtering
</strong><strong>    )
</strong><strong>)
</strong>def my_pipeline():
    ...
</code></pre>

This will associate this pipeline with the model specified. In case the model already exists, this will create a new version of that model.

In case you want to attach the pipeline to an existing model version, specify this as well.

```python
from zenml import pipeline
from zenml import Model
from zenml.enums import ModelStages

@pipeline(
    model=Model(
        name="ClassificationModel",  # Give your models unique names
        tags=["MVP", "Tabular"],  # Use tags for future filtering
        version=ModelStages.LATEST  # Alternatively use a stage: [STAGING, PRODUCTION]]
    )
)
def my_pipeline():
    ...
```

Feel free to also move the Model configuration into your configuration files:

```yaml
...

model:
  name: text_classifier
  description: A breast cancer classifier
  tags: ["classifier","sgd"]

...
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


