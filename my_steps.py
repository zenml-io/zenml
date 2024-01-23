from zenml.steps import step
@step
def s1() -> int:
  return 1

@step
def s2(inp: int) -> None:
  pass