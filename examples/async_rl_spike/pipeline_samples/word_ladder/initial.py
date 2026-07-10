from zenml import step, pipeline

@step
def start() -> str:
    return 'z'

@step
def append_z(input_string: str) -> str:
    return input_string + 'z'

@pipeline(dynamic=True)
def my_pipeline():
    current = start()  # Start with 'z'
    # Repeatedly append 'z' until we have exactly 4 characters
    for _ in range(3):  # Need 3 more 'z's to go from 1 to 4
        current = append_z(input_string=current)
    return current

if __name__ == "__main__":
    my_pipeline()
