# Find out which configuration was used for a run

Sometimes you might want to extract the used configuration from a pipeline that has already run. You can do this simply by loading the pipeline run and accessing its `config` attribute.

<pre class="language-python"><code class="lang-python">from zenml.client import Client

pipeline_run = Client().get_pipeline_run("&#x3C;PIPELINE_RUN_NAME>")

<strong>configuration = pipeline_run.config
</strong></code></pre>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
