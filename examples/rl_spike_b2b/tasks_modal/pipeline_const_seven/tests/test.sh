#!/bin/bash
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
#
# Harbor verifier entrypoint: score /app/pipeline.py with the rl_spike
# scorer and translate its reward JSON into Harbor's reward contract
# (/logs/verifier/reward.json). The full scorer breakdown is kept next to
# it as score.json for post-hoc archaeology.

set -u
mkdir -p /logs/verifier

python /tests/score_pipeline.py /app/pipeline.py /tests/spec.json \
    /logs/verifier/score.json > /logs/verifier/scorer_stdout.log 2>&1

python - <<'PY'
import json

try:
    with open("/logs/verifier/score.json") as f:
        result = json.load(f)
    reward = float(result.get("reward", 0.0))
except Exception:
    # Scorer crashed before writing score.json (e.g. /app/pipeline.py was
    # never written) — that is a legitimate zero, not a verifier error.
    reward = 0.0

with open("/logs/verifier/reward.json", "w") as f:
    json.dump({"reward": reward}, f)
print(f"verifier: reward = {reward}")
PY
