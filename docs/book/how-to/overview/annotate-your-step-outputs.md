---
description: >-
  Step outputs are stored in your artifact store. Annotate and name them to make
  things easier and more explicit.
---

# Annotate your step outputs

<pre class="language-python"><code class="lang-python">    from typing_extensions import Annotated
    from zenml import step

    @step
    def my_step() -> Tuple[
        Annotated[str, "report_json"], 
        Annotated[int, accuracy]
<strong>    ]:
</strong>        ...
        return report, 1  # These outputs should be in the same order as the annotation 
</code></pre>

{% hint style="info" %}
Check our documentation here to see how to use the given names to later retrieve a specific step output.
{% endhint %}
