"""E3: measure what the RL loop actually moves through the artifact store.

Read-only, client-side. For each given pipeline run it walks every step,
stats the step's output artifacts directly on S3 (object count + bytes),
attributes them to loop iterations (ZenML suffixes repeated invocations
`_2`, `_3`, ... — unsuffixed = iteration 0), and optionally loads episode
artifacts to extract the in-sandbox `timings` dicts. Prints a JSON
summary; DATA_LAYER.md interprets the numbers.

Usage (from examples/rl_spike, with the repo venv python — never bare
`uv run`, it wipes the venv):

    python measure_data_layer.py 7c7d72c7 f411036a 9d51a334 93f4246b 6a6e0480 \
        --timings-runs 7c7d72c7 6a6e0480 --json-out data_layer_raw.json

Requires: an AWS profile that can read the artifact bucket
(default zenml-dev-power; `aws sso login` first) and a zenml client
connected to the staging server (project rl-spike).
"""

import argparse
import json
import re
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import boto3

from zenml.client import Client

SUFFIX = re.compile(r"_(\d+)$")


def base_and_iteration(step_name: str) -> Tuple[str, int]:
    """Split a step name into its base name and 0-based loop iteration.

    `map:run_episode_3:17` -> ("map:run_episode", 2); the map chunk index
    is discarded. Unsuffixed names are iteration 0.

    Args:
        step_name: The step run name.

    Returns:
        (base name, iteration index).
    """
    name = step_name
    chunk_stripped = re.sub(r":\d+$", "", name)
    match = SUFFIX.search(chunk_stripped)
    if match:
        return chunk_stripped[: match.start()], int(match.group(1)) - 1
    return chunk_stripped, 0


def resolve_run(client: Client, prefix: str) -> Any:
    """Find a pipeline run by id prefix.

    Args:
        client: ZenML client.
        prefix: Run id prefix (8 chars is enough).

    Returns:
        The pipeline run response.

    Raises:
        ValueError: If no run matches.
    """
    for run in client.list_pipeline_runs(sort_by="desc:created", size=200):
        if str(run.id).startswith(prefix):
            return run
    raise ValueError(f"no run with id prefix {prefix}")


def s3_stat(s3: Any, uri: str) -> Tuple[int, int]:
    """Sum object count and bytes under an s3:// prefix.

    Args:
        s3: boto3 s3 client.
        uri: s3://bucket/prefix artifact uri.

    Returns:
        (object count, total bytes).
    """
    parsed = urlparse(uri)
    bucket, prefix = parsed.netloc, parsed.path.lstrip("/")
    count = size = 0
    token: Optional[str] = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            count += 1
            size += obj["Size"]
        token = resp.get("NextContinuationToken")
        if not token:
            return count, size


def collect_steps(client: Client, run_id: Any) -> List[Any]:
    """Fetch all step runs of a pipeline run, paginated.

    Args:
        client: ZenML client.
        run_id: Pipeline run id.

    Returns:
        All step run responses.
    """
    steps: List[Any] = []
    page = 1
    while True:
        p = client.list_run_steps(pipeline_run_id=run_id, size=500, page=page)
        steps.extend(p.items)
        if page >= p.total_pages:
            return steps
        page += 1


