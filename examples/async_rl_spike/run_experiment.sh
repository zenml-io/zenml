#!/usr/bin/env bash
# Deploy the vLLM server and fire off the trainer + rollout pipelines.
# Assumes the rl-spike project and modal-build stack are already active.
# The orchestrator is async, so both submit and return; the runs continue on
# Modal. Stop the server yourself when done:
#   modal app stop async-rl-spike-vllm -y

set -uo pipefail
cd "$(dirname "$0")"
export PYTHONPATH=.

MODEL="Qwen/Qwen3-4B-Instruct-2507"
RUN_NAME="exp"
TASKS="abs_route bigger_of_two grade_letter parity_branch vowel_any_flag string_grow_until alternating_sum_loop fib_loop word_ladder loop_sum_to_five find_first_big triangular_until double_until"

export MODAL_TOKEN_ID="$(uv run --no-sync python -c "from zenml.client import Client; print(Client().get_secret('modal_credentials').secret_values['token_id'])")"
export MODAL_TOKEN_SECRET="$(uv run --no-sync python -c "from zenml.client import Client; print(Client().get_secret('modal_credentials').secret_values['token_secret'])")"

uv run --no-sync modal app stop async-rl-spike-vllm -y >/dev/null 2>&1 || true
ASYNC_RL_MODEL="$MODEL" ASYNC_RL_GPU="L4" uv run --no-sync modal deploy serving/modal_app.py

echo ">> waiting for vLLM to serve $MODEL"
for _ in $(seq 1 60); do
  curl -s --max-time 10 "https://zenml-io--async-rl-spike-vllm-serve.modal.run/v1/models" 2>/dev/null | grep -qF "$MODEL" && break
  sleep 20
done

uv run --no-sync python run_trainer.py --run-name "$RUN_NAME" --serving-mode remote --backend modal \
  --model "$MODEL" --group-size 8 --groups-per-step 4 --max-train-steps 20 --max-versions 2 \
  --lora-rank 16 --learning-rate 5e-5 --idle-timeout 600

uv run --no-sync python run_rollouts.py --run-name "$RUN_NAME" --serving-mode remote \
  --model "$MODEL" --group-size 8 --num-parallel 12 --temperature 1.0 --first-version-timeout 1200 \
  --task-ids $TASKS
