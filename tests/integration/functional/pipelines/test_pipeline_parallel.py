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
import pathlib
import platform
import subprocess
from typing import List
from uuid import uuid1

import pytest

from zenml.client import Client


class TestArtifactsManagement:
    @pytest.mark.skipif(
        platform.system().lower() == "windows",
        reason="Windows not fully support OS processes.",
    )
    def test_parallel_runs_can_register_same_artifact(
        self, clean_client: Client
    ):
        threads: List[subprocess.Popen] = []
        run_prefix = str(uuid1())
        steps_count = 20
        runs_count = 3
        for i in range(runs_count):
            threads.append(
                subprocess.Popen(
                    [
                        "python3",
                        pathlib.Path(__file__).parent.resolve()
                        / "util_parallel_pipeline_script.py",
                        run_prefix,
                        str(i),
                        str(steps_count),
                    ]
                )
            )
        for thread in threads:
            thread.wait()

        for i in range(runs_count):
            res = clean_client.get_pipeline_run(f"{run_prefix}_{i}")
            assert res.status == "completed", "some pipeline failed"

        res = clean_client.list_artifact_versions(
            size=1000, artifact="artifact"
        )
        assert len(res.items) == runs_count * steps_count, (
            "not all artifacts are registered"
        )
        assert {r.load() for r in res.items} == {
            100 * i + j for i in range(runs_count) for j in range(steps_count)
        }, "not all artifacts are registered with proper values"
        assert {r.version for r in res.items} == {
            str(i) for i in range(1, runs_count * steps_count + 1)
        }, "not all artifacts are registered with proper unique versions"
