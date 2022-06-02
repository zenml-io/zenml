import json
from typing import List, Set

from zenml.integrations.kubernetes.orchestrators.kubernetes_entrypoint_configuration import (
    RUN_NAME_OPTION,
    KubernetesEntrypointConfiguration,
)

RUN_NAME_OPTION = "run_name"
PIPELINE_NAME_OPTION = "pipeline_name"
IMAGE_NAME_OPTION = "image_name"
NAMESPACE_OPTION = "kubernetes_namespace"
PIPELINE_JSON_OPTION = "pipeline_json"
PIPELINE_CONFIG_OPTION = "pipeline_config"


class KubernetesOrchestratorEntrypointConfiguration:
    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all the options required for running this entrypoint."""
        options = {
            RUN_NAME_OPTION,
            PIPELINE_NAME_OPTION,
            IMAGE_NAME_OPTION,
            NAMESPACE_OPTION,
            PIPELINE_JSON_OPTION,
            PIPELINE_CONFIG_OPTION,
        }
        return options

    @classmethod
    def get_entrypoint_command(cls) -> List[str]:
        """Returns a command that runs the entrypoint module."""
        command = [
            "python",
            "-m",
            "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator_entrypoint",
        ]
        return command

    @classmethod
    def get_entrypoint_arguments(
        cls,
        run_name: str,
        pipeline_name: str,
        image_name: str,
        kubernetes_namespace: str,
        pb2_pipeline,
        sorted_steps,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with."""
        pipeline_json = ""

        def _get_args_for_step(step):
            args = KubernetesEntrypointConfiguration.get_entrypoint_arguments(
                step=step,
                pb2_pipeline=pb2_pipeline,
                **{RUN_NAME_OPTION: run_name},
            )

            # remove pipeline json to avoid sending it multiple times
            # TODO: refactor step args to separate step-specific from general
            for i, arg in enumerate(args):
                if arg == "--pipeline_json":
                    nonlocal pipeline_json
                    pipeline_json = args[i + 1]
                    del args[i : i + 2]
            return args

        step_names = [step.name for step in sorted_steps]
        step_command = (
            KubernetesEntrypointConfiguration.get_entrypoint_command()
        )
        step_args = {
            step.name: _get_args_for_step(step) for step in sorted_steps
        }
        pipeline_config = {
            "sorted_steps": step_names,
            "step_command": step_command,
            "step_args": step_args,
        }
        args = [
            f"--{RUN_NAME_OPTION}",
            run_name,
            f"--{PIPELINE_NAME_OPTION}",
            pipeline_name,
            f"--{IMAGE_NAME_OPTION}",
            image_name,
            f"--{NAMESPACE_OPTION}",
            kubernetes_namespace,
            f"--{PIPELINE_JSON_OPTION}",
            pipeline_json,
            f"--{PIPELINE_CONFIG_OPTION}",
            json.dumps(pipeline_config),
        ]
        return args
