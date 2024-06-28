---
description: Register a cloud stack easily
---

# Register a cloud stack with an easy wizard

{% hint style="info" %}
This is a hint for reference.
{% endhint %}

{% tabs %}

{% tab title="Dashboard" %}
<figure><img src="../../.gitbook/assets/Create_Stack.png" alt=""><figcaption><p>This should be the right image.</p></figcaption></figure>
{% endtab %}

{% tab title="CLI" %}

```shell
export STACK_NAME=aws_stack

zenml stack register ${STACK_NAME} -o ${ORCHESTRATOR_NAME} \
    -a ${ARTIFACT_STORE_NAME} -c ${CONTAINER_REGISTRY_NAME} --set
```

{% endtab %}
{% endtabs %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
