# Find out what configuration was used

<pre class="language-python"><code class="lang-python">from zenml.client import Client

pipeline_run = Client().get_pipeline_run("&#x3C;PIPELINE_RUN_NAME>")

<strong>configuration = pipeline_run.config
</strong></code></pre>
