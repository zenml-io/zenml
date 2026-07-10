from zenml import step, pipeline

@step
def add(total: int, number: int) -> int:
    return total + number

@pipeline(dynamic=True)
def my_pipeline():
    numbers = [1, 2, 3, 4, 5]
    total = 0
    for num in numbers:
        total = add(total=total.load(), number=num).load()

if __name__ == "__main__":
    my_pipeline()
