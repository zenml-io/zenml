---
description: Customize the pipeline deployment ASGI application with DeploymentSettings.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}



## Deployment servers and ASGI apps

ZenML pipeline deployments run an ASGI application under a production-grade
`uvicorn` server. This makes your pipelines callable over HTTP for online
workloads like real-time ML inference, LLM agents/workflows, and even full
web apps co-located with pipelines.

At runtime, three core components work together:

- the ASGI application: the HTTP surface that exposes endpoints (health, invoke,
  metrics, docs) and any custom routes or middleware you configure. This is powered by an ASGI framework like FastAPI, Starlette, Django, Flask, etc.
- the ASGI application factory (aka the Deployment App Runner): this component is responsible for constructing the ASGI application piece by piece based on the instructions provided by users via runtime configuration.
- the Deployment Service: the component responsible for the business logic that
  backs the pipeline deployment and its invocation lifecycle.

Both the Deployment App Runner and the Deployment Service are customizable at runtime, through the `DeploymentSettings` configuration mechanism. They can also be extended via inheritance to support different ASGI frameworks or to tweak existing functionality.

The `DeploymentSettings` class lets you shape both server behavior and the
ASGI app composition without changing framework code. Typical reasons to
customize include:

- Tight security posture: CORS controls, strict headers, authentication,
  API surface minimization.
- Observability: request/response logging, tracing, metrics, correlation
  identifiers.
- Enterprise integration: policy gateways, SSO/OIDC/OAuth, audit logging,
  routing and network architecture constraints.
- Product UX: single-page application (SPA) static files served alongside
  deployment APIs or custom docs paths.
- Performance/SRE: thread pool sizing, uvicorn worker settings, log levels,
  max request sizes and platform-specific fine-tuning.

All `DeploymentSettings` are pipeline-level settings. They apply to the
deployment that serves the pipeline as a whole. They are not available at
step-level.

## Configuration overview

You can configure `DeploymentSettings` in Python or via YAML, the same way as
other settings classes. The settings can be attached to a pipeline decorator
or via `with_options`. These settings are only valid at pipeline level.

### Python configuration

Use the `DeploymentSettings` class to configure the deployment settings for your
pipeline in-code

```python
from zenml import pipeline
from zenml.config import DeploymentSettings

deploy_settings = DeploymentSettings(
    app_title="Fraud Scoring Service",
    app_description=(
        "Online scoring API exposing synchronous and batch inference"
    ),
    app_version="1.2.0",
    root_url_path="",
    api_url_path="",
    docs_url_path="/docs",
    redoc_url_path="/redoc",
    invoke_url_path="/invoke",
    health_url_path="/health",
    info_url_path="/info",
    metrics_url_path="/metrics",
    cors={
        "allow_origins": ["https://app.example.com"],
        "allow_methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["*"],
        "allow_credentials": True,
    },
    thread_pool_size=32,
    uvicorn_host="0.0.0.0",
    uvicorn_port=8080,
    uvicorn_workers=2,
)

@pipeline(settings={"deployment": deploy_settings})
def scoring_pipeline() -> None:
    ...

# Alternatively
scoring_pipeline = scoring_pipeline.with_options(
    settings={"deployment": deploy_settings}
)
```

### YAML configuration

Define settings in a YAML configuration file for better separation of code and configuration:

```yaml
settings:
  deployment:
    app_title: Fraud Scoring Service
    app_description: >-
      Online scoring API exposing synchronous and batch inference
    app_version: "1.2.0"
    root_url_path: ""
    api_url_path: ""
    docs_url_path: "/docs"
    redoc_url_path: "/redoc"
    invoke_url_path: "/invoke"
    health_url_path: "/health"
    info_url_path: "/info"
    metrics_url_path: "/metrics"
    cors:
      allow_origins: ["https://app.example.com"]
      allow_methods: ["GET", "POST", "OPTIONS"]
      allow_headers: ["*"]
      allow_credentials: true
    thread_pool_size: 32
    uvicorn_host: 0.0.0.0
    uvicorn_port: 8080
    uvicorn_workers: 2
```

