import pandas as pd
from zenml import step, pipeline



@step
def create_dataframe() -> pd.DataFrame:
    """Create a sample dataframe."""
    import numpy as np
    
    # Create a sample DataFrame
    np.random.seed(42)
    df = pd.DataFrame({
        'A': np.random.rand(100),
        'B': np.random.randint(0, 100, size=100),
        'C': pd.date_range(start='2023-01-01', periods=100),
        'D': [f'Category-{i%5}' for i in range(100)]
    })
    
    return df

# You can also explicitly specify the materializer for a specific step
@step
def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Process the dataframe."""
    # Some processing
    processed_df = df.copy()
    processed_df['A_squared'] = processed_df['A'] ** 2
    processed_df['B_normalized'] = processed_df['B'] / processed_df['B'].max()
    
    return processed_df

@pipeline(enable_cache=False)
def dataframe_visualization_pipeline():
    """Run a simple pipeline that demonstrates DataFrame visualization."""
    df = create_dataframe()
    processed_df = process_dataframe(df)

if __name__ == "__main__":
    # Run the pipeline
    dataframe_visualization_pipeline()
    
    # After running, you can view the DataFrame visualizations in the ZenML dashboard
    # This includes both the default statistical description and the first 10 rows
    print("Pipeline completed. Check your ZenML dashboard to view the DataFrame sample visualization.")