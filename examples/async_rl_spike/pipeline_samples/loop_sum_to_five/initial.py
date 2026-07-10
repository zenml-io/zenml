from zenml import step, pipeline

@step
def add(total: int, number: int) -> int:
    return total + number

@pipeline(dynamic=True)
def my_pipeline():
    # Start with 0 as the initial total
    total = 0
    # Create a list of numbers from 1 to 5
    numbers = [1, 2, 3, 4, 5]
    # Apply the add step once per number in a map
    # Each call to add will take the current total and the next number
    result = add.map(total=total, number=numbers)
    # The final result comes from the last add call
    return result[-1]  # Return the last (final) value

if __name__ == "__main__":
    my_pipeline()
