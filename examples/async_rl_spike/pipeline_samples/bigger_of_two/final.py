from zenml import step, pipeline

@step
def make_a() -> int:
    return 7

@step
def make_b() -> int:
    return 11

@step
def report_a(a: int) -> str:
    return 'a wins'

@step
def report_b(a: int) -> str:
    return 'b wins'

@pipeline(dynamic=True)
def my_pipeline():
    a = make_a().load()
    b = make_b().load()
    if a > b:
        result = report_a(a=a)
    else:
        result = report_b(a=b)

if __name__ == "__main__":
    my_pipeline()
