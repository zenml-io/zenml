---
description: Customize the pipeline deployment ASGI application with DeploymentSettings.
---


## Deployment servers and ASGI apps

ZenML pipeline deployments run an ASGI application under a production-grade
`uvicorn` server. This makes your pipelines callable over HTTP for online
workloads like real-time ML inference, LLM agents/workflows, and even full
web apps co-located with pipelines.

At runtime, two core components work together:

- ASGI application: the HTTP surface that exposes endpoints (health, invoke,
  metrics, docs) and any custom routes or middleware you configure.
- Deployment service: the component responsible for the business logic that
  backs the pipeline deployment and its invocation lifecycle.

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

Before being launched, the ASGI application is constructed piece by piece from
the `DeploymentSettings` by an ASGI application factory component - aka the
Deployment App Runner - which itself can be extended via inheritance to support
different ASGI frameworks or to tweak existing functionality.

## Configuration overview

You can configure `DeploymentSettings` in Python or via YAML, the same way as
other settings classes. The settings can be attached to a pipeline decorator
or via `with_options`. These settings are only valid at pipeline level.

### Python configuration

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

## What you can customize

`DeploymentSettings` expose the following key areas. The sections below provide
short examples and guidance.

- Application metadata and paths
- Built-in endpoints and middleware toggles
- Static files (SPAs) and dashboards
- CORS
- Secure headers
- Startup and shutdown hooks
- Custom endpoints
- Custom middleware
- App extensions
- Uvicorn server options, logging level, and thread pool size


### Application metadata

You can set `app_title`, `app_description`, and `app_version`.

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

### Default endpoints and middleware

The ASGI application exposes the following built-in endpoints:

* documentation endpoints:
    * `/docs` - The API documentation (OpenAPI schema)
    * `/redoc` - The API documentation (ReDoc schema)
* REST API endpoints:
    * `/invoke` - The API invoke endpoint (for synchronous inference)
    * `/health` - The API health check endpoint (for health checks)
    * `/info` - The API info endpoint (for service information)
    * `/metrics` - The API metrics endpoint (for metrics)
* dashboard endpoints:
    * `/`, `/index.html`, `/static` - Endpoints for serving the dashboard files

The ASGI application includes the following built-in middleware:
* secure headers middleware: for setting security headers
* CORS middleware: for handling CORS requests

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
- `/pipeline/api/invoke` - The API invoke endpoint (for synchronous inference)
- `/pipeline/api/healthz` - The API health check endpoint (for health checks)
- CORS middleware: for handling CORS requests

### Static files (SPA)

