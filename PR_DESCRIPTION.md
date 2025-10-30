## Describe changes
I implemented a simple materializer for Path objects that lets you handle files and directories in your pipeline:

# New Feature: Path Materializer for Directory Artifacts

## Overview
This PR introduces a new `PathMaterializer` class that enables ZenML pipelines to handle entire directory structures as artifacts. This materializer works with `pathlib.Path` objects, preserving the complete directory structure including all files and subdirectories.

## Key Features
- **Complete Directory Preservation**: Store and retrieve entire directory structures with all their contents intact
- **Flexible Path Handling**: Works with both individual files and complete directory structures

## Implementation Details
- Efficiently compresses directories to `.tar.gz` format for storage
- Extracts archives to temporary directories when loading
- Handles both individual files and entire directories

## Documentation
- Added a detailed guide for using directory artifacts: `directory-artifacts.md`
- Updated the materializers table in the data handling documentation
- Added the new materializer to the table of contents

## How to Use
```python
from pathlib import Path
from zenml import step, pipeline

@step
def create_directory() -> Path:
    # Create a directory with files
    temp_dir = Path("./my_data_directory")
    temp_dir.mkdir(exist_ok=True)
    (temp_dir / "data.csv").write_text("id,value\n1,100\n2,200")
    return temp_dir

@step
def use_directory(dir_path: Path):
    # Use the directory in another step
    print(f"Contents: {list(dir_path.glob('**/*'))}")
    
@pipeline
def directory_pipeline():
    dir_path = create_directory()
    use_directory(dir_path)
```

This PR enables a much-requested workflow for users who need to work with complex directory structures in their ML pipelines.

## Pre-requisites
Please ensure you have done the following:
- [ ] I have read the **CONTRIBUTING.md** document.
- [ ] I have added tests to cover my changes.
- [ ] I have based my new branch on `develop` and the open PR is targeting `develop`. If your branch wasn't based on develop read [Contribution guide on rebasing branch to develop](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md#-pull-requests-rebase-your-branch-on-develop).
- [ ] **IMPORTANT**: I made sure that my changes are reflected properly in the following resources:
  - [ ] [ZenML Docs](https://docs.zenml.io)
  - [ ] Dashboard: Needs to be communicated to the frontend team.
  - [ ] Templates: Might need adjustments (that are not reflected in the template tests) in case of non-breaking changes and deprecations.
  - [ ] [Projects](https://github.com/zenml-io/zenml-projects): Depending on the version dependencies, different projects might get affected.

## Types of changes
<!--- What types of changes does your code introduce? Put an `x` in all the boxes that apply: -->
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Other (add details above) 