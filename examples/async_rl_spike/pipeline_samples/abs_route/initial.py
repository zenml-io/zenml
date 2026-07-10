from zenml import step, pipeline

@step
def get_value() -> int:
    return -8

@step
def negate(x: int) -> int:
    return -x

@pipeline(dynamic=True)
def my_pipeline():
    value = get_value()  # returns an artifact handle
    if value < 0:
        negated = negate(x=value.load())  # only call negate if value is negative
    else:
        negated = value  # otherwise, just use the original value (but this won't happen)
    return negated

if __name__ == "__main__":
    my_pipeline()