Serve a single-page app (e.g., React/Vue) alongside your APIs by setting
`dashboard_files_path` to a directory that contains an `index.html` and any
assets subdirectories. The path must be relative to the [source root](../steps-pipelines/sources.md#source-root).

```python
settings = DeploymentSettings(
    dashboard_files_path="web/build"  # contains index.html and assets/
)
```

This is useful to ship a minimal admin console, model cards, an operator
UI or a full-fledged single-page application side-by-side with the deployment.
If not set, the default deployment UI that is included with the ZenML python package
will be used, unless explicitly excluded via `include_default_endpoints`.

{% hint style="info" %}
When supplying your own custom dashboard, you may also need to [customize the security headers](./deployment_settings#secure-headers) to allow the dashboard to access various resources. For example, you may want to tweak the `Content-Security-Policy` header to allow the dashboard to access external javascript libraries, images, etc.
{% endhint %}

### CORS

Fine-tune cross-origin access.

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
custom strings allow fully custom policies.

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

Register lifecycle hooks to initialize shared clients (DB, feature store,
tracer) or to perform graceful shutdown.

Hooks can be provided as:

- A Python callable object
- A source path string to be loaded dynamically (e.g. `my_project.runtime.hooks.on_startup`)

```python
def on_startup(warm: bool = False) -> None:
    # e.g., warm model cache, connect tracer, prefetch embeddings
    ...

def on_shutdown(drain_timeout_s: int = 2) -> None:
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

The startup and shutdown hooks are called as part of the ASGI application's lifespan.

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


## Custom endpoints

Use `custom_endpoints` to expose your own HTTP endpoints. These can power
real-time inference, LLM agent tools, orchestration webhooks, or integration
health endpoints. Endpoints support multiple definition modes:

1) Direct callable (framework-specific signature allowed)
2) Builder class (callable class with `__call__`)
3) Builder function (returns the actual endpoint callable)
4) Native framework-specific object (`native=True`)

Definitions can be provided as Python objects or as loadable source strings.

The adapter passes `app_runner` into builders - this is the `BaseDeploymentAppRunner`
instance - the application factory that is responsible for building the ASGI
application. You can use it to access information such as:

* the built ASGI app
* the deployment service instance
* the `DeploymentResponse` object itself

The signature of the endpoint function itself can take any input arguments and return any output that are JSON-serializable or Pydantic models. It can also use framework-specific request/response types (e.g. FastAPI `Request`, `Response`) or dependency injection patterns as needed.

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

# 1) Direct callable: detailed health check endpoint
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

# 2) Builder function: load a model once and expose a prediction endpoint
class PredictionRequest(BaseModel):
    features: List[float]

class PredictionResponse(BaseModel):
    prediction: float
    confidence: float

def build_predict_endpoint(
    app_runner: BaseDeploymentAppRunner, model_path: str
) -> Callable[[PredictionRequest], PredictionResponse]:
    import joblib

    # This gets loaded only once at app build time
    model = joblib.load(model_path)

    async def predict(
        request: PredictionRequest,
    ) -> PredictionResponse:
        yhat = float(model.predict([request.features])[0])
        # Example: return fixed confidence if model lacks proba
        return PredictionResponse(prediction=yhat, confidence=0.9)

    return predict

# 3) Builder function: deployment info
def build_deployment_info(app_runner: BaseDeploymentAppRunner) -> Callable[[], DeploymentResponse]:
    async def endpoint() -> DeploymentResponse:
        return app_runner.deployment

    return endpoint

settings = DeploymentSettings(
    custom_endpoints=[
        EndpointSpec(
            path="/health",
            method=EndpointMethod.GET,
            handler=health_detailed,
            auth_required=False,
        ),
        EndpointSpec(
            path="/predict/custom",
            method=EndpointMethod.POST,
            handler=build_predict_endpoint,
            init_kwargs={"model_path": "/models/model.pkl"},
            auth_required=True,
        ),
        EndpointSpec(
            path="/deployment",
            method=EndpointMethod.GET,
            handler=build_deployment_info,
            auth_required=False,
        ),
    ]
)
```

FastAPI-native example (native mode). In native mode you pass a
framework-specific object; the adapter uses it directly. You can also use
`extra_kwargs` for framework-specific parameters like `response_model`.

```python
# my_project.fastapi_endpoints
from pydantic import BaseModel
from fastapi import APIRouter
from typing import List

from zenml.config import (
    DeploymentSettings,
    EndpointSpec,
    EndpointMethod,
)

router = APIRouter()

class ScoreRequest(BaseModel):
    features: List[float]

class ScoreResponse(BaseModel):
    score: float

@router.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest) -> ScoreResponse:
    return ScoreResponse(score=0.42)
```

```python
from zenml.config import DeploymentSettings, EndpointSpec, EndpointMethod

settings = DeploymentSettings(
    custom_endpoints=[
        EndpointSpec(
            path="/native/score",
            method=EndpointMethod.POST,
            handler="my_project.fastapi_endpoints.router",
            native=True,
            auth_required=True,
        )
    ]
)
```

Notes:

- `auth_required` signals to the adapter to attach any configured auth
  dependencies or middlewares.
- Direct callable endpoints may use framework request/response types (e.g.,
  FastAPI `Request`, `Response`) as needed.


## Custom middleware

`custom_middlewares` allows inserting ASGI middleware for security,
observability, and behavior shaping (rate limiting, correlation IDs, tracing,
body size limits, gzip, etc.). Supported modes are:

1) Middleware class (ASGI callable class)
2) Middleware function (ASGI callable function)
3) Native framework-specific middleware (`native=True`)

