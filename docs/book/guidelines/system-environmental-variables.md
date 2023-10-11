---
description: How to control ZenML behavior with environmental variables
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# System environmental variables

There are a few pre-defined environmental variables that can be used to control 
the behavior of ZenML. See the list below with default values and options:

Choose from `INFO`, `WARN`, `ERROR`, `CRITICAL`, `DEBUG`:
```bash
ZENML_LOGGING_VERBOSITY=INFO
```

Explicit path to the ZenML repository:
```bash
ZENML_REPOSITORY_PATH
```

Setting to `false` disables analytics:
```
ZENML_ANALYTICS_OPT_IN=true
```

Setting to `true` switches to developer mode:
```bash
ZENML_DEBUG=false
```

Setting the `ZENML_ACTIVE_STACK_ID` to a specific UUID will make the 
corresponding stack the active stack:
```bash
ZENML_ACTIVE_STACK_ID=<UUID-OF-YOUR-STACK>
```

When `true`, this prevents a pipeline from executing:
```bash
ZENML_PREVENT_PIPELINE_EXECUTION=false
```

Set to `false` to disable the [`rich`](https://github.com/Textualize/rich) traceback:
```bash
ZENML_ENABLE_RICH_TRACEBACK=true
```

Path to global ZenML config:
```bash
ZENML_CONFIG_PATH
```

Setting to `false` disables integrations logs suppression:
```bash
ZENML_SUPPRESS_LOGS=false
```