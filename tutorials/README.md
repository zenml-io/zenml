# ZenML Tutorials

Welcome to the ZenML Tutorials repository! This folder contains Jupyter notebooks that serve as interactive guides and examples for using ZenML, a powerful MLOps framework.

## 📚 About These Tutorials

The notebooks in this directory are the source material for the user guides available on our [official documentation website](https://docs.zenml.io). They are designed to provide hands-on experience with ZenML features and concepts.

## 🔗 Connection to docs.zenml.io

Here's how these tutorials connect to our GitBook documentation:

1. **Source of Truth**: The Jupyter notebooks in this folder are the primary source of content for our user guides.

2. **Automatic Conversion**: We use a GitHub Action to automatically convert these notebooks into Markdown files.

3. **Asset Handling**: Images and other assets used in the notebooks are automatically copied to the appropriate GitBook assets folder and their paths are updated in the Markdown files.

4. **GitBook Integration**: The converted Markdown files and assets are then integrated into our GitBook structure, which powers the user guide section of [docs.zenml.io](https://docs.zenml.io).

5. **Synchronization**: Any updates made to the notebooks or their assets in this folder will be reflected in the online documentation after the conversion process.

## 📁 Directory Structure

Each subdirectory in this `tutorials` folder corresponds to a specific guide or section in our documentation. For example:

- `starter-guide/`: Maps to the [Starter Guide](https://docs.zenml.io/user-guide/starter-guide) section in our docs
- `advanced-guide/`: Maps to the Advanced Guide section
- `production-guide/`: Contains tutorials for production-level MLOps
- `llmops-guide/`: Focuses on Large Language Model Operations

Assets (images, etc.) used in the notebooks should be placed in the same directory as the notebook that uses them.

## 🚀 Running the Tutorials

You can run these tutorials in two ways:

1. **Locally**: Clone this repository and run the notebooks on your local machine.
2. **Google Colab**: Each notebook in our online documentation has a "Open in Colab" button, allowing you to run the tutorials in a cloud environment.

## 🤝 Contributing

We welcome contributions to improve these tutorials! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request on our [GitHub repository](https://github.com/zenml-io/zenml).

## 📚 Additional Resources

- [ZenML Documentation](https://docs.zenml.io/)
- [ZenML GitHub Repository](https://github.com/zenml-io/zenml)
- [ZenML Examples](https://github.com/zenml-io/zenml/tree/main/examples)

Thank you for using ZenML, and happy learning!