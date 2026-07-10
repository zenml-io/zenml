from zenml import step, pipeline

@step
def start() -> int:
    return 3

@step
def double(x: int) -> int:
    return x * 2

@pipeline(dynamic=True)
def my_pipeline():
    value = start()
    while value <= 50:
        value = double(x=value)
    return value

if __name__ == "__main__":
    my_pipeline()
