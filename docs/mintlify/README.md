# ZenML Docs

This repository contains scripts and tools to help manage and update the documentation for ZenML. Below is a detailed explanation of the process involved in updating the documentation, including a flowchart to visualize the steps.

## Process Overview

The documentation update process involves several steps to ensure that the latest version of the documentation is correctly processed and deployed. The main script responsible for this is `process_docs_update.py`.

### Steps Involved

1. **Extract Documentation Data**: The script starts by extracting the contents of `docs_data.zip` into a temporary directory called `temp_docs`.

2. **Check Version**: The script checks if the version being processed is the latest version, a new version, or the "Bleeding Edge" version (develop branch).

3. **Copy Files**: Depending on the version, the script copies the documentation files to the appropriate versioned folder.

4. **Update Configuration**: The script updates the `mint.json` configuration file with the new version information, including navigation, anchors, and tabs.

5. **Clean Up**: Finally, the script cleans up the temporary files created during the process.

### Flowchart

Below is a flowchart that visualizes the documentation update process:

![Documentation Update Process](_assets/_zenmldocsflow.png)

### Detailed Steps

1. **Extract Documentation Data**:
   - The script extracts `docs_data.zip` into `temp_docs`.

2. **Check Version**:
   - If the version is "develop", it is set to "Bleeding Edge".
   - If the version is in the existing versions list, it is processed as an old version.
   - If the version is not in the existing versions list, it is processed as a new version.

3. **Copy Files**:
   - The script copies the files from `temp_docs` to the appropriate versioned folder, keeping `README.md` and `_assets` at the root.

4. **Update Configuration**:
   - The script updates the `mint.json` configuration file with the new version, navigation, anchors, and tabs.

5. **Clean Up**:
   - The script removes the `temp_docs` directory to clean up temporary files.

### Example Usage

To update the documentation for a new version, run the following command:

```bash
python _scripts/process_docs_update.py --version <new_version>
```