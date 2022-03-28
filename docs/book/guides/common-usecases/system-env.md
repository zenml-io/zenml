---
description: Control ZenML behavior with environmental variables.
---

# System environmental variables

There are a few pre-defined environmental variables that can be used to control some of 
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

When `true`, This prevents a pipeline from executing:
```bash
ZENML_PREVENT_PIPELINE_EXECUTION=false
```

Set to `false` to disable the rich traceback:
```bash
ZENML_ENABLE_RICH_TRACEBACK=true
```

Path to global ZenML config:
```bash
ZENML_CONFIG_PATH
```