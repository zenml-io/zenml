#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Base deployment app runner."""

import os
import re
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)
from uuid import UUID

from asgiref.compatibility import guarantee_single_callable
from asgiref.typing import (
    ASGIApplication,
    ASGIReceiveCallable,
    ASGISendCallable,
    ASGISendEvent,
    Scope,
)

from zenml.client import Client
from zenml.config import (
    AppExtensionSpec,
    DeploymentDefaultEndpoints,
    DeploymentDefaultMiddleware,
    DeploymentSettings,
    EndpointMethod,
    EndpointSpec,
    MiddlewareSpec,
)
from zenml.config.source import SourceOrObject
from zenml.deployers.server.adapters import (
    EndpointAdapter,
    MiddlewareAdapter,
)
from zenml.deployers.server.extensions import BaseAppExtension
from zenml.deployers.server.models import (
    BaseDeploymentInvocationRequest,
    BaseDeploymentInvocationResponse,
)
from zenml.deployers.server.service import (
    BasePipelineDeploymentService,
    PipelineDeploymentService,
)
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models.v2.core.deployment import DeploymentResponse
from zenml.utils import source_utils
from zenml.utils.daemon import setup_daemon

if TYPE_CHECKING:
    from secure import Secure

logger = get_logger(__name__)

ZENML_DEPLOYMENT_ID_ENV_VAR = "ZENML_DEPLOYMENT_ID"


