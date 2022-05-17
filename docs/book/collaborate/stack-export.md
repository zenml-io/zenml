---
description: Exporting and Importing Stacks.
---

# Export and Import ZenML Stacks

If you wish to transfer one of your stacks to another profile or even another
machine, you can do so by exporting the stack configuration and then importing
it again.

To export a stack to YAML, run the following command:

```bash
zenml stack export STACK_NAME FILENAME.yaml
```

This will create a FILENAME.yaml containing the config of your stack and all
of its components, which you can then import again like this:

```bash
zenml stack import STACK_NAME FILENAME.yaml
```

## Known Limitations

The exported Stack is only a configuration. It may have local dependencies
that are not exported and thus will not be available when importing the Stack
on another machine:

* the secrets stored in the local Secrets Managers
* any references to local files and local services not accessible from outside
the machine where the Stack is exported, such as the local Artifact Store and
Metadata Store
