import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations
from subprocess import PIPE, run
from typing import Any, Dict, Tuple

from rich import print

from zenml.integrations.registry import integration_registry


def get_integration_requirements(integration_name: str) -> str:
    """Get the requirements for a given integration.

    Args:
        integration_name: The name of the integration.

    Returns:
        The requirements for the integration as a string.
    """
    requirements = integration_registry.select_integration_requirements(
        integration_name
    )
    if integration_name == "prodigy":
        requirements = [req for req in requirements if req != "prodigy"]
    return " ".join(requirements)


def test_integration_compatibility(integrations: Tuple[str, ...]) -> bool:
    """Test the compatibility of a set of integrations.

    Args:
        integrations: A tuple of integration names.

    Returns:
        True if the integrations are compatible, False otherwise.
    """
    requirements = "\n".join(
        [
            "zenml[server,templates]",
            *[
                "\n".join(get_integration_requirements(integration).split())
                for integration in integrations
            ],
        ]
    )

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".txt"
    ) as temp_file:
        temp_file.write(requirements)
        temp_file_path = temp_file.name

    result = run(
        f"uv pip compile {temp_file_path}",
        shell=True,
        stdout=PIPE,
        stderr=PIPE,
    )
    os.unlink(temp_file_path)

    return result.returncode == 0


def test_integration_combinations(
    integration_names: Tuple[str, ...],
    combination_size: int,
    executor: ThreadPoolExecutor,
) -> Tuple[int, Tuple[Tuple[str, ...], ...]]:
    """Test all possible combinations of integrations of a given size.

    Args:
        integration_names: A tuple of all integration names.
        combination_size: The size of the combinations to test.
        executor: The ThreadPoolExecutor to use for testing combinations.

    Returns:
        A tuple containing the total number of combinations and a tuple of
        incompatible combinations.
    """
    print("-----------------------------")
    print(f"Testing integration combinations of size {combination_size}")
    print(
        f"Total combinations: {len(list(combinations(integration_names, combination_size)))}"
    )
    print("-----------------------------")
    total_combinations = len(
        list(combinations(integration_names, combination_size))
    )
    incompatible_combinations = []

    futures = []
    for combination in combinations(integration_names, combination_size):
        future = executor.submit(test_integration_compatibility, combination)
        future.combination = combination
        futures.append(future)

    for i, future in enumerate(as_completed(futures), start=1):
        combination = future.combination
        if future.result():
            print(
                f"[green]PASS[/green] Completed integration combination {i}/{total_combinations}: {combination}"
            )
        else:
            print(
                f"[red]FAIL[/red] Completed integration combination {i}/{total_combinations}: {combination}"
            )
            incompatible_combinations.append(combination)

    return total_combinations, tuple(incompatible_combinations)


def main() -> None:
    """Main function to run the integration compatibility tests."""
    integrations: Dict[str, Any] = integration_registry.integrations
    integration_names = tuple(integrations.keys())

    incompatible_pairs = []
    incompatible_triplets = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        for combination_size in [2, 3]:
            _, incompatible_combinations = test_integration_combinations(
                integration_names, combination_size, executor=executor
            )

            if combination_size == 2:
                incompatible_pairs = sorted(incompatible_combinations)
            else:
                incompatible_triplets = sorted(incompatible_combinations)

    from rich.console import Console
    from rich.table import Table

    if incompatible_pairs:
        table = Table(
            title=f"{len(incompatible_pairs)} Incompatible Integration Pairs"
        )
        table.add_column("Integration 1", style="cyan")
        table.add_column("Integration 2", style="magenta")

        for pair in incompatible_pairs:
            table.add_row(pair[0], pair[1])

        console = Console()
        console.print(table)

    if incompatible_triplets:
        table = Table(
            title=f"{len(incompatible_triplets)} Incompatible Integration Triplets"
        )
        table.add_column("Integration 1", style="cyan")
        table.add_column("Integration 2", style="magenta")
        table.add_column("Integration 3", style="green")

        for triplet in incompatible_triplets:
            table.add_row(triplet[0], triplet[1], triplet[2])

        console = Console()
        console.print(table)


if __name__ == "__main__":
    main()
