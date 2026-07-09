#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""TRL harness whose Harbor sandbox is a ZenML Sandbox session (task B2b).

`ZenMLPipelineEnv` is a `trl.experimental.harbor.HarborEnv` subclass — the
"base agent" in TRL terms — exposing two tools for the multi-turn
pipeline-writing task: `write_pipeline` (save code to /app/pipeline.py)
and `run_pipeline` (execute it, return the traceback/output). TRL owns the
rollout loop and the policy tokens; Harbor owns task + verifier; the
sandbox every tool call executes in is a ZenML SandboxSession.

THE B2b FINDING LIVES IN `_start`: TRL hardcodes
`TrialEnvironmentConfig(type=self._environment_type)`, and Harbor's
`EnvironmentType` enum has no "zenml-sandbox" member, so the string can
never reach our bridge. But `TrialEnvironmentConfig` also has an
`import_path` field, the factory PREFERS it over `type`, and
`import_class` resolves ZenML's bridge today. The override below is a copy
of TRL's `_start` with that one field changed — the entire gap between
"ZenML Sandbox under TRL-native RL" and reality is one constructor kwarg
TRL does not expose.
"""

import tempfile
import uuid
from pathlib import Path

from trl.experimental.harbor import HarborEnv

# The vendored bridge next to this file, NOT the integration module: the
# remote pipeline image installs released zenml==0.96.1, which has the
# Sandbox API but not the unmerged harbor integration (PR #5029). The
# vendored module rides along with the example source, so the same import
# path works locally and inside the step pod.
ZENML_HARBOR_ENV_IMPORT_PATH = "zenml_sandbox_env:ZenMLSandboxEnvironment"

PIPELINE_PATH = "/app/pipeline.py"

# The sandbox image ships zenml[local]; the pipeline run inside the tool
# call gets its own throwaway store so repeated attempts don't read each
# other's runs (the verifier's scorer isolates itself the same way).
_RUN_ENV = {
    "ZENML_ANALYTICS_OPT_IN": "false",
    "AUTO_OPEN_DASHBOARD": "false",
    "ZENML_ENABLE_RICH_TRACEBACK": "false",
    "ZENML_LOGGING_VERBOSITY": "WARN",
}


class ZenMLPipelineEnv(HarborEnv):
    """Two-tool harness for the multi-turn ZenML-pipeline-writing task."""

    PROMPT_SUFFIX = (
        "\n\nYou have two tools: `write_pipeline(code)` saves your Python "
        "source to /app/pipeline.py (overwriting it), and `run_pipeline()` "
        "executes that file and returns its combined stdout+stderr, "
        "including any traceback. Write the pipeline, run it, and if it "
        "fails, fix the code and write it again — at most 3 attempts. "
        "Only the final saved file is graded; prose does not submit "
        "anything."
    )

    async def _start(self, task_dir: str) -> str:
        # Near-copy of trl.experimental.harbor.HarborEnv._start (v1.7.1).
        # ONE functional change: the environment config selects Harbor's
        # environment via import_path (-> ZenML's bridge) instead of the
        # type enum TRL exposes. The E2B COPY workaround and the
        # /home/user/input convention are dropped — our tasks have no
        # Dockerfile and no input data.
        from harbor.environments.factory import EnvironmentFactory
        from harbor.models.task.task import Task
        from harbor.models.trial.config import (
            EnvironmentConfig as TrialEnvironmentConfig,
        )
        from harbor.models.trial.paths import TrialPaths

        await self._stop()
        self._task = Task(task_dir=Path(task_dir))
        self._paths = TrialPaths(
            trial_dir=Path(tempfile.mkdtemp(prefix="harbor_trl_zenml_"))
        )
        self._env = EnvironmentFactory.create_environment_from_config(
            config=TrialEnvironmentConfig(
                import_path=ZENML_HARBOR_ENV_IMPORT_PATH
            ),
            environment_dir=self._task.paths.environment_dir,
            environment_name=self._task.short_name,
            session_id=uuid.uuid4().hex,
            trial_paths=self._paths,
            task_env_config=self._task.config.environment,
        )
        await self._env.start(force_build=False)
        await self._env.run_healthcheck()
        await self._env.exec("mkdir -p /workdir /app")
        await self._setup()
        return self._task.instruction

    def write_pipeline(self, code: str) -> str:
        """
        Save Python source as /app/pipeline.py in the sandbox, overwriting any previous version. This is the file
        that gets graded.

        Args:
            code: The full Python source of the ZenML pipeline file.

        Returns:
            A confirmation with the number of bytes written.
        """
        with tempfile.NamedTemporaryFile(
            "w", suffix=".py", delete=False
        ) as f:
            f.write(code)
            local_path = f.name
        self._run(self._env.upload_file(local_path, PIPELINE_PATH))
        Path(local_path).unlink(missing_ok=True)
        return f"Wrote {len(code)} bytes to {PIPELINE_PATH}."

    def run_pipeline(self) -> str:
        """
        Execute /app/pipeline.py in the sandbox and return its combined stdout+stderr (including any traceback).
        Use this to check your pipeline actually runs before your attempts are used up.

        Returns:
            The execution output, truncated to 8k characters.
        """
        result = self._run(
            self._env.exec(
                f"python {PIPELINE_PATH}", timeout_sec=780, env=_RUN_ENV
            )
        )
        out = (result.stdout or "") + (result.stderr or "")
        if len(out) > 8000:
            out = out[:8000] + "\n... [truncated]"
        return out or f"(empty output, rc={result.return_code})"
