from zenml import step, pipeline

@step
def make_numbers() -> list[int]:
    return [3, 5, 7]

@step
def total(values: list[int]) -> int:
    return sum(values)

@step
def report_odd() -> str:
    return 'odd'

@step
def report_even() -> str:
    return 'even'

@pipeline(dynamic=True)
def my_pipeline():
    numbers = make_numbers()
    total_value = total(numbers).load()
    if total_value % 2 == 1:
        result = report_odd()
    else:
        result = report_even()

if __name__ == "__main__":
    my_pipeline()
