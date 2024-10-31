---
description: Export stack requirements
---

You can get the `pip` requirements of your stack by running the `zenml stack export-requirements <STACK-NAME>` CLI command.

To install those requirements, it's best to write them to a file and then install them like this:
```bash
zenml stack export-requirements <STACK-NAME> --output-file stack_requirements.txt
pip install -r stack_requirements.txt
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
