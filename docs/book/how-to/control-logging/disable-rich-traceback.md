---
description: How to disable rich traceback output in ZenML.
---

# Disable `rich` traceback output

By default, ZenML uses the [`rich`](https://rich.readthedocs.io/en/stable/traceback.html) library to display rich traceback output. This is especially useful when debugging your pipelines. However, if you wish to disable this feature, you can do so by setting the following environment variable:

```bash
export ZENML_ENABLE_RICH_TRACEBACK=true
```

This will ensure that you see only the plain text traceback output.
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