Check out [this page](https://docs.zenml.io/concepts/steps_and_pipelines/configuration) for more information on the hierarchy and precedence of the various ways in which you can supply the settings.

## Basic customization options

`DeploymentSettings` expose the following basic customization options. The sections below provide
short examples and guidance.

- application metadata and paths
- built-in endpoints and middleware toggles
- static files (SPAs) and dashboards
- CORS
- secure headers
- startup and shutdown hooks
- uvicorn server options, logging level, and thread pool size

### Application metadata

You can set `app_title`, `app_description`, and `app_version` to be reflected in the ASGI application's metadata:

```python
from zenml.config import DeploymentSettings

settings = DeploymentSettings(
    app_title="LLM Agent Service",
    app_description=(
        "Agent endpoints for tools, state inspection, and tracing"
    ),
    app_version="0.7.0",
)
```

### Default URL paths, endpoints and middleware

The ASGI application exposes the following built-in endpoints by default:

* documentation endpoints:
    * `/docs` - The OpenAPI documentation UI generated based on the endpoints and their signatures.
    * `/redoc` - The ReDoc documentation UI generated based on the endpoints and their signatures.
* REST API endpoints:
    * `/invoke` - The main pipeline invocation endpoint for synchronous inference.
    * `/health` - The health check endpoint.
    * `/info` - The info endpoint providing extensive information about the deployment and its service.
    * `/metrics` - Simple metrics endpoint.
* dashboard endpoints - present only if the accompanying UI is enabled:
    * `/`, `/index.html`, `/static` - Endpoints for serving the dashboard files from the `dashboard_files_path` directory.

The ASGI application includes the following built-in middleware by default:
* secure headers middleware: for setting security headers.
* CORS middleware: for handling CORS requests.

You can include or exclude these default endpoints and middleware either globally or individually by setting the `include_default_endpoints` and `include_default_middleware` settings. It is also possible to remap the built-in endpoint URL paths.

```python
from zenml.config import (
    DeploymentSettings,
    DeploymentDefaultEndpoints,
    DeploymentDefaultMiddleware,
)

settings = DeploymentSettings(
    # Include only the endpoints you need
    include_default_endpoints=(
        DeploymentDefaultEndpoints.DOCS
        | DeploymentDefaultEndpoints.INVOKE
        | DeploymentDefaultEndpoints.HEALTH
    ),
    # Customize the root URL path
    root_url_path="/pipeline",
    # Include only the middleware you need
    include_default_middleware=DeploymentDefaultMiddleware.CORS,
    # Customize the base API URL path used for all REST API endpoints
    api_url_path="/api",
    # Customize the documentation URL path
    docs_url_path="/documentation",
    # Customize the health check URL path
    health_url_path="/healthz",
)
```

With the above settings, the ASGI application will only expose the following endpoints and middleware:

- `/pipeline/documentation` - The API documentation (OpenAPI schema)
- `/pipeline/api/invoke` - The REST API pipeline invocation endpoint
- `/pipeline/api/healthz` - The REST API health check endpoint
- CORS middleware: for handling CORS requests

### Static files (single-page applications)

Deployed pipelines can serve full single-page applications (React/Vue/Svelte)
from the same origin as your inference API. This eliminates CORS/auth/routing
friction and lets you ship user-facing UI components alongside
your endpoints, such as:

* operator dashboards
* governance portals
* experiment browsers
* feature explorers
* custom data labeling interfaces
* model cards
* observability dashboards
* customer-facing playgrounds

Co-locating UI and API streamlines delivery (one image, one URL, one CI/CD),
improves latency, and keeps telemetry and auth consistent.

To enable this, point `dashboard_files_path` to a directory containing an
`index.html` and any static assets. The path must be relative to the
[source root](../steps-pipelines/sources.md#source-root):

```python
settings = DeploymentSettings(
    dashboard_files_path="web/build"  # contains index.html and assets/
)
```

A rudimentary playground dashboard is included with the ZenML python package that features a simple UI useful for sending pipeline invocations and viewing the pipeline's response.

{% hint style="info" %}
When supplying your own custom dashboard, you may also need to [customize the security headers](./deployment_settings#secure-headers) to allow the dashboard to access various resources. For example, you may want to tweak the `Content-Security-Policy` header to allow the dashboard to access external javascript libraries, images, etc.
{% endhint %}

### CORS

Fine-tune cross-origin access:

```python
from zenml.config import DeploymentSettings, CORSConfig

settings = DeploymentSettings(
    cors=CORSConfig(
        allow_origins=["https://app.example.com", "https://admin.example.com"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["authorization", "content-type", "x-request-id"],
        allow_credentials=True,
    )
)
```

### Secure headers

Harden responses with strict headers. Each field supports either a boolean or
string. Using `True` selects a safe default, `False` disables the header, and
custom strings allow fully custom policies:

```python
from zenml.config import (
    DeploymentSettings,
    SecureHeadersConfig,
)

settings = DeploymentSettings(
    secure_headers=SecureHeadersConfig(
        server=True,  # emit default ZenML server header value
        hsts=True,    # default: 63072000; includeSubdomains
        xfo=True,     # default: SAMEORIGIN
        content=True, # default: nosniff
        csp=(
            "default-src 'none'; connect-src 'self' https://api.example.com; "
            "img-src 'self' data:; style-src 'self' 'unsafe-inline'"
        ),
        referrer=True,
        cache=True,
        permissions=True,
    )
)
```

Set any field to `False` to omit that header. Set to a string for a custom
value. The defaults are strong, production-safe policies.


### Startup and shutdown hooks

Lifecycle startup and shutdown hooks are called as part of the ASGI application's lifespan. This is an alternative to [the `on_init` and `on_cleanup` hooks that can be configured at pipeline level](./deployment.md#deployment-initialization-cleanup-and-state).

Common use-cases:

- Model inference
  - load models/tokenizers and warm caches (JIT/ONNX/TensorRT, HF, sklearn)
  - hydrate feature stores, connect to vector DBs (FAISS, Milvus, PGVector)
  - initialize GPU memory pools and thread/process pools
  - set global config, download artifacts from registry or object store
  - prefetch embeddings, label maps, lookup tables
  - create connection pools for databases, Redis, Kafka, SQS, Pub/Sub

- LLM agent workflows
  - initialize LLM client(s), tool registry, and router/policy engine
  - build or load RAG indexes; warm retrieval caches and prompts
  - configure rate limiting, concurrency guards, circuit breakers
  - load guardrails (PII filters, toxicity, jailbreak detection)
  - configure tracing/observability for token usage and tool calls

- Shutdown
  - flush metrics/traces/logs, close pools/clients, persist state/caches
  - graceful draining: wait for in-flight requests before teardown

Hooks can be provided as:

- A Python callable object
- A source path string to be loaded dynamically (e.g. `my_project.runtime.hooks.on_startup`)

The callable must accept an `app_runner` argument of type `BaseDeploymentAppRunner` and any additional keyword arguments. The `app_runner` argument is the application factory that is responsible for building the ASGI application. You can use it to access information such as:

* the ASGI application instance that is being built
* the deployment service instance that is being deployed
* the `DeploymentResponse` object itself, which also contains details about the snapshot, pipeline, etc. 

```python
from zenml.deployers.server import BaseDeploymentAppRunner

def on_startup(app_runner: BaseDeploymentAppRunner, warm: bool = False) -> None:
    # e.g., warm model cache, connect tracer, prefetch embeddings
    ...

def on_shutdown(app_runner: BaseDeploymentAppRunner, drain_timeout_s: int = 2) -> None:
    # e.g., flush metrics, close clients
    ...

settings = DeploymentSettings(
    startup_hook=on_startup,
    shutdown_hook=on_shutdown,
    startup_hook_kwargs={"warm": True},
    shutdown_hook_kwargs={"drain_timeout_s": 2},
)
```

YAML using source strings:

```yaml
settings:
  deployment:
    startup_hook: my_project.runtime.hooks.on_startup
    shutdown_hook: my_project.runtime.hooks.on_shutdown
    startup_hook_kwargs:
      warm: true
    shutdown_hook_kwargs:
      drain_timeout_s: 2
```

### Uvicorn and threading

Tune server runtime parameters for performance and topology:

```python
from zenml.config import DeploymentSettings
from zenml.enums import LoggingLevels

settings = DeploymentSettings(
    thread_pool_size=64,  # CPU-bound work offload
    uvicorn_host="0.0.0.0",
    uvicorn_port=8000,
    uvicorn_workers=2,    # multi-process model
    log_level=LoggingLevels.INFO,
    uvicorn_kwargs={
        "proxy_headers": True,
        "forwarded_allow_ips": "*",
        "timeout_keep_alive": 15,
    },
)
```

## Advanced customization options

When the built-in ASGI application, endpoints and middleware are not enough, you can take customizing your deployment to the next level by providing your own implementation for endpoints, middleware and other ASGI application extensions. ZenML `DeploymentSettings` provides a flexible and extensible mechanism to inject your own custom code into the ASGI application at runtime:

- custom endpoints - to expose your own HTTP endpoints.
- custom middleware - to insert your own ASGI middleware.
- free-form ASGI application building extensions - to take full control of the ASGI application and its lifecycle for truly advanced use-cases when endpoints and middleware are not enough.

### Custom endpoints

In production, custom endpoints are often required alongside the main
pipeline invoke route. Common use-cases include:

- Online inference controls
  - model (re)load, warm-up, and cache priming
  - dynamic model/version switching and traffic shaping (A/B, canary)
  - async/batch prediction submission and job-status polling
  - feature store materialization/backfills and online/offline sync triggers

- Enterprise integration
  - authentication bootstrap (API key issuance/rotation), JWKS rotation
  - OIDC/OAuth device-code flows and SSO callback handlers
  - external system webhooks (CRM, billing, ticketing, audit sink)

- Observability and operations
  - detailed health/readiness endpoints (subsystems, dependencies)
  - metrics/traces/log shipping toggles; log level switch (INFO/DEBUG)
  - maintenance-mode enable/disable and graceful drain controls

- LLM agent serving
  - tool registry CRUD, tool execution sandboxes, guardrail toggles
  - RAG index CRUD (upsert documents, rebuild embeddings, vacuum/compact)
  - prompt template catalogs and runtime overrides
  - session memory inspection/reset, conversation export/import

- Governance and data management
  - payload redaction policy updates and capture sampling controls
  - schema/contract discovery (sample payloads, test vectors)
  - tenant provisioning, quotas/limits, and per-tenant configuration

You can configure `custom_endpoints` in `DeploymentSettings` to expose your own HTTP endpoints.

Endpoints support multiple definition modes (see code examples below):

1) Direct callable - a simple function that takes in request parameters and returns a response. Framework-specific arguments such as FastAPI's `Request`, `Response` and dependency injection patterns are supported.
2) Builder class - a callable class with a `__call__` method that is the actual endpoint callable described at 1). The builder class constructor is called by the ASGI application factory and can be leveraged to execute any global initialization logic before the endpoint is called.
3) Builder function - a function that returns the actual endpoint callable described at 1). Similar to the builder class.
4) Native framework-specific object (`native=True`). This can vary from ASGI framework to framework.

