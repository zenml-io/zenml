from zenml import step, pipeline

@step
def make_a() -> int:
    return 7

@step
def make_b() -> int:
    return 11

@step
def report_a(a: int, b: int) -> str:
    return 'a wins'

@step
def report_b(a: int, b: int) -> str:
    return 'b wins'

@pipeline(dynamic=True)
def my_pipeline():
    a = make_a()
    b = make_b()
    
    # Use conditional logic with .load() for control flow
    if a > b:
        result = report_a(a=a, b=b)
    else:
        result = report_b(a=a, b=b)
    
    return result

if __name__ == "__main__":
    my_pipeline()
