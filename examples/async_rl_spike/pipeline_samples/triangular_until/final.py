from zenml import step, pipeline

@step
def add_next(current_total: int) -> int:
    return current_total + (current_total + 1)

@pipeline(dynamic=True)
def my_pipeline():
    total = 0  # Start with 0
    while total <= 20:
        total = add_next(current_total=total).load()

if __name__ == "__main__":
    my_pipeline()
