from zenml import step, pipeline

@step
def start() -> int:
    return 3

@step
def double(x: int) -> int:
    return x * 2

@pipeline(dynamic=True)
def my_pipeline():
    value = start()  # returns artifact handle
    while value.load() <= 50:
        value = double(value)  # update value in loop

if __name__ == "__main__":
    my_pipeline()
