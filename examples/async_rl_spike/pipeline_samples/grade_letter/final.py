from zenml import step, pipeline

@step
def get_grade() -> int:
    return 78

@step
def report_a(grade: int) -> str:
    if grade >= 90:
        return 'A'
    return None

@step
def report_b(grade: int) -> str:
    if 70 <= grade < 90:
        return 'B'
    return None

@step
def report_c(grade: int) -> str:
    if grade < 70:
        return 'C'
    return None

@pipeline(dynamic=True)
def my_pipeline():
    grade = get_grade().load()  # Get the grade value for control flow
    if grade >= 90:
        report = report_a(grade=grade)
    elif 70 <= grade < 90:
        report = report_b(grade=grade)
    else:
        report = report_c(grade=grade)

if __name__ == "__main__":
    my_pipeline()
