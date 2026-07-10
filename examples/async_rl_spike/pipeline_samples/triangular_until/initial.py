from zenml import step, pipeline

@step
def add_next(current_total: int) -> int:
    next_integer = current_total + 1
    return current_total + next_integer

@pipeline(dynamic=True)
def sum_until_exceeds_twenty():
    total = 0
    while True:
        next_total = add_next(current_total=total)
        if next_total > 20:
            return next_total
        total = next_total

if __name__ == "__main__":
    sum_until_exceeds_twenty()
