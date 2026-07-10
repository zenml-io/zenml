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
    if value.load() < 0:  # check value for control flow
        negated = negate(value)  # call negate only if negative
    else:
        negated = value  # otherwise pass through
    
    # Final result should be 8
    return negated.load()

if __name__ == "__main__":
    my_pipeline()
