---
description: Container-isolated sandbox sessions on a local Docker daemon.
---

# Docker Sandbox

The Docker sandbox flavor runs each session as a container on the local Docker daemon: real filesystem and process isolation, arbitrary images, no cloud account. It is the container-isolated counterpart to the [Local](local.md) flavor and the laptop-scale counterpart to [Kubernetes](kubernetes.md) and [Modal](modal.md).

Sessions boot the configured image with a keep-alive command (the image's own `ENTRYPOINT` is cleared, so task images with entrypoints of their own still work). `exec` maps to Docker exec with the session's environment and working directory; file transfer maps to Docker's archive API; `create_snapshot()` commits the container filesystem to a local image that `restore()` can boot again.

## How to register

```bash
zenml sandbox register docker-sb --flavor=docker --image=python:3.11-slim
zenml stack update --sandbox docker-sb
```

A reachable Docker daemon is required at session-creation time.

## Settings

The Docker sandbox inherits `BaseSandboxSettings` and adds:

- `image`: the container image sessions boot from. Task-level image overrides (for example Harbor's per-task `docker_image`) replace this per session via the flavor's image-override capability.
- `workdir`: the working directory inside the container (default `/workspace`). Relative `exec`/`upload_file`/`download_file` paths resolve against it.
- `cpu_limit` / `memory_limit`: optional Docker resource limits (`--cpus` / `--memory` semantics).
- `pull_policy`: `missing` (default) pulls only when the image is absent locally, `always` pulls per session, `never` fails instead of pulling.

## Feature support

| Feature | Docker | Notes |
|---|---|---|
| `snapshot()` / `restore()` | ✅ | `docker commit` to a local image; restore boots a fresh session from it. |
| `attach(session_id)` | ✅ | Sessions are labeled containers; attachable while running. |
| `upload_file` / `download_file` | ✅ | Archive-based; relative paths resolve against `workdir`. |
| Streaming output | ✅ | Demuxed stdout/stderr line streams. |
| Task image overrides | ✅ | Via `image_settings()` — used by the Harbor bridge for task-pinned images. |
| `destroy()` | ✅ | Force-removes the session container. `close()` only releases the handle; the container keeps running until destroyed. |

## When to use it

- Running containerized eval/RL tasks (for example Harbor tasks, which pin per-task images) on a laptop, without a cluster or a cloud account.
- Local development against the same abstraction a `kubernetes` or `modal` stack uses in production — swapping the flavor is a stack change, not a code change.

For untrusted workloads at scale or with stronger tenancy guarantees, prefer the Kubernetes or Modal flavors.
