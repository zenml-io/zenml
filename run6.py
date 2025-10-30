from typing import Tuple, Dict, Any
from typing import Annotated
from zenml import step, pipeline

# --- 1) Seed step with 3 outputs --------------------------------------------

@step
def seed() -> Tuple[
    Annotated[int, "seed_int"],
    Annotated[str, "seed_str"],
    Annotated[float, "seed_float"],
]:
    # Replace with real initialization logic
    return 42, "hello-zenml", 3.14159


# --- 2) First layer: 3,000 sub steps ----------------------------------------

@step
def worker(
    idx: int,
    seed_int: int,
    seed_str: str,
    seed_float: float,
) -> Dict[str, Any]:
    # Replace with your actual per-item processing
    return {
        "idx": idx,
        "summary": f"{seed_str}-{idx}",
        "score": seed_int * seed_float + idx,
    }


# --- 3) Second layer: one subsequent step per worker ------------------------

@step
def followup(result: Dict[str, Any]) -> None:
    # Replace with your aggregation / persistence / notifications, etc.
    # e.g., push to a DB, write a file, send a message, etc.
    print(f"Follow-up for idx={result['idx']}: score={result['score']}")


# --- 4) Pipeline wiring ------------------------------------------------------

@pipeline(
    enable_cache=False,  # optional: disable cache for demonstration
    settings={"orchestrator": {"synchronous": False}},  # run async if supported
)
def mega_pipeline(n_substeps: int = 3000):
    # 1) Get 3 outputs
    seed_int, seed_str, seed_float = seed()

    # 2) Fan-out to N sub steps
    first_layer_outputs = []
    for i in range(n_substeps):
        out = worker(
            idx=i,
            seed_int=seed_int,
            seed_str=seed_str,
            seed_float=seed_float,
            id=f"worker_{i}",  # unique invocation IDs
        )
        first_layer_outputs.append(out)

    # 3) For each sub step, run a subsequent step
    for i, out in enumerate(first_layer_outputs):
        followup(out, id=f"followup_{i}")


# --- 5) Run it ---------------------------------------------------------------

if __name__ == "__main__":
    # TIP: test with a small n_substeps locally (e.g., 5), then scale to 3000.
    mega_pipeline(n_substeps=3000)
