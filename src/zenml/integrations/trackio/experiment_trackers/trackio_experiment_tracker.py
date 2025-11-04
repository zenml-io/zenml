#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Implementation of the Trackio experiment tracker."""

from __future__ import annotations

import inspect
import os
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)
from urllib.parse import urljoin

from zenml.constants import METADATA_EXPERIMENT_TRACKER_URL
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.trackio.flavors import (
    TrackioExperimentTrackerConfig,
    TrackioExperimentTrackerSettings,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import Uri

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.metadata.metadata_types import MetadataType

logger = get_logger(__name__)


class TrackioExperimentTracker(BaseExperimentTracker):
    """Experiment tracker implementation that delegates to Trackio."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Trackio experiment tracker."""

        super().__init__(*args, **kwargs)
        self._active_run: Optional[Any] = None
        self._run_initialized = False
        self._run_url: Optional[str] = None
        self._run_identifier: Optional[str] = None

    @property
    def config(self) -> TrackioExperimentTrackerConfig:
        """Return the configuration of the experiment tracker."""

        return cast(TrackioExperimentTrackerConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Return the settings class for the experiment tracker."""

        return TrackioExperimentTrackerSettings

    @property
    def active_run(self) -> Any:
        """Return the active Trackio run.

        Returns:
            The Trackio run instance.

        Raises:
            RuntimeError: If the run is not initialized.
        """

        if not self._run_initialized or self._active_run is None:
            raise RuntimeError(
                "Trackio run is not initialized. Make sure to access the run "
                "from within a step that uses the Trackio experiment tracker."
            )
        return self._active_run

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Create and configure a Trackio run for the upcoming step."""

        settings = cast(
            TrackioExperimentTrackerSettings, self.get_settings(info)
        )
        run_name = (
            settings.run_name or f"{info.run_name}_{info.pipeline_step_name}"
        )
        tags = self._build_tags(settings.tags, info)
        metadata = settings.metadata

        run, run_url, identifier = self._start_trackio_run(
            run_name=run_name,
            tags=tags,
            metadata=metadata,
        )

        self._active_run = run
        self._run_initialized = True
        self._run_url = run_url
        self._run_identifier = identifier or run_name

    def get_step_run_metadata(
        self, info: "StepRunInfo"
    ) -> Dict[str, "MetadataType"]:
        """Return metadata generated during the step run."""

        metadata: Dict[str, "MetadataType"] = {}

        run_url = self._run_url or self._build_fallback_run_url()
        if run_url:
            metadata[METADATA_EXPERIMENT_TRACKER_URL] = Uri(run_url)

        if self._run_identifier:
            metadata["trackio_run_id"] = self._run_identifier

        return metadata

    def cleanup_step_run(self, info: "StepRunInfo", step_failed: bool) -> None:
        """Finalize the Trackio run associated with the step."""

        try:
            self._finish_run(step_failed)
        finally:
            self._active_run = None
            self._run_initialized = False
            self._run_url = None
            self._run_identifier = None

    # ---------------------------------------------------------------------
    # Helper utilities
    # ---------------------------------------------------------------------
    def _build_tags(
        self, configured_tags: Iterable[str], info: "StepRunInfo"
    ) -> List[str]:
        """Merge configured tags with contextual information."""

        tag_set = set(configured_tags)
        tag_set.update(filter(None, [info.run_name, info.pipeline.name]))
        tag_set.add(info.pipeline_step_name)
        return sorted(tag_set)

    def _start_trackio_run(
        self,
        run_name: str,
        tags: List[str],
        metadata: Dict[str, Any],
    ) -> Tuple[Any, Optional[str], Optional[str]]:
        """Start a Trackio run via the available Python API."""

        trackio_module = self._import_trackio()
        self._authenticate(trackio_module)

        init_kwargs = self._build_init_kwargs(run_name, tags, metadata)

        run = self._try_initialize_run(trackio_module, init_kwargs)
        if run is None:
            raise RuntimeError(
                "Unable to create a Trackio run. Please ensure that the "
                "Trackio package is up to date and compatible with the "
                "ZenML Trackio integration."
            )

        run_url = self._extract_run_url(run)
        identifier = self._extract_run_identifier(run)

        self._attach_tags(run, tags)
        self._log_initial_metadata(run, metadata)

        return run, run_url, identifier

    def _import_trackio(self) -> Any:
        """Import the Trackio Python package."""

        try:
            import trackio  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "The Trackio integration requires the `trackio` package to be "
                "installed. Run `zenml integration install trackio` to "
                "install the dependency."
            ) from exc

        return trackio

    def _authenticate(self, trackio_module: Any) -> None:
        """Authenticate with Trackio if an API key has been provided."""

        api_key = self.config.api_key
        if not api_key:
            return

        for attr in ("login", "authenticate", "set_token"):
            maybe_callable = getattr(trackio_module, attr, None)
            if callable(maybe_callable):
                success, _ = self._call_with_supported_kwargs(
                    maybe_callable,
                    {
                        "api_key": api_key,
                        "token": api_key,
                        "key": api_key,
                    },
                )
                if success:
                    return

        os.environ.setdefault("TRACKIO_API_KEY", api_key)

    def _build_init_kwargs(
        self,
        run_name: str,
        tags: List[str],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect potential keyword arguments for Trackio run creation."""

        kwargs: Dict[str, Any] = {
            "workspace": self.config.workspace,
            "organization": self.config.workspace,
            "project": self.config.project,
            "project_name": self.config.project,
            "base_url": self.config.base_url,
            "api_url": self.config.base_url,
            "url": self.config.base_url,
            "run_name": run_name,
            "name": run_name,
            "display_name": run_name,
            "title": run_name,
            "tags": tags,
            "tag_names": tags,
            "labels": tags,
        }

        if metadata:
            kwargs.update(
                {
                    "metadata": metadata,
                    "properties": metadata,
                    "params": metadata,
                }
            )

        return {key: value for key, value in kwargs.items() if value}

    def _try_initialize_run(
        self, trackio_module: Any, kwargs: Dict[str, Any]
    ) -> Any:
        """Try several possible Trackio APIs to initialize a run."""

        for candidate in ("init", "start_run", "start", "create_run"):
            maybe_callable = getattr(trackio_module, candidate, None)
            if callable(maybe_callable):
                success, result = self._call_with_supported_kwargs(
                    maybe_callable, kwargs
                )
                if success:
                    if result is not None:
                        return result
                    current = self._fetch_current_run(trackio_module)
                    if current is not None:
                        return current

        run_class = getattr(trackio_module, "Run", None)
        if run_class is not None:
            try:
                success, run_instance = self._call_with_supported_kwargs(
                    run_class, kwargs
                )
            except Exception:  # noqa: BLE001
                logger.debug(
                    "Failed to instantiate Trackio Run via constructor.",
                    exc_info=True,
                )
            else:
                if success and run_instance is not None:
                    starter = getattr(run_instance, "start", None)
                    if callable(starter):
                        started_success, started = (
                            self._call_with_supported_kwargs(
                                starter,
                                {
                                    "run_name": kwargs.get("run_name"),
                                    "name": kwargs.get("name"),
                                },
                            )
                        )
                        if started_success:
                            if started is not None:
                                return started
                            current = self._fetch_current_run(trackio_module)
                            if current is not None:
                                return current
                    return run_instance

        return None

    def _fetch_current_run(self, trackio_module: Any) -> Any:
        """Try to retrieve the currently active Trackio run from the module."""

        for attribute in ("get_current_run", "current_run", "active_run"):
            value = getattr(trackio_module, attribute, None)
            if callable(value):
                success, run = self._call_with_supported_kwargs(value, {})
                if success and run is not None:
                    return run
            elif value is not None:
                return value

        return None

    def _call_with_supported_kwargs(
        self, callable_obj: Any, potential_kwargs: Dict[str, Any]
    ) -> Tuple[bool, Any]:
        """Invoke a callable with the subset of supported keyword arguments."""

        try:
            signature = inspect.signature(callable_obj)
        except (TypeError, ValueError):
            signature = None

        filtered_kwargs: Dict[str, Any] = {}
        if signature is None:
            filtered_kwargs = potential_kwargs
        else:
            for name, value in potential_kwargs.items():
                if name in signature.parameters:
                    filtered_kwargs[name] = value

        try:
            result = callable_obj(**filtered_kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Failed to call %s with kwargs %s: %s",
                callable_obj,
                filtered_kwargs,
                exc,
            )
            return False, None

        return True, result

    def _extract_run_url(self, run: Any) -> Optional[str]:
        """Try to extract a URL pointing to the Trackio run."""

        for attribute in ("url", "ui_url", "dashboard_url", "app_url"):
            value = getattr(run, attribute, None)
            if isinstance(value, str) and value:
                return value

        get_url = getattr(run, "get_url", None)
        if callable(get_url):
            try:
                value = get_url()
            except TypeError:
                value = None
            if isinstance(value, str) and value:
                return value

        return None

    def _extract_run_identifier(self, run: Any) -> Optional[str]:
        """Extract a stable identifier for the run."""

        for attribute in ("id", "run_id", "name", "identifier", "slug"):
            value = getattr(run, attribute, None)
            if isinstance(value, str) and value:
                return value

        return None

    def _attach_tags(self, run: Any, tags: List[str]) -> None:
        """Attach tags to the Trackio run if the API supports it."""

        if not tags:
            return

        for attribute in ("set_tags", "add_tags", "with_tags"):
            maybe_callable = getattr(run, attribute, None)
            if callable(maybe_callable):
                success, _ = self._call_with_supported_kwargs(
                    maybe_callable, {"tags": tags, "tag_names": tags}
                )
                if success:
                    return

        add_tag = getattr(run, "add_tag", None)
        if callable(add_tag):
            for tag in tags:
                self._call_with_supported_kwargs(add_tag, {"tag": tag})

    def _log_initial_metadata(
        self, run: Any, metadata: Dict[str, Any]
    ) -> None:
        """Log static metadata right after the run is created."""

        if not metadata:
            return

        if hasattr(run, "__setitem__"):
            try:
                for key, value in metadata.items():
                    run[key] = value
                return
            except Exception:  # noqa: BLE001
                logger.debug(
                    "Falling back to explicit logging for metadata.",
                    exc_info=True,
                )

        for attribute in (
            "log",
            "log_metrics",
            "set_params",
            "update_metadata",
        ):
            maybe_callable = getattr(run, attribute, None)
            if callable(maybe_callable):
                success, _ = self._call_with_supported_kwargs(
                    maybe_callable,
                    {
                        "metrics": metadata,
                        "params": metadata,
                        "metadata": metadata,
                    },
                )
                if success:
                    return

        logger.debug("Unable to automatically log metadata to Trackio run.")

    def _build_fallback_run_url(self) -> Optional[str]:
        """Build a fallback Trackio run URL based on the configuration."""

        if not self.config.base_url or not self._run_identifier:
            return None

        path_parts = [
            part
            for part in (
                self.config.workspace,
                self.config.project,
                "runs",
                self._run_identifier,
            )
            if part
        ]

        if not path_parts:
            return None

        base = self.config.base_url.rstrip("/") + "/"
        return urljoin(base, "/".join(path_parts))

    def _finish_run(self, step_failed: bool) -> None:
        """Finish the active Trackio run."""

        if self._active_run is None:
            return

        success = not step_failed
        status_kwargs = {
            "status": "failed" if step_failed else "success",
            "state": "failed" if step_failed else "completed",
            "success": success,
            "exit_code": 1 if step_failed else 0,
        }

        for attribute in ("finish", "end", "stop", "close", "complete"):
            maybe_callable = getattr(self._active_run, attribute, None)
            if callable(maybe_callable):
                success, _ = self._call_with_supported_kwargs(
                    maybe_callable, status_kwargs
                )
                if success:
                    break
        else:
            context_exit = getattr(self._active_run, "__exit__", None)
            if callable(context_exit):
                try:
                    context_exit(None, None, None)
                except TypeError:
                    context_exit()
