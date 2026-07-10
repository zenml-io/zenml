from zenml import step, pipeline

@step
def apply_term(value: int, term: int, subtract: bool) -> int:
    if subtract:
        return value - term
    else:
        return value + term

@pipeline(dynamic=True)
def my_pipeline():
    running_value = 10  # start with 10
    terms = [1, 2, 3, 4]
    subtract_flags = [True, False, True, False]  # alternate starting with True
    
    # Loop over terms and flags to apply each term
    for term, subtract in zip(terms, subtract_flags):
        running_value = apply_term(
            value=running_value.load(),
            term=term,
            subtract=subtract
        ).load()

if __name__ == "__main__":
    my_pipeline()