class BaseDeploymentAppRunner(ABC):
    """Base class for deployment app runners.

    This class is responsible for building and running the ASGI compatible web
    application (e.g. FastAPI, Django, Flask, Falcon, Quart, BlackSheep, etc.) and the
    associated deployment service for the pipeline deployment. It also acts as
    a adaptation layer between the REST API interface and deployment service to
    preserve the following separation of concerns between the two components:

    * the ASGI application is responsible for handling the HTTP requests and
    responses to the user
    * the deployment service is responsible for handling the business logic

    The deployment service code should be free of any ASGI application specific
    code and concerns and vice-versa. This allows them to be independently
    extendable and easily swappable.

    Implementations of this class must use the deployment and its settings to
    configure and run the web application (e.g. FastAPI, Flask, Falcon, Quart,
    BlackSheep, etc.) that wraps the deployment service according to the user's
    specifications, particularly concerning the following:

    * exposed endpoints (URL paths, methods, input/output models)
    * middleware (CORS, authentication, logging, etc.)
    * error handling
    * lifecycle management (startup, shutdown)
    * custom hooks (startup, shutdown)
    * app configuration (workers, host, port, thread pool size, etc.)

    The following methods must be provided by implementations of this class:

    * flavor: Return the flavor class associated with this deployment
    application runner.
    * build: Build and return an ASGI compatible web application (i.e. an
    ASGIApplication object that can be run with uvicorn). Most Python ASGI
    frameworks provide an ASGIApplication object. This method also has to
    register all the endpoints, middleware and extensions that are either
    required internally or supplied to it. It must also configure the `startup`
    and `shutdown` methods to be run as part of the ASGI application's lifespan
    or overload the `_run_asgi_app` method to handle the startup and shutdown as
    an alternative.
    * _get_dashboard_endpoints: Gets the dashboard endpoints specs from the
    deployment configuration. Only required if the dashboard files path is set
    in the deployment configuration and the app runner supports serving a
    dashboard alongside the API.
    * _build_cors_middleware: Builds the CORS middleware from the CORS settings
    in the deployment configuration.
    """

    def __init__(
        self, deployment: Union[str, UUID, "DeploymentResponse"], **kwargs: Any
    ):
        """Initialize the deployment app.

        Args:
            deployment: The deployment to run.
            **kwargs: Additional keyword arguments for the deployment app runner.
        """
        self.deployment = self.load_deployment(deployment)
        assert self.deployment.snapshot is not None
        self.snapshot = self.deployment.snapshot

        self.settings = (
            self.snapshot.pipeline_configuration.deployment_settings
        )

        self.service = self.load_deployment_service()

        # Create framework-specific adapters
        self.endpoint_adapter = self._create_endpoint_adapter()
        self.middleware_adapter = self._create_middleware_adapter()
        self._asgi_app: Optional[ASGIApplication] = None

        self.endpoints: List[EndpointSpec] = []
        self.middlewares: List[MiddlewareSpec] = []
        self.extensions: List[AppExtensionSpec] = []

    @property
    def asgi_app(self) -> ASGIApplication:
        """Get the ASGI application.

        Returns:
            The ASGI application.

        Raises:
            RuntimeError: If the ASGI application is not built yet.
        """
        if self._asgi_app is None:
            raise RuntimeError(
                "ASGI application is not built yet. Run the deployment app runner's `build` method first."
            )
        return self._asgi_app

    @classmethod
    def load_deployment(
        cls, deployment: Union[str, UUID, "DeploymentResponse"]
    ) -> DeploymentResponse:
        """Load the deployment.

        Args:
            deployment: The deployment to load.

        Returns:
            The deployment.

        Raises:
            RuntimeError: If the deployment or its snapshot cannot be loaded.
        """
        if isinstance(deployment, str):
            deployment = UUID(deployment)

        if isinstance(deployment, UUID):
            try:
                deployment = Client().zen_store.get_deployment(
                    deployment_id=deployment
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load deployment {deployment}: {e}"
                ) from e
        else:
            assert isinstance(deployment, DeploymentResponse)

        if deployment.snapshot is None:
            raise RuntimeError(f"Deployment {deployment.id} has no snapshot")

        return deployment

    @classmethod
    def load_app_runner(
        cls, deployment: Union[str, UUID, "DeploymentResponse"]
    ) -> "BaseDeploymentAppRunner":
        """Load the app runner for the deployment.

        Args:
            deployment: The deployment to load the app runner for.

        Returns:
            The app runner for the deployment.

        Raises:
            RuntimeError: If the deployment app runner cannot be loaded.
        """
        deployment = cls.load_deployment(deployment)
        assert deployment.snapshot is not None

        settings = (
            deployment.snapshot.pipeline_configuration.deployment_settings
        )

        app_runner_flavor = (
            BaseDeploymentAppRunnerFlavor.load_app_runner_flavor(settings)
        )

        app_runner_cls = app_runner_flavor.implementation_class

        logger.info(
            f"Instantiating deployment app runner class '{app_runner_cls}' for "
            f"deployment {deployment.id}"
        )

        try:
            return app_runner_cls(
                deployment, **settings.deployment_app_runner_kwargs
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to instantiate deployment app runner class "
                f"'{app_runner_cls}' for deployment {deployment.id}: {e}"
            ) from e

    def load_deployment_service(self) -> BasePipelineDeploymentService:
        """Load the service for the deployment.

        Returns:
            The deployment service for the deployment.

        Raises:
            RuntimeError: If the deployment service cannot be loaded.
        """
        settings = self.snapshot.pipeline_configuration.deployment_settings
        if settings.deployment_service_class is None:
            service_cls: Type[BasePipelineDeploymentService] = (
                PipelineDeploymentService
            )
        else:
            assert isinstance(
                settings.deployment_service_class, SourceOrObject
            )
            try:
                loaded_service_cls = settings.deployment_service_class.load()
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load deployment service from source "
                    f"{settings.deployment_service_class}: {e}\n"
                    "Please check that the source is valid and that the "
                    "deployment service class is importable from the source "
                    "root directory. Hint: run `zenml init` in your local "
                    "source directory to initialize the source root path."
                ) from e

            if not isinstance(loaded_service_cls, type) or not issubclass(
                loaded_service_cls, BasePipelineDeploymentService
            ):
                raise RuntimeError(
                    f"Deployment service class '{loaded_service_cls}' is not a "
                    "subclass of 'BasePipelineDeploymentService'"
                )
            service_cls = loaded_service_cls

        logger.info(
            f"Instantiating deployment service class '{service_cls}' for "
            f"deployment {self.deployment.id}"
        )

        try:
            return service_cls(self, **settings.deployment_service_kwargs)
        except Exception as e:
            raise RuntimeError(
                f"Failed to instantiate deployment service class "
                f"'{service_cls}' for deployment {self.deployment.id}: {e}"
            ) from e

    @property
    @abstractmethod
    def flavor(cls) -> "BaseDeploymentAppRunnerFlavor":
        """Return the flavor associated with this deployment application runner.

        Returns:
            The flavor associated with this deployment application runner.
        """

    @abstractmethod
    def _create_endpoint_adapter(self) -> EndpointAdapter:
        """Create the framework-specific endpoint adapter.

        Returns:
            Endpoint adapter instance for this framework.
        """

    @abstractmethod
    def _create_middleware_adapter(self) -> MiddlewareAdapter:
        """Create the framework-specific middleware adapter.

        Returns:
            Middleware adapter instance for this framework.
        """

    def _build_invoke_endpoint(
        self,
    ) -> Callable[
        [BaseDeploymentInvocationRequest], BaseDeploymentInvocationResponse
    ]:
        """Create the endpoint used to invoke the pipeline deployment.

        Returns:
            The invoke endpoint, built according to the pipeline deployment
            input and output specifications.
        """
        PipelineInvokeRequest, PipelineInvokeResponse = (
            self.service.get_pipeline_invoke_models()
        )

        def _invoke_endpoint(
            request: PipelineInvokeRequest,  # type: ignore[valid-type]
        ) -> PipelineInvokeResponse:  # type: ignore[valid-type]
            return self.service.execute_pipeline(request)

        return _invoke_endpoint

    def dashboard_files_path(self) -> Optional[str]:
        """Get the absolute path of the dashboard files directory.

        Returns:
            Absolute path.

        Raises:
            ValueError: If the dashboard files path is absolute.
            RuntimeError: If the dashboard files path does not exist.
        """
        # If an absolute path is provided, use it
        dashboard_files_path = self.settings.dashboard_files_path
        if not dashboard_files_path:
            import zenml

            return os.path.join(
                zenml.__path__[0], "deployers", "server", "dashboard"
            )

        if os.path.isabs(dashboard_files_path):
            raise ValueError(
                f"Dashboard files path '{dashboard_files_path}' must be "
                "relative to the source root, not absolute."
            )

        # Otherwise, assume this is a path relative to the source root
        source_root = source_utils.get_source_root()
        dashboard_path = os.path.join(source_root, dashboard_files_path)
        if not os.path.exists(dashboard_path):
            raise RuntimeError(
                f"Dashboard files path '{dashboard_path}' does not exist. "
                f"Please check that the path exists and that the source root "
                f"is set correctly. Hint: run `zenml init` in your local source "
                f"directory to initialize the source root path."
            )
        return dashboard_path

    @abstractmethod
    def _get_dashboard_endpoints(self) -> List[EndpointSpec]:
        """Get the dashboard endpoints specs.

        This is called if the dashboard files path is set to construct the
        endpoints specs for the dashboard.

        Returns:
            The dashboard endpoints specs.
        """

    def _create_default_endpoint_specs(self) -> List[EndpointSpec]:
        """Create EndpointSpec objects for default endpoints.

        Returns:
            List of endpoint specs for default endpoints.
        """
        specs = []

        if self.settings.endpoint_enabled(DeploymentDefaultEndpoints.INVOKE):
            specs.append(
                EndpointSpec(
                    path=f"{self.settings.api_url_path}{self.settings.invoke_url_path}",
                    method=EndpointMethod.POST,
                    handler=self._build_invoke_endpoint(),
                    auth_required=True,
                )
            )

        if self.settings.endpoint_enabled(DeploymentDefaultEndpoints.HEALTH):
            specs.append(
                EndpointSpec(
                    path=f"{self.settings.api_url_path}{self.settings.health_url_path}",
                    method=EndpointMethod.GET,
                    handler=self.service.health_check,
                    auth_required=False,
                )
            )

        if self.settings.endpoint_enabled(DeploymentDefaultEndpoints.INFO):
            specs.append(
                EndpointSpec(
                    path=f"{self.settings.api_url_path}{self.settings.info_url_path}",
                    method=EndpointMethod.GET,
                    handler=self.service.get_service_info,
                    auth_required=False,
                )
            )

        if self.settings.endpoint_enabled(DeploymentDefaultEndpoints.METRICS):
            specs.append(
                EndpointSpec(
                    path=f"{self.settings.api_url_path}{self.settings.metrics_url_path}",
                    method=EndpointMethod.GET,
                    handler=self.service.get_execution_metrics,
                    auth_required=False,
                )
            )

        return specs

    def _get_secure_headers(self) -> "Secure":
        """Get the secure headers settings.

        Returns:
            The secure headers settings.
        """
        import secure

        # For each of the secure headers supported by the `secure` library, we
        # check if the corresponding configuration is set in the deployment
        # configuration:
        #
        # - if set to `True`, we use the default value for the header
        # - if set to a string, we use the string as the value for the header
        # - if set to `False`, we don't set the header

        server: Optional[secure.Server] = None
        if self.settings.secure_headers.server:
            server = secure.Server()
            if isinstance(self.settings.secure_headers.server, str):
                server.set(self.settings.secure_headers.server)
            else:
                server.set(str(self.deployment.id))

        hsts: Optional[secure.StrictTransportSecurity] = None
        if self.settings.secure_headers.hsts:
            hsts = secure.StrictTransportSecurity()
            if isinstance(self.settings.secure_headers.hsts, str):
                hsts.set(self.settings.secure_headers.hsts)

        xfo: Optional[secure.XFrameOptions] = None
        if self.settings.secure_headers.xfo:
            xfo = secure.XFrameOptions()
            if isinstance(self.settings.secure_headers.xfo, str):
                xfo.set(self.settings.secure_headers.xfo)

        csp: Optional[secure.ContentSecurityPolicy] = None
        if self.settings.secure_headers.csp:
            csp = secure.ContentSecurityPolicy()
            if isinstance(self.settings.secure_headers.csp, str):
                csp.set(self.settings.secure_headers.csp)

        xcto: Optional[secure.XContentTypeOptions] = None
        if self.settings.secure_headers.content:
            xcto = secure.XContentTypeOptions()
            if isinstance(self.settings.secure_headers.content, str):
                xcto.set(self.settings.secure_headers.content)

        referrer: Optional[secure.ReferrerPolicy] = None
        if self.settings.secure_headers.referrer:
            referrer = secure.ReferrerPolicy()
            if isinstance(self.settings.secure_headers.referrer, str):
                referrer.set(self.settings.secure_headers.referrer)

        cache: Optional[secure.CacheControl] = None
        if self.settings.secure_headers.cache:
            cache = secure.CacheControl()
            if isinstance(self.settings.secure_headers.cache, str):
                cache.set(self.settings.secure_headers.cache)

        permissions: Optional[secure.PermissionsPolicy] = None
        if self.settings.secure_headers.permissions:
            permissions = secure.PermissionsPolicy()
            if isinstance(self.settings.secure_headers.permissions, str):
                # This one is special, because it doesn't allow setting the
                # value as a string, but rather as a list of directives, so we
                # hack our way around it by setting the private _default_value
                # attribute.
                permissions._default_value = (
                    self.settings.secure_headers.permissions
                )

        return secure.Secure(
            server=server,
            hsts=hsts,
            xfo=xfo,
            csp=csp,
            xcto=xcto,
            referrer=referrer,
            cache=cache,
            permissions=permissions,
        )

    def _build_secure_headers_middleware(
        self,
    ) -> MiddlewareSpec:
        """Get the secure headers middleware.

        Returns:
            The secure headers middleware spec.
        """
        secure_headers = self._get_secure_headers()

        async def set_secure_headers(
            app: ASGIApplication,
            scope: Scope,
            receive: ASGIReceiveCallable,
            send: ASGISendCallable,
        ) -> None:
            skip = False
            if scope["type"] != "http":
                skip = True
            else:
                path = scope["path"]

                if path.startswith(
                    self.settings.docs_url_path
                ) or path.startswith(self.settings.redoc_url_path):
                    skip = True

            async def send_wrapper(message: ASGISendEvent) -> None:
                if message["type"] == "http.response.start":
                    hdrs: List[Tuple[bytes, bytes]] = list(
                        message.get("headers", [])
                    )
                    existing = {k: i for i, (k, _) in enumerate(hdrs)}
                    for k, v in secure_headers.headers.items():
                        i = existing.get(k.encode())
                        if i is not None:
                            hdrs[i] = (k.encode(), v.encode())
                        else:
                            hdrs.append((k.encode(), v.encode()))
                    message["headers"] = hdrs
                await send(message)

            wrapped_app = guarantee_single_callable(app)  # type: ignore[no-untyped-call]

            await wrapped_app(scope, receive, send if skip else send_wrapper)

        return MiddlewareSpec(
            middleware=set_secure_headers,
        )

    @abstractmethod
    def _build_cors_middleware(self) -> MiddlewareSpec:
        """Get the CORS middleware.

        Returns:
            The CORS middleware spec.
        """

    def _create_default_middleware_specs(self) -> List[MiddlewareSpec]:
        """Create MiddlewareSpec objects for default middleware.

        Returns:
            List of middleware specs for default middleware.
        """
        specs = []

        if self.settings.middleware_enabled(
            DeploymentDefaultMiddleware.SECURE_HEADERS
        ):
            specs.append(self._build_secure_headers_middleware())

        if self.settings.middleware_enabled(DeploymentDefaultMiddleware.CORS):
            specs.append(self._build_cors_middleware())

        return specs

    def install_extensions(self, *extension_specs: AppExtensionSpec) -> None:
        """Install the given app extensions.

        Args:
            extension_specs: The app extensions to install.

        Raises:
            ValueError: If the extension is not a subclass of BaseAppExtension.
            RuntimeError: If the extension cannot be initialized.
        """
        for ext_spec in extension_specs:
            # Load extension
            ext_spec.load_sources()
            extension_obj = ext_spec.resolve_extension_handler()

            # Handle callable vs class-based extensions
            if isinstance(extension_obj, type):
                if not issubclass(extension_obj, BaseAppExtension):
                    raise ValueError(
                        f"Extension type {extension_obj} is not a subclass of "
                        "BaseAppExtension"
                    )

                try:
                    extension_instance = extension_obj(
                        **ext_spec.extension_kwargs
                    )
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to initialize extension class {extension_obj}: {e}"
                    ) from e

                extension_instance.install(self)
            else:
                # Simple callable extension
                extension_obj(
                    app_runner=self,
                    **ext_spec.extension_kwargs,
                )
            self.extensions.append(ext_spec)

    def register_endpoints(self, *endpoint_specs: EndpointSpec) -> None:
        """Register the given endpoints.

        Args:
            endpoint_specs: The endpoints to register.
        """
        for endpoint_spec in endpoint_specs:
            endpoint_spec.load_sources()
            self.endpoint_adapter.register_endpoint(self, endpoint_spec)
            self.endpoints.append(endpoint_spec)

    def register_middlewares(self, *middleware_specs: MiddlewareSpec) -> None:
        """Register the given middleware.

        Args:
            middleware_specs: The middleware to register.
        """
        for middleware_spec in middleware_specs:
            middleware_spec.load_sources()
            self.middleware_adapter.register_middleware(self, middleware_spec)
            self.middlewares.append(middleware_spec)

    def _run_startup_hook(self) -> None:
        """Run the startup hook.

        Raises:
            ValueError: If the startup hook is not callable.
            Exception: If the startup hook fails to execute.
        """
        if not self.settings.startup_hook:
            return

        assert isinstance(self.settings.startup_hook, SourceOrObject)
        startup_hook = self.settings.startup_hook.load()

        if not callable(startup_hook):
            raise ValueError(
                f"The startup hook object {startup_hook} must be callable"
            )

        logger.info("Executing the deployment application startup hook...")
        try:
            startup_hook(
                app_runner=self,
                **self.settings.startup_hook_kwargs,
            )
        except Exception as e:
            logger.exception(f"Failed to execute startup hook: {e}")
            raise

    def startup(self) -> None:
        """Startup the deployment app.

        Raises:
            Exception: If the service initialization fails.
        """
        logger.info("🚀 Initializing the pipeline deployment service...")

        try:
            self.service.initialize()
            logger.info(
                "✅ Pipeline deployment service initialized successfully"
            )
        except Exception as e:
            logger.error(
                f"❌ Failed to initialize the pipeline deployment service: {e}"
            )
            raise

        self._run_startup_hook()

    def _run_shutdown_hook(self) -> None:
        """Run the shutdown hook.

        Raises:
            ValueError: If the shutdown hook is not callable.
            Exception: If the shutdown hook fails to execute.
        """
        if not self.settings.shutdown_hook:
            return

        assert isinstance(self.settings.shutdown_hook, SourceOrObject)

        shutdown_hook = self.settings.shutdown_hook.load()

        if not shutdown_hook:
            return

        if not callable(shutdown_hook):
            raise ValueError(
                f"The shutdown hook object {shutdown_hook} must be callable"
            )

        logger.info("Executing the deployment application shutdown hook...")
        try:
            shutdown_hook(
                app_runner=self,
                **self.settings.shutdown_hook_kwargs,
            )
        except Exception as e:
            logger.exception(f"Failed to execute shutdown hook: {e}")
            raise

    def shutdown(self) -> None:
        """Shutdown the deployment app.

        Raises:
            Exception: If the service cleanup fails.
        """
        self._run_shutdown_hook()

        logger.info("🛑 Cleaning up the pipeline deployment service...")
        try:
            self.service.cleanup()
            logger.info(
                "✅ The pipeline deployment service was cleaned up successfully"
            )
        except Exception as e:
            logger.error(
                f"❌ Failed to clean up the pipeline deployment service: {e}"
            )
            raise

    def build_asgi_app(self) -> ASGIApplication:
        """Build the ASGI application.

        Returns:
            The ASGI application.
        """
        endpoints = self._create_default_endpoint_specs()

        custom_endpoints = (
            self.settings.custom_endpoints
            if self.settings.custom_endpoints
            else []
        )

        # Allow custom endpoints to override default endpoints when they share
        # the same path and method.

        def normalize_path(path: str) -> str:
            if path and path != "/":
                path = re.sub(r"(?<!^)/+$", "", path)

            # normalize typed path params: {name:path} -> {param:path}
            path = re.sub(r"\{[^{}:/]+:path\}", "{param:path}", path)

            # normalize untyped params: {name} -> {param}
            path = re.sub(r"\{[^{}:/]+\}", "{param}", path)

            return path

        custom_keys = {
            (e.method, normalize_path(e.path)) for e in custom_endpoints
        }
        endpoints = [
            e
            for e in endpoints
            if (e.method, normalize_path(e.path)) not in custom_keys
        ]

        endpoints.extend(custom_endpoints)

        if self.settings.endpoint_enabled(
            DeploymentDefaultEndpoints.DASHBOARD
        ):
            endpoints.extend(self._get_dashboard_endpoints())

        middlewares = self._create_default_middleware_specs()

        if self.settings.custom_middlewares:
            middlewares.extend(self.settings.custom_middlewares)

        extensions = []
        if self.settings.app_extensions:
            extensions.extend(self.settings.app_extensions)

        return self.build(middlewares, endpoints, extensions)

    def run(self) -> None:
        """Run the ASGI application via uvicorn.

        Raises:
            Exception: If the application fails to start.
        """
        import uvicorn

        settings = self.settings

        logger.info(f"""
🚀 Starting ZenML pipeline deployment application:
   Deployment ID: {self.deployment.id}
   Deployment Name: {self.deployment.name}
   Snapshot ID: {self.snapshot.id}
   Snapshot Name: {self.snapshot.name or "N/A"}
   Pipeline ID: {self.snapshot.pipeline.id}
   Pipeline Name: {self.snapshot.pipeline.name}
   Host: {settings.uvicorn_host}
   Port: {settings.uvicorn_port}
   Workers: {settings.uvicorn_workers}
   Log Level: {settings.log_level}
""")

        uvicorn_kwargs: Dict[str, Any] = dict(
            host=settings.uvicorn_host,
            port=settings.uvicorn_port,
            workers=settings.uvicorn_workers,
            log_level=settings.log_level.value,
            reload=settings.uvicorn_reload,
            access_log=True,
        )
        if settings.uvicorn_kwargs:
            uvicorn_kwargs.update(settings.uvicorn_kwargs)

        if settings.uvicorn_workers > 1 or settings.uvicorn_reload:
            # These settings require the app to run as a subprocess, so we need
            # to use the factory pattern and pass the app as a source object.
            os.environ[ZENML_DEPLOYMENT_ID_ENV_VAR] = str(self.deployment.id)

            app_source = source_utils.resolve(build_asgi_app)
            app_path = f"{app_source.module}:{app_source.attribute}"
            uvicorn_kwargs.update(dict(app=app_path, factory=True))
        else:
            # The regular path is to build the app and pass it as an object in
            # the same process.
            app = self.build_asgi_app()
            uvicorn_kwargs.update(dict(app=app))

        try:
            # Start the ASGI application
            uvicorn.run(
                **uvicorn_kwargs,
            )
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error(
                f"❌ Failed to start deployment application: {str(e)}"
            )
            raise
        logger.info("\n🛑 Deployment application shutdown")

    @abstractmethod
    def build(
        self,
        middlewares: List[MiddlewareSpec],
        endpoints: List[EndpointSpec],
        extensions: List[AppExtensionSpec],
    ) -> ASGIApplication:
        """Build the ASGI compatible web application.

        Args:
            middlewares: The middleware to register.
            endpoints: The endpoints to register.
            extensions: The extensions to install.

        Returns:
            The ASGI compatible web application.
        """


