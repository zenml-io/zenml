import datetime
import glob
import os
from typing import Any, Dict, Optional

import airflow
from airflow.providers.docker.operators.docker import DockerOperator

from zenml.config.pipeline_deployment import PipelineDeployment
from zenml.constants import (
    ENV_ZENML_LOCAL_STORES_PATH,
    ORCHESTRATOR_DOCKER_IMAGE_KEY,
)
from zenml.integrations.airflow.flavors.airflow_orchestrator_flavor import (
    ENV_AIRFLOW_RUN_NAME,
    REQUIRES_LOCAL_STORES,
    AirflowEntrypointConfiguration,
    AirflowOrchestratorFlavor,
    AirflowOrchestratorSettings,
)
from zenml.pipelines import Schedule
from zenml.utils import settings_utils, yaml_utils


def _translate_schedule(
    schedule: Optional[Schedule] = None,
) -> Dict[str, Any]:
    """Convert ZenML schedule into Airflow schedule.

    The Airflow schedule uses slightly different naming and needs some
    default entries for execution without a schedule.

    Args:
        schedule: Containing the interval, start and end date and
            a boolean flag that defines if past runs should be caught up
            on

    Returns:
        Airflow configuration dict.
    """
    if schedule:
        if schedule.cron_expression:
            start_time = schedule.start_time or (
                datetime.datetime.now() - datetime.timedelta(7)
            )
            return {
                "schedule_interval": schedule.cron_expression,
                "start_date": start_time,
                "end_date": schedule.end_time,
                "catchup": schedule.catchup,
            }
        else:
            return {
                "schedule_interval": schedule.interval_second,
                "start_date": schedule.start_time,
                "end_date": schedule.end_time,
                "catchup": schedule.catchup,
            }

    return {
        "schedule_interval": "@once",
        # set the a start time in the past and disable catchup so airflow runs the dag immediately
        "start_date": datetime.datetime.now() - datetime.timedelta(7),
        "catchup": False,
    }


dag_configs_pattern = os.path.join(os.path.dirname(__file__), "zenml", "*.yaml")
for dag_config_file in glob.glob(dag_configs_pattern):
    deployment_dict = yaml_utils.read_yaml(dag_config_file)
    deployment = PipelineDeployment.parse_obj(deployment_dict)

    settings_key = settings_utils.get_flavor_setting_key(
        AirflowOrchestratorFlavor
    )
    potential_settings = deployment.pipeline.settings.get(settings_key)
    if potential_settings:
        settings = AirflowOrchestratorSettings.parse_obj(potential_settings)
        tags = settings.tags
        # TODO
        # operator = settings.operator
    else:
        tags = []
    operator = DockerOperator

    airflow_schedule = _translate_schedule(schedule=deployment.schedule)
    dag = airflow.DAG(
        dag_id=deployment.pipeline.name,
        is_paused_upon_creation=False,
        tags=tags,
        **airflow_schedule
    )

    image_name = deployment.pipeline.extra[ORCHESTRATOR_DOCKER_IMAGE_KEY]
    step_name_to_airflow_operator = {}
    base_command = AirflowEntrypointConfiguration.get_entrypoint_command()

    mounts = []
    environment = {ENV_AIRFLOW_RUN_NAME: "{{run_id}}"}

    requires_local_mounts = deployment.pipeline.extra.get(
        REQUIRES_LOCAL_STORES, False
    )
    if requires_local_mounts:
        from docker.types import Mount

        from zenml.config.global_config import GlobalConfiguration

        local_stores_path = os.path.expanduser(
            GlobalConfiguration().local_stores_path
        )

        environment[ENV_ZENML_LOCAL_STORES_PATH] = local_stores_path
        mounts = [
            Mount(
                target=local_stores_path, source=local_stores_path, type="bind"
            )
        ]

    for step_name, step in deployment.steps.items():
        arguments = AirflowEntrypointConfiguration.get_entrypoint_arguments(
            step_name=step_name
        )

        operator = DockerOperator(
            dag=dag,
            task_id=step_name,
            image=image_name,
            command=base_command + arguments,
            mounts=mounts,
            environment=environment,
        )

        step_name_to_airflow_operator[step.config.name] = operator
        for upstream_step in step.spec.upstream_steps:
            operator.set_upstream(step_name_to_airflow_operator[upstream_step])

    globals()[deployment.pipeline.name] = dag