def summarize(values: List[float]) -> Dict[str, float]:
    """Mean/median/p95/min/max summary of a list.

    Args:
        values: The values.

    Returns:
        Summary dict (empty if no values).
    """
    if not values:
        return {}
    ordered = sorted(values)
    return {
        "n": len(values),
        "mean": round(statistics.fmean(values), 3),
        "median": round(ordered[len(ordered) // 2], 3),
        "p95": round(ordered[int(len(ordered) * 0.95) - 1], 3),
        "min": round(ordered[0], 3),
        "max": round(ordered[-1], 3),
        "sum": round(sum(values), 3),
    }


def measure_run(
    client: Client, s3: Any, prefix: str, load_timings: bool
) -> Dict[str, Any]:
    """Measure artifact sizes (and optionally timings) for one run.

    Args:
        client: ZenML client.
        s3: boto3 s3 client.
        prefix: Run id prefix.
        load_timings: Whether to load every episode artifact for its
            timings dict (one S3 GET per episode — minutes, not hours).

    Returns:
        Per-run measurement dict.
    """
    run = resolve_run(client, prefix)
    steps = collect_steps(client, run.id)

    artifacts: List[Dict[str, Any]] = []
    episode_avs: List[Any] = []
    for step in steps:
        base, iteration = base_and_iteration(step.name)
        duration = None
        if step.start_time and step.end_time:
            duration = (step.end_time - step.start_time).total_seconds()
        for out_name, avs in (step.outputs or {}).items():
            for av in avs:
                artifacts.append(
                    {
                        "step_base": base,
                        "iteration": iteration,
                        "output": out_name,
                        "uri": av.uri,
                        "step_duration_s": duration,
                    }
                )
                if base.startswith("map:run_episode") and load_timings:
                    episode_avs.append((base, iteration, duration, av))

    with ThreadPoolExecutor(max_workers=16) as pool:
        stats = list(pool.map(lambda a: s3_stat(s3, a["uri"]), artifacts))
    for art, (count, size) in zip(artifacts, stats):
        art["objects"], art["bytes"] = count, size

    by_step: Dict[str, Dict[str, Any]] = {}
    by_iteration: Dict[int, int] = {}
    for art in artifacts:
        bucket = by_step.setdefault(
            art["step_base"],
            {"bytes": [], "objects": 0, "durations": []},
        )
        bucket["bytes"].append(art["bytes"])
        bucket["objects"] += art["objects"]
        if art["step_duration_s"] is not None:
            bucket["durations"].append(art["step_duration_s"])
        by_iteration[art["iteration"]] = (
            by_iteration.get(art["iteration"], 0) + art["bytes"]
        )

    result: Dict[str, Any] = {
        "run": run.name,
        "run_id": str(run.id),
        "status": str(run.status),
        "steps": len(steps),
        "artifacts": len(artifacts),
        "total_bytes": sum(a["bytes"] for a in artifacts),
        "total_objects": sum(a["objects"] for a in artifacts),
        "bytes_by_iteration": dict(sorted(by_iteration.items())),
        "by_step": {
            name: {
                "artifact_bytes": summarize([float(b) for b in d["bytes"]]),
                "objects": d["objects"],
                "step_duration_s": summarize(d["durations"]),
            }
            for name, d in sorted(by_step.items())
        },
    }

    if load_timings and episode_avs:

        def load_timing(
            item: Tuple[str, int, Optional[float], Any],
        ) -> Dict[str, Any]:
            _, iteration, duration, av = item
            episode = av.load()
            return {
                "iteration": iteration,
                "step_duration_s": duration,
                **(episode.get("timings") or {}),
            }

        with ThreadPoolExecutor(max_workers=16) as pool:
            timing_rows = list(pool.map(load_timing, episode_avs))
        keys = sorted(
            {k for row in timing_rows for k in row if k.endswith("_s")}
        )
        result["episode_timings"] = {
            key: summarize(
                [row[key] for row in timing_rows if row.get(key) is not None]
            )
            for key in keys
        }
        in_sandbox = [
            sum(
                row.get(k, 0)
                for k in ("session_create_s", "upload_s", "score_exec_s")
            )
            for row in timing_rows
        ]
        overhead = [
            row["step_duration_s"] - sandbox_time
            for row, sandbox_time in zip(timing_rows, in_sandbox)
            if row.get("step_duration_s") is not None
        ]
        result["episode_timings"]["harness_overhead_s"] = summarize(overhead)

    return result


def main() -> None:
    """Run the measurement and print the JSON summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", help="Run id prefixes")
    parser.add_argument(
        "--timings-runs",
        nargs="*",
        default=[],
        help="Run prefixes whose episode artifacts should be loaded for timings",
    )
    parser.add_argument("--profile", default="zenml-dev-power")
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    s3 = boto3.Session(profile_name=args.profile).client("s3")
    client = Client()
    results = [
        measure_run(
            client,
            s3,
            prefix,
            load_timings=any(prefix.startswith(t) for t in args.timings_runs),
        )
        for prefix in args.runs
    ]
    output = json.dumps(results, indent=2)
    print(output)
    if args.json_out:
        with open(args.json_out, "w") as f:
            f.write(output)


if __name__ == "__main__":
    main()