class BaseDeploymentAppRunnerFlavor(ABC):
    """Base class for deployment app runner flavors.

    BaseDeploymentAppRunner implementations must also provide implementations
    for this class. The flavor class implementation should be kept separate from
    the implementation class to allow it to be imported without importing the
    implementation class and all its dependencies.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the deployment app runner flavor.

        Returns:
            The name of the deployment app runner flavor.
        """

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseDeploymentAppRunner]:
        """The class that implements the deployment app runner.

        Returns:
            The implementation class for the deployment app runner.
        """

    @property
    def requirements(self) -> List[str]:
        """The software requirements for the deployment app runner.

        Returns:
            The software requirements for the deployment app runner.
        """
        return ["uvicorn", "secure~=1.0.1", "asgiref~=3.10.0", "Jinja2"]

    @classmethod
    def load_app_runner_flavor(
        cls, settings: DeploymentSettings
    ) -> "BaseDeploymentAppRunnerFlavor":
        """Load the app runner flavor for the deployment settings.

        Args:
            settings: The deployment settings to load the app runner flavor for.

        Returns:
            The app runner flavor for the deployment.

        Raises:
            RuntimeError: If the deployment app runner flavor cannot be loaded.
        """
        from zenml.deployers.server.fastapi import (
            FastAPIDeploymentAppRunnerFlavor,
        )

        if settings.deployment_app_runner_flavor is None:
            app_runner_flavor_class: Type[BaseDeploymentAppRunnerFlavor] = (
                FastAPIDeploymentAppRunnerFlavor
            )
        else:
            assert isinstance(
                settings.deployment_app_runner_flavor, SourceOrObject
            )
            try:
                loaded_app_runner_flavor_class = (
                    settings.deployment_app_runner_flavor.load()
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load deployment app runner flavor from source "
                    f"{settings.deployment_app_runner_flavor}: {e}\n"
                    "Please check that the source is valid and that the "
                    "deployment app runner flavor class is importable from the "
                    "source root directory. Hint: run `zenml init` in your "
                    "local source directory to initialize the source root path."
                ) from e

            if not isinstance(
                loaded_app_runner_flavor_class, type
            ) or not issubclass(
                loaded_app_runner_flavor_class, BaseDeploymentAppRunnerFlavor
            ):
                raise RuntimeError(
                    f"The object '{loaded_app_runner_flavor_class}' is not a "
                    "subclass of 'BaseDeploymentAppRunnerFlavor'"
                )

            app_runner_flavor_class = loaded_app_runner_flavor_class

        try:
            app_runner_flavor = app_runner_flavor_class()
        except Exception as e:
            raise RuntimeError(
                f"Failed to instantiate deployment app runner flavor "
                f"'{loaded_app_runner_flavor_class}': {e}"
            ) from e

        return app_runner_flavor


