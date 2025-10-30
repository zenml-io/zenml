from typing_extensions import Annotated
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
# import db_dtypes  # Import for DB date types

from zenml import pipeline, step
from zenml.config import DockerSettings
import site
import sys
from pathlib import Path
from typing import Any
import zenml
from zenml.config import DockerSettings


def get_docker_settings(skip_parent_build: bool = False, **kwargs: Any) -> DockerSettings:
    settings_kwargs = {
        "build_config": {
            "build_options": {
                "platform": "linux/amd64",
            }
        },
        "python_package_installer": "uv",
    }

    if not skip_parent_build:
        for path in site.getsitepackages() + [site.getusersitepackages()]:
            if Path(path).resolve() in Path(zenml.__file__).resolve().parents:
                # Not an editable install
                break
        else:
            # Editable install, add parent build for local files
            zenml_git_root = Path(zenml.__file__).parents[2]
            settings_kwargs.update(
                {
                    "dockerfile": str(zenml_git_root / "docker" / "zenml-dev.Dockerfile"),
                    "build_context_root": str(zenml_git_root),
                    "parent_image_build_config": {
                        "build_options": {
                            "platform": "linux/amd64",
                            "buildargs": {
                                "PYTHON_VERSION": f"{sys.version_info.major}.{sys.version_info.minor}"
                            },
                        }
                    },
                }
            )

    settings_kwargs.update(kwargs)
    return DockerSettings(**settings_kwargs)


@step(settings={"docker": get_docker_settings(requirements=["db_dtypes", "pandas", "numpy"], python_package_installer="uv")})
def generate_dummy_data() -> Annotated[pd.DataFrame, "dummy_data"]:
    """Generate dummy data with various data types including dbdate."""
    import db_dtypes
    # Create a base date and generate a range of dates
    base_date = datetime(2023, 1, 1)
    dates = [base_date + timedelta(days=i) for i in range(100)]
    
    # Generate random numerical data
    numeric_data = np.random.randn(100, 3)
    
    # Create categories
    categories = np.random.choice(['A', 'B', 'C'], size=100)
    
    # Create the DataFrame
    df = pd.DataFrame({
        'date': dates,                           # standard datetime column
        'value1': numeric_data[:, 0],            # float column
        'value2': numeric_data[:, 1],            # float column
        'value3': numeric_data[:, 2],            # float column
        'category': categories,                  # categorical column
        'integer': np.random.randint(0, 100, 100)  # integer column
    })
    
    # Convert the standard date column to dbdate explicitly
    df['db_date'] = pd.Series(dates, dtype='dbdate')
    
    print(f"Generated DataFrame with shape: {df.shape}")
    print(f"Data types: {df.dtypes}")
    
    return df


@step(settings={"docker": get_docker_settings(requirements=["pyarrow", "pandas", "numpy"], python_package_installer="uv")})
def process_data(df: pd.DataFrame) -> Annotated[pd.DataFrame, "processed_data"]:
    """Process the dummy data to demonstrate data manipulation with dbdate."""
    # Convert dbdate to datetime64 to use datetime accessors
    datetime_series = df['db_date'].astype('datetime64[ns]')
    
    # Add columns based on converted datetime
    df['year'] = datetime_series.dt.year
    df['month'] = datetime_series.dt.month
    df['day_of_week'] = datetime_series.dt.day_name()
    
    # Some simple aggregations
    grouped = df.groupby('month').agg({
        'value1': 'mean',
        'value2': 'sum',
        'integer': 'max'
    }).reset_index()
    
    print(f"Processed data shape: {grouped.shape}")
    return grouped


@pipeline(enable_cache=False)
def dummy_data_pipeline():
    """Pipeline that generates and processes dummy data including dbdate values."""
    data = generate_dummy_data()
    processed = process_data(data)
    return processed


if __name__ == "__main__":
    # Run the pipeline
    result = dummy_data_pipeline()
    
    # Fetch the last run
    from zenml.client import Client
    
    pipeline = Client().get_pipeline("dummy_data_pipeline")
    last_run = pipeline.last_run
