# Scorer image for the agentic RL taskset (examples/agentic_rl/tasks/*).
#
# Every task.toml pins this image, which makes the scorer environment part
# of the task's identity: "this reward came from this exact environment"
# is a recorded fact. Build once and (for remote stacks) push to a
# registry the sandbox flavor can pull from:
#
#   docker build -t zenml-rl-scorer:0.1 examples/agentic_rl/docker
#
# The scorer (score_pipeline.py) is the RL spike's verifier, byte
# identical — refreshed by scripts/gen_taskset.py, asserted by the unit
# tests. It runs generated pipelines against a throwaway local sqlite
# store (it sets ZENML_CONFIG_PATH itself before any zenml import).
#
# python:3.11-slim (Debian) already ships bash, coreutils `timeout`, and
# tar — the three tools the ZenML/Harbor sandbox bridge requires.
FROM python:3.11-slim

# The generated pipelines and the scorer only need zenml with the local
# sqlite store. Pinned to the version this example was built against.
RUN pip install --no-cache-dir "zenml[local]==0.96.1"

COPY score_pipeline.py /opt/zenml-scorer/score_pipeline.py

ENV ZENML_ANALYTICS_OPT_IN=false \
    AUTO_OPEN_DASHBOARD=false \
    ZENML_ENABLE_RICH_TRACEBACK=false \
    ZENML_LOGGING_VERBOSITY=WARN

# Keep-alive is supplied by the sandbox flavor; no ENTRYPOINT/CMD here.
