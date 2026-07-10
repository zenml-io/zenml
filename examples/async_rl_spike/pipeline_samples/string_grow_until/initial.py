from zenml import step, pipeline

@step
def start() -> str:
    return 'a'

@step
def double_str(s: str) -> str:
    return s + s

@pipeline(dynamic=True)
def my_pipeline():
    s = start()  # returns artifact handle
    while len(s.load()) <= 5:
        s = double_str(s)  # fan-out with condition based on length
    return s

if __name__ == "__main__":
    my_pipeline()