Definitions can be provided as Python objects or as loadable source path strings.

The builder class and builder function must accept an `app_runner` argument of type `BaseDeploymentAppRunner`. This is the application factory that is responsible for building the ASGI application. You can use it to access information such as:

* the ASGI application instance that is being built
* the deployment service instance that is being deployed
* the `DeploymentResponse` object itself, which also contains details about the snapshot, pipeline, etc. 

The final endpoint callable can take any input arguments and return any output that are JSON-serializable or Pydantic models. The application factory will handle converting these into the appropriate schema for the ASGI application.

You can also use framework-specific request/response types (e.g. FastAPI `Request`, `Response`) or dependency injection patterns for your endpoint callable if needed. However, this will limit the portability of your endpoint to other frameworks.

The following code examples demonstrate the different definition modes for custom endpoints:

1. a custom detailed health check endpoint implemented as a direct callable

```python
from typing import Any, Callable, Dict, List
from pydantic import BaseModel
from zenml.client import Client
from zenml.config import (
    DeploymentSettings,
    EndpointSpec,
    EndpointMethod,
)
from zenml.deployers.server import BaseDeploymentAppRunner
from zenml.models import DeploymentResponse

async def health_detailed() -> Dict[str, Any]:
    import psutil

    client = Client()

    return {
        "status": "healthy",
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "zenml": client.zen_store.get_store_info().model_dump(),
    }

settings = DeploymentSettings(
    custom_endpoints=[
        EndpointSpec(
            path="/health",
            method=EndpointMethod.GET,
            handler=health_detailed,
            auth_required=False,
        ),
    ]
)
```

