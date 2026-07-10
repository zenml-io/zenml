from zenml import step, pipeline

@step
def start() -> str:
    return 'a'

@step
def double_str(s: str) -> str:
    return s + s

@pipeline(dynamic=True)
def my_pipeline():
    s = start()  # returns an artifact handle
    while s.load() <= 'a' * 5:  # check length in control flow
        s = double_str(s)  # fan out and reassign

if __name__ == "__main__":
    my_pipeline()
