from zenml import step, pipeline

@step
def start() -> str:
    return 'z'

@step
def append_z(input_string: str) -> str:
    return input_string + 'z'

@pipeline(dynamic=True)
def my_pipeline():
    s = start()  # returns artifact handle
    for _ in range(3):  # start with 'z', need 3 more 'z' to reach 4 chars
        s = append_z(s)

if __name__ == "__main__":
    my_pipeline()
