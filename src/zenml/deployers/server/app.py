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

import importlib
import os
from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)
from uuid import UUID

import secure
from asgiref.compatibility import guarantee_single_callable
from asgiref.typing import (
    ASGIApplication,
    ASGIReceiveCallable,
    ASGISendCallable,
    ASGISendEvent,
    HTTPScope,
    Scope,
)

from zenml.client import Client
from zenml.config.deployment_settings import (
    AppExtensionSpec,
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

logger = get_logger(__name__)


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
    * _get_cors_middleware: Builds the CORS middleware from the CORS settings
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
            RuntimeError: If the dashboard files path cannot be loaded.
        """
        # If an absolute path is provided, use it
        dashboard_files_path = self.settings.dashboard_files_path
        if not dashboard_files_path:
            return None
        if os.path.isabs(dashboard_files_path):
            return dashboard_files_path

        # Otherwise, assume this is a Python source path and load the module
        try:
            module = importlib.import_module(dashboard_files_path)
        except Exception as e:
            raise RuntimeError(
                f"Failed to import dashboard files module {dashboard_files_path}: {e}"
            ) from e

        return module.__path__[0]

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

        specs.append(
            EndpointSpec(
                path=f"{self.settings.api_url_path}{self.settings.invoke_url_path}",
                method=EndpointMethod.POST,
                handler=self._build_invoke_endpoint(),
                auth_required=True,
            )
        )

        specs.append(
            EndpointSpec(
                path=f"{self.settings.api_url_path}{self.settings.health_url_path}",
                method=EndpointMethod.GET,
                handler=self.service.health_check,
                auth_required=False,
            )
        )

        specs.append(
            EndpointSpec(
                path=f"{self.settings.api_url_path}{self.settings.info_url_path}",
                method=EndpointMethod.GET,
                handler=self.service.get_service_info,
                auth_required=False,
            )
        )

        specs.append(
            EndpointSpec(
                path=f"{self.settings.api_url_path}{self.settings.metrics_url_path}",
                method=EndpointMethod.GET,
                handler=self.service.get_execution_metrics,
                auth_required=False,
            )
        )

        if self.settings.dashboard_files_path:
            specs.extend(self._get_dashboard_endpoints())

        return specs

    def _get_secure_headers(self) -> secure.Secure:
        """Get the secure headers settings.

        Returns:
            The secure headers settings.
        """
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
                scope = cast(HTTPScope, scope)
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
    def _get_cors_middleware(self) -> MiddlewareSpec:
        """Get the CORS middleware.

        Returns:
            The CORS middleware.
        """

    def _create_default_middleware_specs(self) -> List[MiddlewareSpec]:
        """Create MiddlewareSpec objects for default middleware.

        Returns:
            List of middleware specs for default middleware.
        """
        specs = []

        specs.append(self._build_secure_headers_middleware())

        specs.append(self._get_cors_middleware())

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

    def register_endpoints(self, *endpoint_specs: EndpointSpec) -> None:
        """Register the given endpoints.

        Args:
            endpoint_specs: The endpoints to register.
        """
        for endpoint_spec in endpoint_specs:
            endpoint_spec.load_sources()
            self.endpoint_adapter.register_endpoint(self, endpoint_spec)

    def register_middlewares(self, *middleware_specs: MiddlewareSpec) -> None:
        """Register the given middleware.

        Args:
            middleware_specs: The middleware to register.
        """
        for middleware_spec in middleware_specs:
            middleware_spec.load_sources()
            self.middleware_adapter.register_middleware(self, middleware_spec)

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

    def _build_asgi_app(self) -> ASGIApplication:
        """Build the ASGI application.

        Returns:
            The ASGI application.
        """
        endpoints = []

        if self.settings.include_default_endpoints:
            endpoints.extend(self._create_default_endpoint_specs())

        if self.settings.custom_endpoints:
            endpoints.extend(self.settings.custom_endpoints)

        middlewares = []
        if self.settings.include_default_middleware:
            middlewares.extend(self._create_default_middleware_specs())

        if self.settings.custom_middlewares:
            middlewares.extend(self.settings.custom_middlewares)

        extensions = []
        if self.settings.app_extensions:
            extensions.extend(self.settings.app_extensions)

        return self.build(middlewares, endpoints, extensions)

    def _run_asgi_app(self, asgi_app: ASGIApplication) -> None:
        """Run the ASGI application.

        Args:
            asgi_app: The ASGI application to run.

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
            access_log=True,
        )
        if settings.uvicorn_kwargs:
            uvicorn_kwargs.update(settings.uvicorn_kwargs)

        try:
            # Start the ASGI application
            uvicorn.run(
                asgi_app,
                **uvicorn_kwargs,
            )
        except KeyboardInterrupt:
            logger.info("\n🛑 Deployment application shutdown")
        except Exception as e:
            logger.error(
                f"❌ Failed to start deployment application: {str(e)}"
            )
            raise

    def run(self) -> None:
        """Run the deployment app."""
        if self._asgi_app is None:
            self._build_asgi_app()

        self._run_asgi_app(self.asgi_app)

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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--deployment_id",
        default=os.getenv("ZENML_DEPLOYMENT_ID"),
        help="Pipeline snapshot ID",
    )
    args = parser.parse_args()

    logger.info(
        f"Starting deployment application server for deployment "
        f"{args.deployment_id}"
    )

    # Activate integrations to ensure all components are available
    integration_registry.activate_integrations()

    app_runner = BaseDeploymentAppRunner.load_app_runner(args.deployment_id)
    app_runner.run()