2. a custom ML model inference endpoint, implemented as a builder function. Note how the builder function loads the model only once at runtime, and then reuses it for all subsequent requests.


```python
from typing import Any, Callable, Dict, List
from pydantic import BaseModel
from zenml.client import Client
from zenml.config import (
    DeploymentSettings,
    EndpointSpec,
    EndpointMethod,
)
from zenml.deployers.server import BaseDeploymentAppRunner
from zenml.models import DeploymentResponse

class PredictionRequest(BaseModel):
    features: List[float]

class PredictionResponse(BaseModel):
    prediction: float
    confidence: float

def build_predict_endpoint(
    app_runner: BaseDeploymentAppRunner,
    model_name: str,
    model_version: str,
    model_artifact: str,
) -> Callable[[PredictionRequest], PredictionResponse]:

    stored_model_version = Client().get_model_version(model_name, model_version)
    stored_model_artifact = stored_model_version.get_artifact(model_artifact)
    model = stored_model_artifact.load()

    def predict(
        request: PredictionRequest,
    ) -> PredictionResponse:
        pred = float(model.predict([request.features])[0])
        # Example: return fixed confidence if model lacks proba
        return PredictionResponse(prediction=pred, confidence=0.9)

    return predict

settings = DeploymentSettings(
    custom_endpoints=[
        EndpointSpec(
            path="/predict/custom",
            method=EndpointMethod.POST,
            handler=build_predict_endpoint,
            init_kwargs={
                "model_name": "fraud-classifier",
                "model_version": "v1",
                "model_artifact": "sklearn_model",
            },
            auth_required=True,
        ),
    ]
)
```

