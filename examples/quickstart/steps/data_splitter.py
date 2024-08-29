import math
import random
from typing import Annotated, Tuple

from datasets import Dataset

from zenml import step


@step
def split_dataset(
    dataset: Dataset,
    train_size: float=0.7,
    test_size: float=0.1,
    eval_size: float=0.2,
    subset_size: float = 1.0,
    random_state: int = 42,
) -> Tuple[
    Annotated[Dataset, "train_dataset"],
    Annotated[Dataset, "eval_dataset"],
    Annotated[Dataset, "test_dataset"],
]:
    """
    Split a dataset into train, evaluation, and test sets.

    Args:
    dataset (Dataset): The input dataset to split.
    subset_size (float): Fraction of the dataset to use. Default is 1.0 (use full dataset).
    train_size (float): Fraction of the dataset to use for training. Default is 0.7.
    test_size (float): Fraction of the dataset to use for testing. Default is 0.1.
    eval_size (float): Fraction of the non-test data to use for evaluation. Default is 0.2.
    random_state (int): Random state for reproducibility. Default is 42.

    Returns:
    tuple: (train_dataset, eval_dataset, test_dataset)
    """
    # Validate split proportions
    if not math.isclose(train_size + eval_size + test_size, 1.0, rel_tol=1e-5):
        raise ValueError("Split proportions must sum to 1.0")
    # Validate split proportions
    if subset_size > 1.0 or subset_size < 0.0:
        print(
            f"Subset_size should be in the range [0.0, 1.0], {subset_size} was supplied. "
            f"Defaulting subset_size to 1.0"
        )
        subset_size = 1.0

    # Set random seed for reproducibility
    random.seed(random_state)

    # Get the total number of samples in the dataset
    total_samples = len(dataset)

    # Calculate the number of samples for the subset
    subset_samples = int(total_samples * subset_size)

    # Randomly select indices for the subset
    all_indices = list(range(total_samples))
    subset_indices = random.sample(all_indices, subset_samples)

    # Calculate split sizes
    train_samples = int(subset_samples * train_size)
    eval_samples = int(subset_samples * eval_size)

    # Shuffle the subset indices
    random.shuffle(subset_indices)

    # Split the indices
    train_indices = subset_indices[:train_samples]
    eval_indices = subset_indices[train_samples : train_samples + eval_samples]
    test_indices = subset_indices[train_samples + eval_samples :]

    return (
        dataset.select(train_indices),
        dataset.select(eval_indices),
        dataset.select(test_indices),
    )
