from zenml import step, pipeline

@step
def return_string() -> str:
    """Return a sample string."""
    return "Hello, ZenML!"

@step
def return_int() -> int:
    """Return a sample integer."""
    return 42

@step
def return_bool() -> bool:
    """Return a sample boolean."""
    return True

@step
def return_dict() -> dict:
    """Return a sample dictionary."""
    return {"key1": "value1", "key2": "value2"}

@step
def return_list() -> list:
    """Return a sample list."""
    return [1, 2, 3, 4, 5]

@pipeline(enable_cache=False)
def simple_pipeline():
    """Run a simple pipeline that returns various data types."""
    string_artifact = return_string()
    int_artifact = return_int()
    bool_artifact = return_bool()
    dict_artifact = return_dict()
    list_artifact = return_list()

if __name__ == "__main__":
    # Run the pipeline
    simple_pipeline()
    print("Pipeline completed. Check your ZenML dashboard to view the artifacts.")