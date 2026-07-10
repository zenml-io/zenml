from zenml import step, pipeline

@step
def make_numbers() -> list[int]:
    return [3, 8, 2, 9]

@step
def is_big(x: int) -> bool:
    return x > 5

@step
def report_value(x: int) -> int:
    return x

@pipeline(dynamic=True)
def my_pipeline():
    numbers = make_numbers()
    results = []
    for num in numbers:
        is_big_result = is_big(x=num)
        if is_big_result:
            results.append(num)
            break
    report_value(x=results[0] if results else 0)

if __name__ == "__main__":
    my_pipeline()
