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
"""Phase-1 smoke test for B2b: drive ZenMLPipelineEnv by hand, no trainer.

Plays the exact sequence GRPOTrainer would drive — reset(task_dir) ->
tool calls -> env.reward — but with a scripted "policy", so it runs on a
laptop with no vLLM/GPU. Two scenarios:

  1. perfect: write a known-good const_seven pipeline, run it, expect
     reward 1.0 from the in-sandbox verifier.
  2. fix-loop (--fix-loop): write a broken pipeline first, run it, read
     the traceback, then write the fixed version — the multi-turn
     "attempt -> traceback -> edit" filesystem history the snapshot demo
     wants.

Run from this directory (so the .zen context selects the rl-spike project
and a stack with a Sandbox component):

    ../../.venv-b2b/bin/python smoke_env.py [--fix-loop]
"""

import argparse
import sys
import time
from pathlib import Path

from zenml_harness import ZenMLPipelineEnv

TASK_DIR = Path(__file__).parent / "tasks" / "pipeline_const_seven"

GOOD_PIPELINE = '''\
from zenml import step, pipeline

@step
def make_seven() -> int:
    return 7

@pipeline(dynamic=True)
def seven_pipeline():
    make_seven()

if __name__ == "__main__":
    seven_pipeline()
'''

# Broken on purpose: the step returns a string, and the pipeline never
# calls the step — running it succeeds but produces no completed run with
# the right output, and the first version also has a NameError to give
# the fix loop a real traceback to read.
BROKEN_PIPELINE = '''\
from zenml import step, pipeline

@step
def make_seven() -> int:
    return sevn

@pipeline(dynamic=True)
def seven_pipeline():
    make_seven()

if __name__ == "__main__":
    seven_pipeline()
'''


def banner(title: str) -> None:
    print(f"\n=== {title} " + "=" * max(0, 60 - len(title)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix-loop", action="store_true")
    args = parser.parse_args()

    env = ZenMLPipelineEnv()
    started = time.time()

    banner("reset (opens the ZenML Sandbox session)")
    instruction = env.reset(task_dir=str(TASK_DIR))
    print(instruction)
    print(f"[reset took {time.time() - started:.1f}s]")

    if args.fix_loop:
        banner("turn 1: write BROKEN pipeline")
        print(env.write_pipeline(BROKEN_PIPELINE))
        banner("turn 1: run it (expect a NameError traceback)")
        out = env.run_pipeline()
        print(out[-2000:])
        banner("turn 2: write the FIXED pipeline")

    print(env.write_pipeline(GOOD_PIPELINE))
    banner("run the pipeline in the sandbox")
    t = time.time()
    out = env.run_pipeline()
    print(out[-2000:])
    print(f"[run_pipeline took {time.time() - t:.1f}s]")

    banner("reward (runs the verifier in the sandbox)")
    t = time.time()
    reward = env.reward
    print(f"reward = {reward}  [verifier took {time.time() - t:.1f}s]")

    banner("teardown")
    env._run(env._stop())  # noqa: SLF001 — spike: HarborEnv has no public close
    print(f"total {time.time() - started:.1f}s")

    if reward != 1.0:
        print("SMOKE FAILED: expected reward 1.0")
        return 1
    print("SMOKE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
