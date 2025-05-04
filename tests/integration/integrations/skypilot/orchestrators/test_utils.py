"""Tests for Skypilot utility functions."""

from unittest.mock import patch

from zenml.integrations.skypilot.flavors.skypilot_orchestrator_base_vm_config import (
    SkypilotBaseOrchestratorSettings,
)
from zenml.integrations.skypilot.utils import (
    create_docker_run_command,
    prepare_docker_setup,
    prepare_launch_kwargs,
    prepare_resources_kwargs,
    prepare_task_kwargs,
    sanitize_cluster_name,
)


def test_sanitize_cluster_name():
    """Test the sanitize_cluster_name function."""
    # Test with valid input
    assert sanitize_cluster_name("test-cluster") == "test-cluster"

    # Test with uppercase
    assert sanitize_cluster_name("Test-Cluster") == "test-cluster"

    # Test with special characters
    assert (
        sanitize_cluster_name("test!@#$%^&*()cluster")
        == "test----------cluster"
    )

    # Test with leading/trailing hyphens
    assert sanitize_cluster_name("---test-cluster---") == "test-cluster"


def test_prepare_docker_setup():
    """Test the prepare_docker_setup function."""
    # Test with credentials and sudo
    setup, envs = prepare_docker_setup(
        container_registry_uri="registry.example.com",
        credentials=("username", "password"),
        use_sudo=True,
    )
    assert "sudo docker login" in setup
    assert "registry.example.com" in setup
    assert envs["DOCKER_USERNAME"] == "username"
    assert envs["DOCKER_PASSWORD"] == "password"

    # Test with credentials and no sudo
    setup, envs = prepare_docker_setup(
        container_registry_uri="registry.example.com",
        credentials=("username", "password"),
        use_sudo=False,
    )
    assert "docker login" in setup
    assert "sudo" not in setup
    assert "registry.example.com" in setup

    # Test without credentials
    setup, envs = prepare_docker_setup(
        container_registry_uri="registry.example.com",
    )
    assert setup is None
    assert envs == {}


def test_create_docker_run_command():
    """Test the create_docker_run_command function."""
    # Test with sudo
    command = create_docker_run_command(
        image="test-image:latest",
        entrypoint_str="python -m app",
        arguments_str="--arg1 value1 --arg2 value2",
        environment={"ENV1": "val1", "ENV2": "val2"},
        docker_run_args=["--network=host", "--privileged"],
        use_sudo=True,
    )

    assert "sudo docker run" in command
    assert "--rm" in command
    assert "--network=host --privileged" in command
    assert "-e ENV1=val1" in command
    assert "-e ENV2=val2" in command
    assert "test-image:latest" in command
    assert "python -m app" in command
    assert "--arg1 value1 --arg2 value2" in command

    # Test without sudo
    command = create_docker_run_command(
        image="test-image:latest",
        entrypoint_str="python -m app",
        arguments_str="--arg1 value1 --arg2 value2",
        environment={"ENV1": "val1", "ENV2": "val2"},
        docker_run_args=["--network=host", "--privileged"],
        use_sudo=False,
    )

    assert "docker run" in command
    assert "sudo" not in command


def test_prepare_task_kwargs():
    """Test the prepare_task_kwargs function."""
    settings = SkypilotBaseOrchestratorSettings(
        envs={"SETTING_ENV": "setting_val"},
        task_name=None,
        workdir="/workdir",
        file_mounts={"/src": "/dest"},
        task_settings={"custom": "value"},
    )

    task_kwargs = prepare_task_kwargs(
        settings=settings,
        run_command="echo hello",
        setup="apt-get update",
        task_envs={"TASK_ENV": "task_val"},
        task_name="test-task",
    )

    assert task_kwargs["run"] == "echo hello"
    assert task_kwargs["setup"] == "apt-get update"
    assert task_kwargs["name"] == "test-task"
    assert task_kwargs["workdir"] == "/workdir"
    assert task_kwargs["file_mounts"] == {"/src": "/dest"}
    assert task_kwargs["custom"] == "value"
    assert task_kwargs["envs"]["SETTING_ENV"] == "setting_val"
    assert task_kwargs["envs"]["TASK_ENV"] == "task_val"


@patch("sky.clouds.Cloud")
def test_prepare_resources_kwargs(mock_cloud):
    """Test the prepare_resources_kwargs function."""
    settings = SkypilotBaseOrchestratorSettings(
        instance_type="m4.large",
        cpus=4,
        memory=16,
        accelerators={"V100": 2},
        region="us-west-2",
        disk_size=100,
        resources_settings={"custom_resource": "value"},
    )

    resources_kwargs = prepare_resources_kwargs(
        cloud=mock_cloud,
        settings=settings,
        default_instance_type="t2.micro",
    )

    assert resources_kwargs["cloud"] == mock_cloud
    assert resources_kwargs["instance_type"] == "m4.large"
    assert resources_kwargs["cpus"] == 4
    assert resources_kwargs["memory"] == 16
    assert resources_kwargs["accelerators"] == {"V100": 2}
    assert resources_kwargs["region"] == "us-west-2"
    assert resources_kwargs["disk_size"] == 100
    assert resources_kwargs["custom_resource"] == "value"


def test_prepare_launch_kwargs():
    """Test the prepare_launch_kwargs function."""
    settings = SkypilotBaseOrchestratorSettings(
        retry_until_up=True,
        idle_minutes_to_autostop=60,
        down=True,
        stream_logs=True,
        num_nodes=3,
        launch_settings={"custom_launch": "value"},
    )

    # Test default behavior (detach_run opposite of stream_logs)
    launch_kwargs = prepare_launch_kwargs(
        settings=settings,
        stream_logs=True,
    )

    assert launch_kwargs["retry_until_up"] is True
    assert launch_kwargs["idle_minutes_to_autostop"] == 60
    assert launch_kwargs["down"] is True
    assert launch_kwargs["stream_logs"] is True
    assert launch_kwargs["detach_run"] is False  # opposite of stream_logs
    assert launch_kwargs["num_nodes"] == 3
    assert launch_kwargs["custom_launch"] == "value"

    # Test with explicit detach_run override
    launch_kwargs = prepare_launch_kwargs(
        settings=settings,
        stream_logs=True,
        detach_run=True,  # Explicitly override
    )

    assert launch_kwargs["stream_logs"] is True
    assert (
        launch_kwargs["detach_run"] is True
    )  # Explicitly set, not derived from stream_logs

    # Test with override values
    launch_kwargs = prepare_launch_kwargs(
        settings=settings,
        stream_logs=False,
        down=False,
        idle_minutes_to_autostop=30,
        num_nodes=5,
    )

    assert launch_kwargs["idle_minutes_to_autostop"] == 30
    assert launch_kwargs["down"] is False
    assert launch_kwargs["stream_logs"] is False
    assert launch_kwargs["detach_run"] is True  # opposite of stream_logs
    assert launch_kwargs["num_nodes"] == 5
