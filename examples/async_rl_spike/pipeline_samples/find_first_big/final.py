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
    numbers = make_numbers()  # returns an artifact handle
    values = numbers.load()   # get the list to walk through
    
    for num in values:
        is_big_result = is_big(x=num).load()  # call is_big and check result
        if is_big_result:
            report_value(num)  # stop at first True and report the value
            break

if __name__ == "__main__":
    my_pipeline()