def build_asgi_app() -> ASGIApplication:
    """Build the ASGI application.

    This is the factory method called by uvicorn to build the ASGI
    application. It is not allowed to receive any arguments and therefore
    the deployment ID must be passed in as the ZENML_DEPLOYMENT_ID
    environment variable.

    Returns:
        The ASGI application.

    Raises:
        RuntimeError: If the deployment ID is not set in the
            ZENML_DEPLOYMENT_ID environment variable.
    """
    deployment_id = os.getenv(ZENML_DEPLOYMENT_ID_ENV_VAR)
    if not deployment_id:
        raise RuntimeError(
            f"{ZENML_DEPLOYMENT_ID_ENV_VAR} environment variable is not set"
        )

    app_runner = BaseDeploymentAppRunner.load_app_runner(deployment_id)
    return app_runner.build_asgi_app()


def start_deployment_app(
    deployment_id: UUID,
    pid_file: Optional[str] = None,
    log_file: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    reload: Optional[bool] = None,
) -> None:
    """Start the deployment app.

    Args:
        deployment_id: The deployment ID.
        pid_file: The PID file to use for the deployment.
        log_file: The log file to use for the deployment.
        host: The custom host to use for the deployment.
        port: The custom port to use for the deployment.
        reload: Whether to automatically reload the deployment when the
            code changes.
    """
    if pid_file or log_file:
        # create parent directory if necessary
        for f in (pid_file, log_file):
            if f:
                os.makedirs(os.path.dirname(f), exist_ok=True)

        setup_daemon(pid_file, log_file)

    logger.info(
        f"Starting deployment application server for deployment "
        f"{deployment_id}"
    )

    app_runner = BaseDeploymentAppRunner.load_app_runner(deployment_id)

    # Allow host/port overrides coming from the CLI.
    if host:
        app_runner.settings.uvicorn_host = host
    if port:
        app_runner.settings.uvicorn_port = int(port)
    if reload is not None:
        app_runner.settings.uvicorn_reload = reload
    app_runner.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--deployment_id",
        default=os.getenv(ZENML_DEPLOYMENT_ID_ENV_VAR),
        help="Pipeline snapshot ID",
    )
    parser.add_argument(
        "--pid_file",
        default=os.getenv("ZENML_PID_FILE"),
        help="PID file to use for the deployment",
    )
    parser.add_argument(
        "--log_file",
        default=os.getenv("ZENML_LOG_FILE"),
        help="Log file to use for the deployment",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("ZENML_UVICORN_HOST"),
        help=(
            "Optional host override for the uvicorn server. If provided, "
            "this takes precedence over the deployment settings."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=os.getenv("ZENML_UVICORN_PORT"),
        help=(
            "Optional port override for the uvicorn server. If provided, "
            "this takes precedence over the deployment settings."
        ),
    )
    parser.add_argument(
        "--reload",
        type=bool,
        default=os.getenv("ZENML_UVICORN_RELOAD"),
        help=(
            "Whether to automatically reload the deployment when the code changes."
        ),
    )
    args = parser.parse_args()

    # Activate integrations to ensure all components are available
    integration_registry.activate_integrations()

    start_deployment_app(
        deployment_id=args.deployment_id,
        pid_file=args.pid_file,
        log_file=args.log_file,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
