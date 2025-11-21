"""Weather Agent Pipeline."""

from pipelines import weather_agent

from zenml.client import Client

if __name__ == "__main__":
    client = Client()

    data_input = input("Enter city to get weather recommendations: ")
    run = weather_agent(city=data_input)

    # # Load and print the output of the last step of the last run
    # run = client.get_pipeline_run(run.id)
    if run:
        result = run.steps["analyze_weather_with_llm"].output.load()
        comparison = run.steps["compare_city_trends"].output.load()
        print(result)
        print("\n" + comparison)
