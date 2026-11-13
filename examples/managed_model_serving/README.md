# Managed model serving example

This example requires the coordinated unreleased core, Pro plugin, cloud API and infrastructure changes. It remains disabled by default. It has not been validated against a real fine-tuned model or Baseten account.

## Prepare the artifacts

The training workflow must export expanded Transformers safetensors plus `config.json`, and save the actual tokenizer using `save_pretrained`. For a sharded export, include every shard referenced by `model.safetensors.index.json`. Store these files beneath immutable directories in the active S3 artifact store and register each directory with `zenml.artifacts.utils.register_artifact`. Use the resulting artifact-version IDs. Do not pass an archived `DirectoryMaterializer` output: the initial resolver does not unpack archives or execute materializers.

The existing AWS service connector must be usable by the workspace. Its returned storage credentials are passed privately to Baseten for this POC, including a session token when present. The deployment step and bot never receive the Baseten key. No universal `LLMWeights` Python type is assumed.

Register a model deployer with `zenml model-deployer register managed-serving --flavor=managed`, attach it to the active stack, then call `serve_registered_model` in `deploy.py` with the two artifact-version IDs, an approved profile, and a persisted request key. Reuse that key only when retrying the same intended deployment. The step disables caching and receives `UnmaterializedArtifact` metadata instead of downloading the weights.

## Inspect and invoke

```python
from uuid import UUID
from zenml.managed_models.client import ManagedModelClient
from zenml.models.managed_model import ManagedModelMutation

client = ManagedModelClient()
service = client.get(UUID("<service-id-from-the-deployment-step>"))
service = client.wait(service, timeout=600)
for event in client.stream(service.id, [{"role": "user", "content": "Hello"}], max_tokens=64):
    print(event)

paused = client.mutate(service.id, ManagedModelMutation(action="pause", expected_generation=service.generation), request_key="<persisted-pause-intent-key>")
client.wait(paused)
```

Use `ManagedModelMutation` for update, rollback, resume, delete and retry. Updates carry a new revision; rollback carries an exact retained revision ID. Every mutation uses the last observed generation and its own persisted request key. A wait timeout never cancels backend work. `retry` preserves recovery checkpoints and does not blindly recreate an uncertain provider deployment.

After asynchronous deletion succeeds, `client.purge(service.id)` removes the tombstone and releases its project/model-deployer references. Customer artifacts are never deleted by service cleanup. The actual Beam training export remains a separate integration task until a representative producer and artifact are available.
