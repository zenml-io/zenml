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
"""The multi-turn snapshot demo carried over from F1 (SNAPSHOTS.md).

F1's demo could only snapshot a single-shot episode; B2b's fix loop gives
the filesystem *history* Hamza actually described: attempt -> traceback ->
edit, all in one session. This script plays that loop through the SAME
TRL harness the trainer drives, snapshots the sandbox AT FAILURE TIME
(after the broken attempt), lets the "policy" fix the file, then restores
the snapshot into a fresh session and shows the broken version frozen
inside — time travel to what the model saw when it failed.

Snapshots are Modal-only (SNAPSHOTS.md support matrix), so this needs a
stack with the Modal sandbox, e.g.:

    ../../.venv-b2b/bin/zenml stack set rl-spike-modal
    ../../.venv-b2b/bin/python snapshot_demo.py

The Modal task variant (tasks_modal/) has no docker_image pin; the demo
pip-installs zenml[local] into the session so run_pipeline produces a
real in-sandbox traceback.
"""

import sys
import time
from pathlib import Path

from smoke_env import BROKEN_PIPELINE, GOOD_PIPELINE, banner
from zenml_harness import ZenMLPipelineEnv

TASK_DIR = Path(__file__).parent / "tasks_modal" / "pipeline_const_seven"


def main() -> int:
    env = ZenMLPipelineEnv()
    started = time.time()

    banner("reset (opens the Modal sandbox session)")
    print(env.reset(task_dir=str(TASK_DIR))[:200], "...")

    banner("prep: pip install zenml[local] in the session (~1-2 min)")
    out = env._exec(  # noqa: SLF001 — spike: reuse the harness's exec
        "pip install -q 'zenml[local]==0.96.1' 2>&1 | tail -1", timeout=600
    )
    print(out[-300:])

    banner("turn 1: write BROKEN pipeline, run it")
    print(env.write_pipeline(BROKEN_PIPELINE))
    traceback_out = env.run_pipeline()
    print(traceback_out[-600:])

    banner("snapshot AT FAILURE TIME")
    # The layering the spike pierces on purpose: harness -> Harbor env
    # bridge -> ZenML SandboxSession. A shipped version would expose
    # snapshot() on the bridge.
    session = env._env._session  # noqa: SLF001
    snapshot = session.create_snapshot()
    print(f"snapshot ref: {snapshot.ref}")
    print(f"sandbox component: {snapshot.sandbox_id}")

    banner("turn 2: fix the pipeline, run green")
    print(env.write_pipeline(GOOD_PIPELINE))
    print(env.run_pipeline()[-300:])
    live_final = env._exec("cat /app/pipeline.py")  # noqa: SLF001
    print("live session file now contains:", live_final[:60].strip(), "...")

    banner("teardown live session")
    env._run(env._stop())  # noqa: SLF001

    banner("RESTORE the failure snapshot into a fresh session")
    from zenml.client import Client

    sandbox = Client().active_stack.sandbox
    restored = sandbox.restore(snapshot)
    try:
        frozen = restored.exec(
            ["bash", "-c", "cat /app/pipeline.py"]
        ).collect()
        print("restored /app/pipeline.py:")
        print(frozen.stdout)
        is_broken = "sevn" in frozen.stdout
        print(
            "=> restored file is the BROKEN version:",
            is_broken,
            "(the live session had already been fixed — time travel works)",
        )
    finally:
        restored.destroy()

    print(f"total {time.time() - started:.1f}s")
    if not is_broken:
        print("DEMO FAILED: restored filesystem did not carry the history")
        return 1
    print("DEMO PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
