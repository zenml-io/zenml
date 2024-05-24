# Find out what configuration was used

<pre class="language-python"><code class="lang-python">from zenml.client import Client

pipeline_run = Client().get_pipeline_run("&#x3C;PIPELINE_RUN_NAME>")

<strong>configuration = pipeline_run.config
</strong></code></pre>
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