NOTE: a similar way to do this is to implement a proper ZenML pipeline that loads the model in the `on_init` hook and then runs pre-processing and inference steps in the pipeline.

3. a custom deployment info endpoint implemented as a builder class


```python
from typing import Any, Awaitable, Callable, Dict, List
from pydantic import BaseModel
from zenml.client import Client
from zenml.config import (
    DeploymentSettings,
    EndpointSpec,
    EndpointMethod,
)
from zenml.deployers.server import BaseDeploymentAppRunner
from zenml.models import DeploymentResponse

def build_deployment_info(app_runner: BaseDeploymentAppRunner) -> Callable[[], Awaitable[DeploymentResponse]]:
    async def endpoint() -> DeploymentResponse:
        return app_runner.deployment

    return endpoint

settings = DeploymentSettings(
    custom_endpoints=[
        EndpointSpec(
            path="/deployment",
            method=EndpointMethod.GET,
            handler=build_deployment_info,
            auth_required=True,
        ),
    ]
)
```

4. a custom model selection endpoint, implemented as a FastAPI router. This example is more involved and demonstrates how to coordinate multiple endpoints with the main pipeline invoke endpoint.

```python
# my_project.fastapi_endpoints
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sklearn.base import ClassifierMixin
from zenml.client import Client
from zenml.models import ArtifactVersionResponse
from zenml.config import DeploymentSettings, EndpointSpec, EndpointMethod

model_router = APIRouter()

# Global, process-local model registry for inference
CURRENT_MODEL: Optional[Any] = None
CURRENT_MODEL_ARTIFACT: Optional[ArtifactVersionResponse] = None


class LoadModelRequest(BaseModel):
    """Request to load/replace the in-memory model version."""

    model_name: str = Field(default="fraud-classifier")
    version_name: str = Field(default="v1")
    artifact_name: str = Field(default="sklearn_model")


@model_router.post("/load", response_model=ArtifactVersionResponse)
def load_model(req: LoadModelRequest) -> ArtifactVersionResponse:
    """Load or replace the in-memory model version."""
    global CURRENT_MODEL, CURRENT_MODEL_ARTIFACT

    model_version = Client().get_model_version(
        req.model_name, req.version_name
    )
    CURRENT_MODEL_ARTIFACT = model_version.get_artifact(req.artifact_name)
    CURRENT_MODEL = CURRENT_MODEL_ARTIFACT.load()

    return CURRENT_MODEL_ARTIFACT


@model_router.get("/current", response_model=ArtifactVersionResponse)
def current_model() -> ArtifactVersionResponse:
    """Return the artifact of the currently loaded in-memory model."""

    if CURRENT_MODEL_ARTIFACT is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No model loaded. Use /model/load first.",
        )

    return CURRENT_MODEL_ARTIFACT

deploy_settings = DeploymentSettings(
    custom_endpoints=[
        EndpointSpec(
            path="/model",
            method=EndpointMethod.POST,  # method is ignored for native routers
            handler="my_project.fastapi_endpoints.model_router",
            native=True,
            auth_required=True,
        )
    ]
)
```

