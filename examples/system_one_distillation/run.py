#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.

"""Run the Banking77 distillation experiments on the active ZenML stack."""

import argparse
from typing import Any

from examples.system_one_distillation.banking77_open_teacher import (
    OPEN_TEACHER_CODE_REVISION,
)
from examples.system_one_distillation.banking77_pipelines import (
    DEFAULT_RUNG_SIZES,
    TEACHER_SHARD_COUNT,
    banking77_distillation_pipeline,
    banking77_open_teacher_pilot_pipeline,
    banking77_qwen_student_pipeline,
)

from zenml.config import DockerSettings, ResourceSettings
from zenml.integrations.modal.flavors import ModalOrchestratorSettings

OPEN_JEV_ARCHIVE = (
    "https://github.com/Zefan-Cai/Open-Jev/archive/"
    f"{OPEN_TEACHER_CODE_REVISION}.tar.gz"
)


def _add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    """Add options shared by the pilot and complete experiment.

    Args:
        parser: Subcommand parser to configure.
    """
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--prefix-cache", action="store_true")
    parser.add_argument("--gpu", default="H100")
    parser.add_argument(
        "--runtime-image",
        help=(
            "Prebuilt Modal-compatible image containing the open-teacher "
            "dependencies. When set, ZenML downloads this checkout's code "
            "at runtime instead of rebuilding the image."
        ),
    )


def _modal_step_settings(
    *, timeout: int, memory: str, gpu: str | None = None
) -> dict[str, Any]:
    """Build per-step Modal settings for one CPU or single-GPU container.

    Args:
        timeout: Modal timeout in seconds.
        memory: Container memory, for example ``"64GiB"``.
        gpu: Modal GPU type, or ``None`` for a CPU-only step.

    Returns:
        A step configuration for ``with_options(steps=...)``.
    """
    return {
        "settings": {
            "orchestrator": ModalOrchestratorSettings(
                gpu=gpu, modal_environment="dev", timeout=timeout
            ),
            "resources": ResourceSettings(
                cpu_count=8, gpu_count=1 if gpu else 0, memory=memory
            ),
        }
    }


def main(argv: list[str] | None = None) -> None:
    """Run the teacher pilot, full distillation, or Qwen student experiment.

    Args:
        argv: Optional arguments for tests.
    """
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    pilot_parser = subcommands.add_parser(
        "pilot", help="Measure the teacher on the validation split."
    )
    _add_shared_arguments(pilot_parser)
    pilot_parser.add_argument("--evaluation-limit", type=int, default=100)
    full_parser = subcommands.add_parser(
        "full", help="Label the full cohort and train every fixed rung."
    )
    _add_shared_arguments(full_parser)
    full_parser.add_argument(
        "--rung-sizes",
        nargs="+",
        type=int,
        default=list(DEFAULT_RUNG_SIZES),
    )
    qwen_parser = subcommands.add_parser(
        "qwen",
        help=(
            "Fine-tune Qwen students on a finished run's stored teacher "
            "labels without rerunning the teacher."
        ),
    )
    qwen_parser.add_argument(
        "--source-run",
        required=True,
        help="ID of a completed full run whose teacher labels to reuse.",
    )
    qwen_parser.add_argument("--gpu", default="L40S")
    qwen_parser.add_argument(
        "--rung-sizes",
        nargs="+",
        type=int,
        default=list(DEFAULT_RUNG_SIZES),
    )
    qwen_parser.add_argument(
        "--runtime-image",
        help="Prebuilt image with Torch and Transformers 5.10 or newer.",
    )
    args = parser.parse_args(argv)

    docker_settings = (
        DockerSettings(parent_image=args.runtime_image, skip_build=True)
        if args.runtime_image
        else DockerSettings(
            python_package_installer="uv",
            apt_packages=["gcc", "libc6-dev"],
            requirements=[
                f"open-jev[train] @ {OPEN_JEV_ARCHIVE}",
                "scikit-learn>=1.7,<2",
            ],
        )
    )
    if args.command == "qwen":
        banking77_qwen_student_pipeline.with_options(
            settings={"docker": docker_settings},
            steps={
                "distill_banking77_qwen_students": _modal_step_settings(
                    gpu=args.gpu, timeout=14_400, memory="64GiB"
                )
            },
        )(
            source_run_id=args.source_run,
            rung_sizes=tuple(args.rung_sizes),
            requested_gpu=args.gpu,
        )
        return
    is_pilot = args.command == "pilot"
    pipeline_definition = (
        banking77_open_teacher_pilot_pipeline
        if is_pilot
        else banking77_distillation_pipeline
    )
    teacher_steps = (
        ("label_banking77_with_open_teacher",)
        if is_pilot
        else tuple(
            f"label_open_teacher_shard_{index}"
            for index in range(1, TEACHER_SHARD_COUNT + 1)
        )
    )
    teacher_settings = _modal_step_settings(
        gpu=args.gpu,
        timeout=10_800 if is_pilot else 86_400,
        memory="64GiB",
    )
    student_settings = _modal_step_settings(timeout=10_800, memory="32GiB")
    step_settings = {step_id: teacher_settings for step_id in teacher_steps}
    if not is_pilot:
        step_settings["distill_banking77_students"] = student_settings
    configured = pipeline_definition.with_options(
        settings={
            "docker": docker_settings,
        },
        steps=step_settings,
    )
    shared_inputs = {
        "batch_size": args.batch_size,
        "prefix_cache": args.prefix_cache,
    }
    if is_pilot:
        configured(
            evaluation_limit=args.evaluation_limit,
            **shared_inputs,
        )
    else:
        configured(
            rung_sizes=tuple(args.rung_sizes),
            teacher_requested_gpu=args.gpu,
            **shared_inputs,
        )


if __name__ == "__main__":
    main()
