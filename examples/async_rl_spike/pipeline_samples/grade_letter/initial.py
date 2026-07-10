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
def grading_pipeline():
    grade = get_grade()  # returns artifact handle
    grade_value = grade.load()  # get the actual value for control flow
    
    # Use control flow to determine which report step to run
    if grade_value >= 90:
        report = report_a(grade=grade_value)
    elif grade_value >= 70:
        report = report_b(grade=grade_value)
    else:
        report = report_c(grade=grade_value)
    
    # Return the final result (only one report step runs)
    return report

if __name__ == "__main__":
    grading_pipeline()
