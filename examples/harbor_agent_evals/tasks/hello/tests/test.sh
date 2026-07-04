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
# Check that the agent wrote '42' into /app/answer.txt.
# Reward 1.0 on a clean match, 0.0 otherwise. Writes to /logs/verifier/reward.txt.

set -u
mkdir -p /logs/verifier

answer_file=/app/answer.txt
reward=0.0

if [ -f "$answer_file" ]; then
    contents="$(cat "$answer_file" | tr -d '\n')"
    echo "verifier: /app/answer.txt contents = '$contents'"
    if [ "$contents" = "42" ]; then
        reward=1.0
    fi
else
    echo "verifier: $answer_file not found"
fi

echo "$reward" > /logs/verifier/reward.txt
echo "verifier: reward = $reward"
