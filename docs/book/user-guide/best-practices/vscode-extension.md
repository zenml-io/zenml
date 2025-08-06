---
description: Use the ZenML VSCode extension to manage your ZenML server
icon: computer-mouse
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Using VS Code extension

The ZenML VSCode extension is a tool that allows you to manage your ZenML server\
from within VSCode. It provides features for stack management, pipeline\
visualization, and project management capabilities. You can use it in any IDE\
which allows the installation of extensions from the VSCode Marketplace, which\
means that Cursor also supports this extension.

![ZenML VSCode Extension](../../.gitbook/assets/vscode-extension.gif)

## How to install the ZenML VSCode extension

You can install the ZenML VSCode extension in several ways:

### From the VSCode Marketplace

1. Open VSCode
2. Navigate to the Extensions view (Ctrl+Shift+X or Cmd+Shift+X on macOS)
3. Search for "ZenML"
4. Click "Install"

### From the Command Line

```bash
code --install-extension zenml.zenml-vscode
```

## Features

The ZenML VSCode extension offers several powerful features:

* **Project Management**: Create, manage, and navigate ZenML projects
* **Stack Visualization**: View and manage your ZenML stacks and components
* **DAG Visualization**: Visualize your pipeline DAGs for better understanding
* **Pipeline Run Management**: Monitor and manage your pipeline runs
* **Stack Registration**: Register new stacks directly from VSCode

## Version Compatibility

The ZenML VSCode extension has different versions that are compatible with specific ZenML library versions. For the best experience, use an extension version that matches your ZenML library.

For a detailed compatibility table, refer to the [ZenML VSCode extension repository](https://github.com/zenml-io/vscode-zenml/blob/develop/VERSIONS.md).

### Installing a Specific Version

If you need to work with an older ZenML version:

#### Using VS Code UI:

1. Go to the Extensions view (Ctrl+Shift+X)
2. Search for "ZenML"
3. Click the dropdown next to the Install button
4. Select "Install Another Version..."
5. Choose the version that matches your ZenML library version

#### Using Command Line:

```bash
# Example for installing version 0.0.11
code --install-extension zenml.zenml-vscode@0.0.11
```

For the best experience, we recommend using the latest version of both the ZenML library and the extension:

```bash
pip install -U zenml
```

## Using the Extension

After installation:

1. **Connect to your ZenML server**: Use the ZenML sidebar in VSCode to connect to your ZenML server
2. **Explore your projects**: Browse through your existing projects or create new ones
3. **Visualize pipelines**: View DAGs of your pipelines to understand their structure
4. **Manage stack components**: Visualize and configure stack components
5. **Monitor runs**: Track the status and details of your pipeline runs

## Troubleshooting

If you encounter issues with the extension:

* Ensure your ZenML library and extension versions are compatible
* Check your server connection settings
* Verify that your authentication credentials are correct
* Try restarting VSCode

For more help, visit the [ZenML GitHub\
repository](https://github.com/zenml-io/vscode-zenml) or send us a message on\
our [Slack community](https://zenml.io/slack).