And here is a minimal ZenML inference pipeline that uses the globally loaded
model. The prediction step reads the model from the global variable set
by the FastAPI router above. You can invoke this pipeline via the built-in
`/invoke` endpoint once a model has been loaded through `/model/load`.

```python
from typing import List

from pydantic import BaseModel
from zenml import pipeline, step


class InferenceRequest(BaseModel):
    features: List[float]


class InferenceResponse(BaseModel):
    prediction: float


@step
def preprocess_step(request: InferenceRequest) -> List[float]:
    # Replace with real transformations, scaling, encoding, etc.
    return request.features

@step
def predict_step(features: List[float]) -> InferenceResponse:
    """Run model inference using the globally loaded model."""

    if GLOBAL_CURRENT_MODEL is None:
        raise RuntimeError(
            "No model loaded. Call /model/load before invoking."
        )

    pred = float(GLOBAL_CURRENT_MODEL.predict([features])[0])
    return InferenceResponse(prediction=pred)


@pipeline(settings={"deployment": deploy_settings})
def inference_pipeline(request: InferenceRequest) -> InferenceResponse:
    processed = preprocess_step(request)
    return predict_step(processed)
```

### Custom middleware

Middleware is where you enforce cross-cutting concerns consistently across every endpoint. Common use-cases include:

- Security and access control
  - API key/JWT verification, tenant extraction and context injection
  - IP allow/deny lists, basic WAF-style request filtering, mTLS header checks
  - Request body/schema validation and max body size enforcement

- Governance and privacy
  - PII detection/redaction on inputs/outputs; payload sampling/scrubbing
  - Policy enforcement (data residency, retention, consent) at request time

- Reliability and traffic shaping
  - Rate limiting, quotas, per-tenant concurrency limits
  - Idempotency keys, deduplication, retries with backoff, circuit breakers
  - Timeouts, slow-request detection, maintenance mode and graceful drain

- Observability
  - Correlation/trace IDs, OpenTelemetry spans, structured logging
  - Metrics for latency, throughput, error rates, request/response sizes

- Performance and caching
  - Response caching/ETags, compression (gzip/br), streaming/chunked responses
  - Adaptive content negotiation and serialization tuning

- LLM/agent-specific controls
  - Token accounting/limits, cost guards per tenant/user
  - Guardrails (toxicity/PII/jailbreak) and output filtering
  - Tool execution sandboxing gates and allowlists

- Data and feature enrichment
  - Feature store prefetch, user/tenant profile enrichment, AB bucketing tags


You can configure `custom_middlewares` in `DeploymentSettings` to insert your own ASGI middleware.

Middlewares support multiple definition modes (see code examples below):

1) Middleware class - a standard ASGI middleware class that implements the `__call__` method that takes the traditional `scope`, `receive` and `send` arguments. The constructor must accept an `app` argument of type `ASGIApplication` and any additional keyword arguments.
2) Middleware callable - a callable that takes all arguments in one go: `app`, `scope`, `receive` and `send`.
3) Native framework-specific middleware (`native=True`) - this can vary from ASGI framework to framework.

Definitions can be provided as Python objects or as loadable source path strings. The `order` parameter controls the insertion order in the middleware chain. Lower `order` values insert the middleware earlier in the chain.

The following code examples demonstrate the different definition modes for custom middlewares:

1. a custom middleware that adds a processing time header to every response, implemented as a middleware class:

```python
import time
from typing import Any
from asgiref.compatibility import guarantee_single_callable
from asgiref.typing import (
    ASGIApplication,
    ASGIReceiveCallable,
    ASGISendCallable,
    ASGISendEvent,
    Scope,
)
from zenml.config import DeploymentSettings, MiddlewareSpec

class RequestTimingMiddleware:
    """ASGI middleware to measure request processing time."""

    def __init__(self, app: ASGIApplication, header_name: str = "x-process-time-ms") -> None:
        self.app = guarantee_single_callable(app)
        self.header_name = header_name

    async def __call__(
        self,
        scope: Scope,
        receive: ASGIReceiveCallable,
        send: ASGISendCallable,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        async def send_wrapper(message: ASGISendEvent) -> None:
            if message["type"] == "http.response.start":
                process_time = (time.time() - start_time) * 1000
                headers = list(message.get("headers", []))
                headers.append((self.header_name.encode(), str(process_time).encode()))
                message = {**message, "headers": headers}

            await send(message)

        await self.app(scope, receive, send_wrapper)


settings = DeploymentSettings(
    custom_middlewares=[
        MiddlewareSpec(
            middleware=RequestTimingMiddleware,
            order=10,
            init_kwargs={"header_name": "x-process-time-ms"},
        ),
    ]
)
```