```python
import time
from typing import Any
from asgiref.typing import (
    ASGIApplication,
    ASGIReceiveCallable,
    ASGISendCallable,
    Scope,
)
from zenml.config import DeploymentSettings, MiddlewareSpec

class RequestTimingMiddleware:
    """ASGI middleware to measure request processing time.

    Uses the standard ASGI interface (scope, receive, send) which works across
    all ASGI frameworks: FastAPI, Django, Starlette, Quart, etc.
    """

    def __init__(self, app: ASGIApplication) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: ASGIReceiveCallable,
        send: ASGISendCallable,
    ) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start_time = time.time()

        async def send_wrapper(message):  # type: ignore
            if message["type"] == "http.response.start":
                process_time = (time.time() - start_time) * 1000
                headers = list(message.get("headers", []))
                headers.append((b"x-process-time-ms", str(process_time).encode()))
                message = {**message, "headers": headers}

            await send(message)

        await self.app(scope, receive, send_wrapper)


async def timing_header_middleware(
    app: ASGIApplication,
    scope: Scope,
    receive: ASGIReceiveCallable,
    send: ASGISendCallable,
    header_name: str = "x-process-time-ms",
) -> None:
    """ASGI function middleware that adds a timing header.

    Args:
        app: The wrapped ASGI application.
        scope: The ASGI connection scope.
        receive: Callable to receive ASGI events.
        send: Callable to send ASGI events.
        header_name: Name of the header to inject.
    """
    if scope["type"] != "http":
        await app(scope, receive, send)
        return

    start_time = time.time()

    async def send_wrapper(message) -> None:  # type: ignore[no-any-explicit]
        if message["type"] == "http.response.start":
            ms = (time.time() - start_time) * 1000
            headers = list(message.get("headers", []))
            headers.append((header_name.encode(), f"{ms}".encode()))
            message = {**message, "headers": headers}

        await send(message)

    await app(scope, receive, send_wrapper)


settings = DeploymentSettings(
    custom_middlewares=[
        MiddlewareSpec(
            middleware=RequestTimingMiddleware,
            order=10,
        ),
        MiddlewareSpec(
            middleware=timing_header_middleware,
            order=5,
            init_kwargs={"header_name": "x-latency-ms"},
        ),
    ]
)
```

FastAPI/Starlette-native middlewares (native mode):

```python
settings = DeploymentSettings(
    custom_middlewares=[
        MiddlewareSpec(
            middleware="starlette.middleware.cors.CORSMiddleware",
            native=True,
            order=0,
            extra_kwargs={
                "allow_origins": ["*"],
                "allow_methods": ["*"],
                "allow_headers": ["*"],
            },
        ),
        MiddlewareSpec(
            middleware="starlette.middleware.gzip.GZipMiddleware",
            native=True,
            order=20,
            extra_kwargs={"minimum_size": 1024},
        ),
    ]
)
```

Ordering: lower `order` values install earlier in the chain.


## App extensions

App extensions are pluggable components that can install complex, possibly
framework-specific structures: routers, auth systems, tracing, or metrics.

You can supply either a callable or a class. The adapter passes `app_runner` into both - this is the `BaseDeploymentAppRunner` instance - the application factory that is responsible for building the ASGI application. You can use it to access information such as:

* the built ASGI app
* the deployment service instance
* the `DeploymentResponse` object itself

The extensions are installed into the ASGI near the end of the process - after the ASGI app has been built according to the deployment settings.

The example below installs API key authentication at the FastAPI application
level, attaches the dependency to selected routes, registers an auth error
handler, and augments the OpenAPI schema with the security scheme.

```python
from __future__ import annotations

from typing import Literal, Sequence, Set

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
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
        protect_paths_prefix: str = "/api",
    ) -> None:
        self.scheme = scheme
        self.header_name = header_name
        self.valid_keys: Set[str] = set(valid_keys or [])
        self.protect_paths_prefix = protect_paths_prefix

    def install(self, app_runner: BaseDeploymentAppRunner, **_: object) -> None:
        app = app_runner.asgi_app
        if not isinstance(app, FastAPI):
            raise RuntimeError("FastAPIAuthExtension requires FastAPI")

        api_key_header = APIKeyHeader(
            name=self.header_name, auto_error=False
        )

        async def verify_api_key(
            api_key: str | None = Depends(api_key_header),
        ) -> None:
            if not api_key or api_key not in self.valid_keys:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or missing API key",
                )

        # Attach dependency to protected routes
        for route in app.routes:
            if isinstance(route, APIRoute) and route.path.startswith(
                self.protect_paths_prefix
            ):
                route.dependencies.append(Depends(verify_api_key))

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
                "protect_paths_prefix": "/api",
            },
        )
    ]
)
```

## Advanced: customizing the runner and service

For cases where you need deeper control over how the ASGI app is created or
how the deployment logic is implemented, you can swap/extend the core
components:

- `deployment_app_runner_flavor` and `deployment_app_runner_kwargs` let you
  choose or extend the app runner that constructs and runs the ASGI app.
- `deployment_service_class` and `deployment_service_kwargs` let you provide
  your own deployment service to customize the pipeline deployment logic.

Both accept loadable sources or objects. We cover how to implement custom
runner flavors and services in a dedicated guide.

