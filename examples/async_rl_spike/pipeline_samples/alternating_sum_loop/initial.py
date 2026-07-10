from zenml import step, pipeline

@step
def apply_term(current_value: int, term: int, subtract: bool) -> int:
    if subtract:
        return current_value - term
    else:
        return current_value + term

@pipeline(dynamic=True)
def compute_expression():
    value = 10
    terms = [1, 2, 3, 4]
    subtract_flags = [True, False, True, False]  # alternate starting with True
    
    # Apply each term with its corresponding subtract flag
    for term, subtract in zip(terms, subtract_flags):
        value = apply_term(current_value=value, term=term, subtract=subtract).load()
    
    return value

if __name__ == "__main__":
    compute_expression()
