# ZenML sandbox bridge for Google Cloud Run

Cloud Run sandboxes have no standalone REST API: the `sandbox` CLI only
exists inside a Cloud Run service deployed with the sandbox launcher. This
directory contains the small HTTP service — the *bridge* — that the ZenML
`cloudrun` sandbox flavor talks to.

## What it does

The bridge translates the ZenML sandbox bridge protocol (v1) into
`/usr/local/gcp/bin/sandbox` CLI calls:

| Endpoint | CLI |
|---|---|
| `POST /v1/sandbox` (caller supplies the id) | `sandbox run <id> --detach … -- sleep infinity` |
| `POST /v1/sandbox/<id>/exec` | `sandbox exec <id> [--env K=V] [--workdir DIR] -- argv…` (streamed as SSE) |
| `DELETE /v1/sandbox/<id>/exec/<exec-id>` | terminates the running command |
| `PUT/GET /v1/sandbox/<id>/file/<path>` | staged through a bind-mounted share directory |
| `POST /v1/sandbox/<id>/snapshot` | `sandbox tar <id>` + upload to Cloud Storage |
| `GET /v1/sandbox/<id>/running` | `sandbox exec <id> /bin/true` |
| `DELETE /v1/sandbox/<id>` | `sandbox delete <id> --force` |

The client generates sandbox ids, so a create whose response is lost can
still be cleaned up. Exec commands carry a client-generated exec id so
`process.kill()` can terminate them. File staging opens host-side
descriptors with `O_NOFOLLOW`, so untrusted sandbox code can't redirect a
transfer to a host path via a symlink.

> **Verify before release:** the exec CLI flags (`--env`, `--workdir`) and
> the mount/`--import-tar` syntax are taken from the public
> [code-execution docs](https://docs.cloud.google.com/run/docs/code-execution);
> confirm them with `sandbox exec -h` on a deployed instance, since the CLI
> is still in preview.

Authentication is delegated to Cloud Run IAM — the bridge itself contains no
auth code. Deploy with `--no-allow-unauthenticated` and Cloud Run verifies
the caller's Google ID token before the request reaches the container.

## Deploy

```bash
gcloud beta run deploy zenml-sandbox-bridge \
  --source . \
  --region europe-west1 \
  --sandbox-launcher \
  --no-allow-unauthenticated \
  --max-instances 1 \
  --min-instances 1 \
  --no-cpu-throttling \
  --memory 2Gi --cpu 2
```

Why these flags:

- `--sandbox-launcher` — enables the `sandbox` CLI inside the instance
  (requires the second-generation execution environment).
- `--max-instances 1` — persistent sandboxes are instance-local; a second
  instance would not see sandboxes created on the first.
- `--min-instances 1 --no-cpu-throttling` — keeps detached sandboxes alive
  and scheduled between requests.
- Sandboxes share the instance's CPU/memory: size `--memory`/`--cpu` for
  your workload.

Grant callers invoke rights:

```bash
gcloud run services add-iam-policy-binding zenml-sandbox-bridge \
  --region europe-west1 \
  --member "serviceAccount:YOUR_CALLER_SA" \
  --role roles/run.invoker
```

For snapshots, also grant the *service's* runtime service account
`roles/storage.objectAdmin` on the snapshot bucket.

## Register the ZenML component

```bash
zenml integration install gcp
zenml sandbox register cloudrun_sandbox --flavor cloudrun \
  --service_url="$(gcloud run services describe zenml-sandbox-bridge \
      --region europe-west1 --format 'value(status.url)')" \
  --snapshot_uri_prefix="gs://my-bucket/zenml-sandbox-snapshots"
zenml stack update my_stack --sandbox cloudrun_sandbox
```

Then, inside a step:

```python
from zenml.client import Client

sandbox = Client().active_stack.sandbox
with sandbox.create_session(destroy_on_exit=True) as session:
    output = session.exec("python3 -c 'print(21 * 2)'").collect()
    assert output.stdout.strip() == "42"
```

## Notes and limits

- File transfer is capped at 32 MiB per request (a Cloud Run request-body
  limit); route bigger payloads through GCS and fetch them from inside the
  sandbox (`allow_egress` or a mounted path).
- A single exec stream is bounded by the Cloud Run request timeout (max 60
  minutes) — keep `timeout_ms` below the service timeout.
- The `sandbox` CLI is in public preview; flag names may change. All CLI
  interaction is contained in `main.py`.
