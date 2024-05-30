---
description: How to set the logging verbosity in ZenML.
---

# Set logging verbosity

By default, ZenML sets the logging verbosity to `INFO`. If you wish to change this, you can do so by setting the following environment variable:

```bash
export ZENML_LOGGING_VERBOSITY=INFO
```

Choose from `INFO`, `WARN`, `ERROR`, `CRITICAL`, `DEBUG`. This will set the logs
to whichever level you suggest.
