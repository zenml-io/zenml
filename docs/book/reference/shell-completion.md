---
description: Enable shell completion for the ZenML CLI.
---

# Shell completion

ZenML uses Click's built-in shell completion for the `zenml` command. Completion
is opt-in: add the activation command for your shell to the appropriate shell
configuration file.

For Bash:

```bash
eval "$(_ZENML_COMPLETE=bash_source zenml)"
```

For Zsh:

```bash
eval "$(_ZENML_COMPLETE=zsh_source zenml)"
```

For Fish:

```fish
_ZENML_COMPLETE=fish_source zenml | source
```

For faster shell startup, generate the script once and source the generated
file:

```bash
_ZENML_COMPLETE=bash_source zenml > ~/.zenml-complete.bash
echo "source ~/.zenml-complete.bash" >> ~/.bashrc
```

Command and option completion is local. Resource-name completion may query your
configured ZenML store or server for stacks, stack components, flavors, service
connectors, connector metadata, and secrets that your user can list.

Dynamic completion is best effort. If ZenML is offline, unauthenticated, the
backend is unavailable, or the query fails, completion returns no dynamic
resource candidates instead of printing errors. Secret completion suggests
secret names only, never secret values. Service connector resource IDs are not
completed because discovering them can enumerate provider resources.

Set `ZENML_CLI_DISABLE_DYNAMIC_COMPLETION=1` to keep only local command and
option completion.
