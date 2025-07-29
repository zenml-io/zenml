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
"""LangFuse trace collector implementation."""

import os
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from zenml.integrations.langfuse.constants import (
    ZENML_LANGFUSE_PIPELINE_NAME,
    ZENML_LANGFUSE_TRACE_ID,
    ZENML_LANGFUSE_USER_ID,
)
from zenml.integrations.langfuse.flavors.langfuse_trace_collector_flavor import (
    LangFuseTraceCollectorConfig,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType, Uri
from zenml.trace_collectors.base_trace_collector import BaseTraceCollector
from zenml.trace_collectors.models import (
    BaseObservation,
    Event,
    Generation,
    Session,
    Span,
    Trace,
    TraceAnnotation,
    TraceUsage,
)

if TYPE_CHECKING:
    from uuid import UUID

    from langfuse import Langfuse

    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack

logger = get_logger(__name__)


class LangFuseTraceCollector(BaseTraceCollector):
    """LangFuse trace collector implementation.

    This trace collector integrates with LangFuse to collect and query traces,
    spans, and sessions from LLM applications. It provides a unified interface
    to retrieve observability data for monitoring and debugging purposes.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the LangFuse trace collector.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self._client: Optional["Langfuse"] = None

    @property
    def config(self) -> LangFuseTraceCollectorConfig:
        """Returns the LangFuse trace collector configuration.

        Returns:
            The configuration.
        """
        return cast(LangFuseTraceCollectorConfig, self._config)

    @property
    def client(self) -> "Langfuse":
        """Get or create the LangFuse client.

        Returns:
            The LangFuse client instance.
        """
        if self._client is None:
            try:
                from langfuse import Langfuse
            except ImportError as e:
                raise ImportError(
                    "LangFuse is not installed. Please install it with "
                    "`pip install langfuse>=2.0.0`"
                ) from e

            client_kwargs = {
                "host": self.config.host,
                "public_key": self.config.public_key,
                "secret_key": self.config.secret_key,
                "debug": self.config.debug,
                "enabled": self.config.enabled,
            }

            # if self.config.project_id:
            #     client_kwargs["project_id"] = self.config.project_id

            self._client = Langfuse(**client_kwargs)
        return self._client

    def prepare_pipeline_deployment(
        self, deployment: "PipelineDeploymentResponse", stack: "Stack"
    ) -> None:
        """Initializes pipeline-level trace if enabled.

        This method is called before pipeline deployment to set up the
        pipeline-level trace context that steps will use.

        Args:
            deployment: The pipeline deployment being prepared.
            stack: The stack being used for deployment.
        """
        if not self.config.enabled or self.config.trace_per_step:
            return

        try:
            # Generate pipeline trace name and use deployment ID as trace ID
            pipeline_name = deployment.pipeline_configuration.name
            run_id = str(deployment.id)[
                :8
            ]  # Use first 8 chars of deployment ID for name
            trace_name = f"{pipeline_name}_{run_id}"

            # TODO: We use deployment.id as trace_id, but ideally we'd use the pipeline run ID.
            # The challenge is that prepare_pipeline_deployment() is called before the actual
            # pipeline run is created, so we don't have access to the run ID yet.
            # This means multiple runs of the same deployment will share the same trace ID,
            # which is not ideal for tracing individual pipeline executions.
            trace_id = str(deployment.id)

            # Get user ID from deployment if available
            user_id = str(deployment.user.id) if deployment.user else "unknown"

            # Set environment variables for context propagation
            os.environ[ZENML_LANGFUSE_PIPELINE_NAME] = pipeline_name
            os.environ[ZENML_LANGFUSE_TRACE_ID] = (
                trace_id  # Store the actual trace ID
            )
            os.environ[ZENML_LANGFUSE_USER_ID] = user_id

            # Generate a deterministic trace ID based on deployment ID
            import hashlib

            trace_hash = hashlib.md5(trace_id.encode()).hexdigest()
            langfuse_trace_id = (
                trace_hash  # Use MD5 hash as 32-char hex trace ID
            )

            # Create the trace using Langfuse client with custom ID
            self.client.trace(
                id=langfuse_trace_id,
                name=trace_name,
                user_id=user_id,
                tags=["zenml", "pipeline"],
                metadata={
                    "pipeline_name": pipeline_name,
                    "deployment_id": str(deployment.id),
                    "stack_name": stack.name,
                },
            )

            # Configure langfuse context for pipeline-level tracing
            from langfuse.decorators import langfuse_context

            langfuse_context.configure(
                secret_key=self.config.secret_key,
                public_key=self.config.public_key,
                host=self.config.host,
                enabled=self.config.enabled,
            )

            # Store the actual Langfuse trace ID for URL generation
            os.environ[ZENML_LANGFUSE_TRACE_ID] = langfuse_trace_id

            logger.debug(
                f"Pipeline-level trace initialized: {trace_name} (ID: {langfuse_trace_id})"
            )

        except Exception as e:
            logger.warning(
                f"Failed to initialize pipeline-level trace: {e}. "
                "Steps will create individual traces as fallback."
            )

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Sets up automatic Langfuse tracing for the step execution.

        This method is called before the step runs and configures the global
        Langfuse context to enable automatic tracing of LLM calls and other
        operations during step execution.

        Args:
            info: Information about the step that will be executed.
        """
        if not self.config.enabled:
            return

        try:
            from langfuse.decorators import langfuse_context
        except ImportError:
            logger.warning(
                "Langfuse decorators not available. Automatic tracing will be "
                "disabled. Please install langfuse>=2.0.0 for full functionality."
            )
            return

        try:
            # Set environment variables for LiteLLM and other integrations
            os.environ["LANGFUSE_PUBLIC_KEY"] = self.config.public_key
            os.environ["LANGFUSE_SECRET_KEY"] = self.config.secret_key
            os.environ["LANGFUSE_HOST"] = self.config.host
            if not self.config.enabled:
                os.environ["LANGFUSE_ENABLED"] = "false"
            
            # Get pipeline trace ID to set for LiteLLM
            pipeline_trace_id = os.environ.get(ZENML_LANGFUSE_TRACE_ID)
            if pipeline_trace_id:
                # Set the trace ID that LiteLLM should use
                os.environ["LANGFUSE_TRACE_ID"] = pipeline_trace_id
                logger.debug(f"Set LANGFUSE_TRACE_ID environment variable to: {pipeline_trace_id}")

            # Configure the global langfuse context with credentials
            langfuse_context.configure(
                secret_key=self.config.secret_key,
                public_key=self.config.public_key,
                host=self.config.host,
                enabled=self.config.enabled,
            )

            # Handle step-level tracing logic
            self._setup_step_tracing(info, langfuse_context)

            logger.info(
                f"Langfuse tracing enabled for step '{info.config.name}'"
            )
        except Exception as e:
            logger.warning(
                f"Failed to set up Langfuse tracing for step "
                f"'{info.config.name}': {e}. Step will execute without tracing."
            )

    def _setup_step_tracing(
        self, info: "StepRunInfo", langfuse_context: Any
    ) -> None:
        """Sets up step-level tracing based on configuration and context.

        Args:
            info: Information about the step that will be executed.
            langfuse_context: The langfuse context object.
        """
        step_name = info.config.name

        # Get environment variables set by pipeline-level trace
        pipeline_trace_id = os.environ.get(ZENML_LANGFUSE_TRACE_ID)
        pipeline_name = os.environ.get(ZENML_LANGFUSE_PIPELINE_NAME)
        user_id = os.environ.get(ZENML_LANGFUSE_USER_ID, "unknown")

        if self.config.trace_per_step or not pipeline_trace_id:
            # Create separate trace for this step (fallback or configured)
            trace_name = (
                f"{pipeline_name}_{step_name}" if pipeline_name else step_name
            )

            langfuse_context.update_current_trace(
                name=trace_name,
                user_id=user_id,
                tags=["zenml", "step"],
                metadata={
                    "step_name": step_name,
                    "pipeline_name": pipeline_name or "unknown",
                },
            )

            if not pipeline_trace_id:
                logger.debug(
                    f"Created fallback trace for step '{step_name}' "
                    "(pipeline trace not available)"
                )
        else:
            # Set up context to use the existing pipeline trace
            # Set environment variables that the completion will use to attach to existing trace
            os.environ["LANGFUSE_TRACE_ID"] = pipeline_trace_id

            # Update current trace context to the existing trace
            langfuse_context.update_current_trace(
                name=step_name,
                metadata={
                    "step_name": step_name,
                    "pipeline_name": pipeline_name,
                    "user_id": user_id,
                },
            )

            logger.debug(
                f"Set trace context to existing trace: {pipeline_trace_id}"
            )

    def cleanup_step_run(self, info: "StepRunInfo", step_failed: bool) -> None:
        """Cleans up Langfuse tracing resources after step execution.

        This method is called after the step completes (successfully or with
        failure) to ensure traces are flushed and resources are cleaned up.

        Args:
            info: Information about the step that was executed.
            step_failed: Whether the step execution failed.
        """
        if not self.config.enabled:
            return

        try:
            # Flush any pending traces to ensure they are sent to Langfuse
            if self._client:
                self._client.flush()

            logger.debug(
                f"Langfuse tracing cleaned up for step '{info.config.name}'"
            )
        except Exception as e:
            logger.warning(
                f"Error during Langfuse tracing cleanup for step "
                f"'{info.config.name}': {e}"
            )

    def _convert_langfuse_trace_to_trace(self, langfuse_trace: Any) -> Trace:
        """Convert a LangFuse trace object to zenml trace model.

        Args:
            langfuse_trace: The LangFuse trace object.

        Returns:
            Converted trace object.
        """
        # Convert usage information if available
        usage = None
        if hasattr(langfuse_trace, "usage") and langfuse_trace.usage:
            usage_data = langfuse_trace.usage
            usage = TraceUsage(
                input_tokens=getattr(usage_data, "input", None),
                output_tokens=getattr(usage_data, "output", None),
                total_tokens=getattr(usage_data, "total", None),
                input_cost=getattr(usage_data, "input_cost", None),
                output_cost=getattr(usage_data, "output_cost", None),
                total_cost=getattr(usage_data, "total_cost", None),
            )

        # Get observations (spans, generations, events)
        observations = []
        if hasattr(langfuse_trace, "observations"):
            for obs in langfuse_trace.observations:
                converted_obs = self._convert_langfuse_observation(obs)
                if converted_obs:
                    observations.append(converted_obs)

        # Convert scores to annotations
        annotations = []
        if hasattr(langfuse_trace, "scores"):
            for score in langfuse_trace.scores:
                annotation = TraceAnnotation(
                    id=getattr(score, "id", str(score)),
                    name=getattr(score, "name", "score"),
                    value=getattr(score, "value", score),
                    comment=getattr(score, "comment", None),
                    created_at=getattr(score, "created_at", datetime.now()),
                    updated_at=getattr(score, "updated_at", None),
                )
                annotations.append(annotation)

        return Trace(
            id=langfuse_trace.id,
            name=getattr(langfuse_trace, "name", None),
            start_time=langfuse_trace.timestamp,
            end_time=getattr(langfuse_trace, "end_time", None),
            metadata=getattr(langfuse_trace, "metadata", {}),
            input=getattr(langfuse_trace, "input", None),
            output=getattr(langfuse_trace, "output", None),
            tags=getattr(langfuse_trace, "tags", []),
            level=getattr(langfuse_trace, "level", None),
            status_message=getattr(langfuse_trace, "status_message", None),
            version=getattr(langfuse_trace, "version", None),
            created_at=langfuse_trace.timestamp,
            updated_at=getattr(langfuse_trace, "updated_at", None),
            user_id=getattr(langfuse_trace, "user_id", None),
            session_id=getattr(langfuse_trace, "session_id", None),
            release=getattr(langfuse_trace, "release", None),
            external_id=getattr(langfuse_trace, "external_id", None),
            public=getattr(langfuse_trace, "public", False),
            bookmarked=getattr(langfuse_trace, "bookmarked", False),
            usage=usage,
            observations=observations,
            annotations=annotations,
        )

    def _convert_langfuse_observation(
        self, obs: Any
    ) -> Optional[BaseObservation]:
        """Convert a LangFuse observation to zenml observation models.

        Args:
            obs: The LangFuse observation object.

        Returns:
            Converted observation object or None if conversion fails.
        """
        obs_type = getattr(obs, "type", None)

        base_fields = {
            "id": obs.id,
            "name": getattr(obs, "name", None),
            "start_time": obs.start_time or datetime.now(),
            "end_time": getattr(obs, "end_time", None),
            "metadata": getattr(obs, "metadata", {}),
            "input": getattr(obs, "input", None),
            "output": getattr(obs, "output", None),
            "tags": getattr(obs, "tags", []),
            "level": getattr(obs, "level", None),
            "status_message": getattr(obs, "status_message", None),
            "version": getattr(obs, "version", None),
            "created_at": getattr(obs, "created_at", datetime.now()),
            "updated_at": getattr(obs, "updated_at", None),
        }

        trace_id = getattr(obs, "trace_id", "")
        parent_id = getattr(obs, "parent_observation_id", None)

        if obs_type == "SPAN":
            usage = None
            if hasattr(obs, "usage") and obs.usage:
                usage_data = obs.usage
                usage = TraceUsage(
                    input_tokens=getattr(usage_data, "input", None),
                    output_tokens=getattr(usage_data, "output", None),
                    total_tokens=getattr(usage_data, "total", None),
                    input_cost=getattr(usage_data, "input_cost", None),
                    output_cost=getattr(usage_data, "output_cost", None),
                    total_cost=getattr(usage_data, "total_cost", None),
                )

            return Span(
                trace_id=trace_id,
                parent_observation_id=parent_id,
                usage=usage,
                **base_fields,
            )

        elif obs_type == "GENERATION":
            usage = None
            if hasattr(obs, "usage") and obs.usage:
                usage_data = obs.usage
                usage = TraceUsage(
                    input_tokens=getattr(usage_data, "input", None),
                    output_tokens=getattr(usage_data, "output", None),
                    total_tokens=getattr(usage_data, "total", None),
                    input_cost=getattr(usage_data, "input_cost", None),
                    output_cost=getattr(usage_data, "output_cost", None),
                    total_cost=getattr(usage_data, "total_cost", None),
                )

            return Generation(
                trace_id=trace_id,
                parent_observation_id=parent_id,
                model=getattr(obs, "model", None),
                model_parameters=getattr(obs, "model_parameters", {}),
                usage=usage,
                prompt_tokens=getattr(obs, "prompt_tokens", None),
                completion_tokens=getattr(obs, "completion_tokens", None),
                **base_fields,
            )

        elif obs_type == "EVENT":
            return Event(
                trace_id=trace_id,
                parent_observation_id=parent_id,
                **base_fields,
            )

        logger.warning(f"Unknown observation type: {obs_type}")
        return None

    def get_session(self, session_id: str) -> List[Trace]:
        """Get all traces for a session.

        Args:
            session_id: The session ID to retrieve traces for.

        Returns:
            List of traces belonging to the session.
        """
        try:
            traces_response = self.client.api.trace.list(session_id=session_id)
            traces = []

            for trace_data in traces_response.data:
                # Get full trace with observations
                full_trace = self.client.api.trace.get(trace_data.id)
                trace = self._convert_langfuse_trace_to_trace(full_trace)
                traces.append(trace)

            return traces

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise

    def get_trace(self, trace_id: str) -> Trace:
        """Get a single trace by ID.

        Args:
            trace_id: The trace ID to retrieve.

        Returns:
            The trace with complete information including latency, cost,
            metadata, and annotations.
        """
        try:
            langfuse_trace = self.client.api.trace.get(trace_id)
            return self._convert_langfuse_trace_to_trace(langfuse_trace)

        except Exception as e:
            logger.error(f"Failed to get trace {trace_id}: {e}")
            raise

    def get_traces(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        name: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Trace]:
        """Get traces with optional filtering.

        Args:
            start_time: Filter traces created after this timestamp.
            end_time: Filter traces created before this timestamp.
            session_id: Filter by session ID.
            user_id: Filter by user ID.
            tags: Filter by tags (traces must have all specified tags).
            name: Filter by trace name.
            limit: Maximum number of traces to return.
            offset: Number of traces to skip for pagination.
            **kwargs: Additional provider-specific filter parameters.

        Returns:
            List of traces matching the filters.
        """
        try:
            # Build filter parameters
            filter_params = {}

            if start_time:
                filter_params["from_timestamp"] = start_time
            if end_time:
                filter_params["to_timestamp"] = end_time
            if session_id:
                filter_params["session_id"] = session_id
            if user_id:
                filter_params["user_id"] = user_id
            if name:
                filter_params["name"] = name
            if tags:
                filter_params["tags"] = tags
            if limit:
                filter_params["limit"] = limit
            if offset:
                filter_params["page"] = offset // (limit or 50) + 1

            # Add any additional kwargs
            filter_params.update(kwargs)

            traces_response = self.client.api.trace.list(**filter_params)
            traces = []

            for trace_data in traces_response.data:
                # Get full trace with observations
                full_trace = self.client.api.trace.get(trace_data.id)
                trace = self._convert_langfuse_trace_to_trace(full_trace)
                traces.append(trace)

            return traces

        except Exception as e:
            logger.error(f"Failed to get traces: {e}")
            raise

    def get_span(self, span_id: str) -> Span:
        """Get a single span by ID.

        Args:
            span_id: The span ID to retrieve.

        Returns:
            The span with complete information.
        """
        try:
            observation = self.client.api.observations.get(span_id)
            converted = self._convert_langfuse_observation(observation)

            if not isinstance(converted, Span):
                raise ValueError(f"Observation {span_id} is not a span")

            return converted

        except Exception as e:
            logger.error(f"Failed to get span {span_id}: {e}")
            raise

    def add_annotations(
        self,
        trace_id: str,
        annotations: List[TraceAnnotation],
    ) -> None:
        """Add annotations to a trace.

        Args:
            trace_id: The trace ID to add annotations to.
            annotations: List of annotations to add.
        """
        try:
            for annotation in annotations:
                self.client.score(
                    trace_id=trace_id,
                    name=annotation.name,
                    value=annotation.value,
                    comment=annotation.comment,
                )

        except Exception as e:
            logger.error(f"Failed to add annotations to trace {trace_id}: {e}")
            raise

    def log_metadata(
        self,
        trace_id: str,
        metadata: Dict[str, Any],
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Add metadata and tags to a trace.

        Args:
            trace_id: The trace ID to add metadata to.
            metadata: Dictionary of metadata to add.
            tags: List of tags to add.
            **kwargs: Additional provider-specific parameters.
        """
        raise NotImplementedError

    def get_sessions(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Session]:
        """Get sessions with optional filtering.

        Args:
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip for pagination.
            **kwargs: Additional provider-specific filter parameters.

        Returns:
            List of sessions matching the filters.
        """
        try:
            filter_params = {}
            if limit:
                filter_params["limit"] = limit
            if offset:
                filter_params["page"] = offset // (limit or 50) + 1

            # Add any additional kwargs
            filter_params.update(kwargs)

            sessions_response = self.client.api.sessions.list(**filter_params)
            sessions = []

            for session_data in sessions_response.data:
                session = Session(
                    id=session_data.id,
                    created_at=session_data.created_at,
                    updated_at=getattr(session_data, "updated_at", None),
                    public=getattr(session_data, "public", False),
                    bookmarked=getattr(session_data, "bookmarked", False),
                    trace_count_total=getattr(
                        session_data, "trace_count_total", 0
                    ),
                    user_count_total=getattr(
                        session_data, "user_count_total", 0
                    ),
                )
                sessions.append(session)

            return sessions

        except Exception as e:
            logger.error(f"Failed to get sessions: {e}")
            raise

    def search_traces(
        self,
        query: str,
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Trace]:
        """Search traces by text query.

        Args:
            query: Text to search for in trace content.
            limit: Maximum number of traces to return.
            **kwargs: Additional provider-specific search parameters.

        Returns:
            List of traces matching the search query.
        """
        try:
            # LangFuse may support text search - this is a placeholder implementation
            # that uses the name filter as a basic search
            return self.get_traces(name=query, limit=limit, **kwargs)

        except Exception as e:
            logger.error(f"Failed to search traces with query '{query}': {e}")
            raise

    def _get_project_id(self) -> Optional[str]:
        """Get the project ID for URL generation.

        Returns:
            The project ID if available, None otherwise.
        """
        # If project_id is explicitly configured, use it
        if self.config.project_id:
            return self.config.project_id

        # Try to discover project ID by fetching a trace and extracting it
        try:
            # Get recent traces to extract project ID
            traces_response = self.client.api.trace.list(limit=1)
            if traces_response.data:
                # Extract project ID from the first trace
                first_trace = traces_response.data[0]
                if hasattr(first_trace, "project_id"):
                    return first_trace.project_id
                elif hasattr(first_trace, "projectId"):
                    return first_trace.projectId
        except Exception as e:
            logger.debug(f"Could not determine project ID: {e}")

        return None

    def _get_langfuse_trace_url(self, trace_id: str) -> str:
        """Generate a Langfuse trace URL.

        Args:
            trace_id: The trace ID to generate a URL for.

        Returns:
            The full URL to view the trace in Langfuse.
        """
        # Extract base URL from host (remove trailing slashes)
        base_url = self.config.host.rstrip("/")

        # Try to get project ID
        project_id = self._get_project_id()

        if project_id:
            # Langfuse trace URL format: https://host/project/PROJECT_ID/traces/TRACE_ID
            return f"{base_url}/project/{project_id}/traces/{trace_id}"
        else:
            # Fallback to generic trace view (may not work but best effort)
            logger.warning(
                f"Could not determine project ID for trace URL generation. "
                f"Using fallback URL format."
            )
            return f"{base_url}/traces/{trace_id}"

    def get_pipeline_run_metadata(
        self, run_id: "UUID"
    ) -> Dict[str, "MetadataType"]:
        """Get pipeline-specific metadata including the Langfuse trace URL.

        Args:
            run_id: The ID of the pipeline run.

        Returns:
            A dictionary of metadata including the trace URL.
        """
        if not self.config.enabled:
            return {}

        metadata: Dict[str, Any] = {}

        try:
            # Get the pipeline trace ID from environment variables
            pipeline_trace_id = os.environ.get(ZENML_LANGFUSE_TRACE_ID)

            if pipeline_trace_id:
                # Generate the Langfuse trace URL
                trace_url = self._get_langfuse_trace_url(pipeline_trace_id)
                metadata["langfuse_trace_url"] = Uri(trace_url)
                metadata["langfuse_trace_id"] = pipeline_trace_id

                logger.debug(f"Pipeline run metadata: trace URL {trace_url}")
            else:
                logger.debug(
                    "No pipeline trace ID found for metadata generation"
                )

        except Exception as e:
            logger.warning(f"Failed to generate pipeline run metadata: {e}")

        return metadata