2. a custom middleware that injects a correlation ID into responses (and generates one if missing), implemented as a middleware callable:

```python
import uuid
from typing import Any
from asgiref.compatibility import guarantee_single_callable
from asgiref.typing import (
    ASGIApplication,
    ASGIReceiveCallable,
    ASGISendCallable,
    ASGISendEvent,
    Scope,
)
from zenml.config import DeploymentSettings, MiddlewareSpec

async def request_id_middleware(
    app: ASGIApplication,
    scope: Scope,
    receive: ASGIReceiveCallable,
    send: ASGISendCallable,
    header_name: str = "x-request-id",
) -> None:
    """ASGI function middleware that ensures a correlation ID header exists."""

    app = guarantee_single_callable(app)

    if scope["type"] != "http":
        await app(scope, receive, send)
        return

    # Reuse existing request ID if present; otherwise generate one
    request_id = None
    for k, v in scope.get("headers", []):
        if k.decode().lower() == header_name:
            request_id = v.decode()
            break

    if not request_id:
        request_id = str(uuid.uuid4())

    async def send_wrapper(message: ASGISendEvent) -> None:
        if message["type"] == "http.response.start":
            headers = list(message.get("headers", []))
            headers.append((header_name.encode(), request_id.encode()))
            message = {**message, "headers": headers}

        await send(message)

    await app(scope, receive, send_wrapper)


settings = DeploymentSettings(
    custom_middlewares=[
        MiddlewareSpec(
            middleware=request_id_middleware,
            order=5,
            init_kwargs={"header_name": "x-request-id"},
        ),
    ]
)
```

4. a FastAPI/Starlette-native middleware that adds GZIP support, implemented as a native middleware:

```python
from starlette.middleware.gzip import GZipMiddleware
from zenml.config import DeploymentSettings, MiddlewareSpec

settings = DeploymentSettings(
    custom_middlewares=[
        MiddlewareSpec(
            middleware=GZipMiddleware,
            native=True,
            order=20,
            extra_kwargs={"minimum_size": 1024},
        ),
    ]
)
```

### App extensions

App extensions are pluggable components that are running as part of the ASGI application factory that can install complex, possibly framework-specific structures. The following are usual scenarios for using a full-blown extension instead of endpoints/middleware:

- Advanced authentication and authorization
  - install org-wide dependencies (e.g., OAuth/OIDC auth, RBAC guards)
  - register custom exception handlers for uniform error envelopes
  - augment OpenAPI with security schemes and per-route security policies

- Multi-tenant and routing topology
  - programmatically include routers per tenant/region/version
  - mount sub-apps for internal admin vs public APIs under different prefixes
  - dynamic route rewrites/switches for blue/green or canary rollouts

- Observability and platform integration
  - wire OpenTelemetry instrumentation at the app level (tracer/meter providers)
  - register global request/response logging with redaction policies
  - expose or mount vendor-specific observability apps (e.g., Prometheus)

- LLM agent control plane
  - attach a tool registry/router and lifecycle hooks for tools
  - register guardrail handlers and policy engines across routes
  - install runtime prompt/template catalogs and index management routers

- API ergonomics and governance
  - reshape OpenAPI (tags, servers, components) and versioned docs
  - global response model wrapping, pagination conventions, error mappers
  - maintenance-mode switch and graceful-drain controls at the app level

App extensions support multiple definition modes (see code examples below):

1) Extension class - a class that implements the `BaseAppExtension` abstract class. The class constructor must accept any keyword arguments and the `install` method must accept an `app_runner` argument of type `BaseDeploymentAppRunner`.
2) Extension callable - a callable that takes the `app_runner` argument of type `BaseDeploymentAppRunner`.

Both classes and callables must take in an `app_runner` argument of type `BaseDeploymentAppRunner`. This is the application factory that is responsible for building the ASGI application. You can use it to access information such as:

* the ASGI application instance that is being built
* the deployment service instance that is being deployed
* the `DeploymentResponse` object itself, which also contains details about the snapshot, pipeline, etc. 

Definitions can be provided as Python objects or as loadable source path strings.

The extensions are summoned to take part in the ASGI application building process near the end of the initialization - after the ASGI app has been built according to the deployment configuration settings.

The example below installs API key authentication at the FastAPI application
level, attaches the dependency to selected routes, registers an auth error
handler, and augments the OpenAPI schema with the security scheme.

```python
from __future__ import annotations

from typing import Literal, Sequence, Set

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from zenml.config import AppExtensionSpec, DeploymentSettings
from zenml.deployers.server.app import BaseDeploymentAppRunner
from zenml.deployers.server.extensions import BaseAppExtension


class FastAPIAuthExtension(BaseAppExtension):
    """Install API key auth and OpenAPI security on a FastAPI app."""

    def __init__(
        self,
        scheme: Literal["api_key"] = "api_key",
        header_name: str = "x-api-key",
        valid_keys: Sequence[str] | None = None,
    ) -> None:
        self.scheme = scheme
        self.header_name = header_name
        self.valid_keys: Set[str] = set(valid_keys or [])

    def install(self, app_runner: BaseDeploymentAppRunner) -> None:
        app = app_runner.asgi_app
        if not isinstance(app, FastAPI):
            raise RuntimeError("FastAPIAuthExtension requires FastAPI")

        api_key_header = APIKeyHeader(
            name=self.header_name, auto_error=True
        )

        # Find endpoints that have auth_required=True
        protected_endpoints = [
            endpoint.path
            for endpoint in app_runner.endpoints
            if endpoint.auth_required
        ]

        @app.middleware("http")
        async def api_key_guard(request: Request, call_next):
            if request.url.path in protected_endpoints:
                api_key = await api_key_header(request)
                if api_key not in self.valid_keys:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or missing API key",
                    )
            return await call_next(request)

        # Auth error handler
        @app.exception_handler(HTTPException)
        async def auth_exception_handler(
            _, exc: HTTPException
        ) -> JSONResponse:
            if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                    headers={"WWW-Authenticate": "ApiKey"},
                )
            return JSONResponse(
                status_code=exc.status_code, content={"detail": exc.detail}
            )

        # OpenAPI security
        def custom_openapi() -> dict:
            if app.openapi_schema:
                return app.openapi_schema  # type: ignore[return-value]
            openapi_schema = get_openapi(
                title=app.title,
                version=app.version if app.version else "0.1.0",
                description=app.description,
                routes=app.routes,
            )
            components = openapi_schema.setdefault("components", {})
            security_schemes = components.setdefault("securitySchemes", {})
            security_schemes["ApiKeyAuth"] = {
                "type": "apiKey",
                "in": "header",
                "name": self.header_name,
            }
            openapi_schema["security"] = [{"ApiKeyAuth": []}]
            app.openapi_schema = openapi_schema
            return openapi_schema

        app.openapi = custom_openapi  # type: ignore[assignment]


settings = DeploymentSettings(
    app_extensions=[
        AppExtensionSpec(
            extension=(
                "my_project.extensions.FastAPIAuthExtension"
            ),
            extension_kwargs={
                "scheme": "api_key",
                "header_name": "x-api-key",
                "valid_keys": ["secret-1", "secret-2"],
            },
        )
    ]
)
```

## Implementation customizations for advanced use cases

For cases where you need deeper control over how the ASGI app is created or
how the deployment logic is implemented, you can swap/extend the core
components using the following `DeploymentSettings` fields:

- `deployment_app_runner_flavor` and `deployment_app_runner_kwargs` let you
  choose or extend the app runner that constructs and runs the ASGI app. This
  needs to be set to a subclass of `BaseDeploymentAppRunnerFlavor`, which is
  basically a descriptor of an app runner implementation that itself is a
  subclass of `BaseDeploymentAppRunner`.
- `deployment_service_class` and `deployment_service_kwargs` let you provide
  your own deployment service to customize the pipeline deployment logic. This
  needs to be set to a subclass of `BasePipelineDeploymentService`.

Both accept loadable sources or objects. We cover how to implement custom
runner flavors and services in a dedicated guide.
