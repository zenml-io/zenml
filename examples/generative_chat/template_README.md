# 💬 Generative Chat with Langchain and Llama Index

<MOTIVATION OF WHY THIS IS RELEVANT>

## 🗺 Overview

<HOW THIS INTERFACES WITH ZENML>

## 🧰 How the example is implemented

<WHAT SHOULD THE USER EXPECT WHEN GOING THROUGH THE EXAMPLE>

<HIGHLIGHT INTERESTING CODE SNIPPETS>

<OPTIONALLY SHOW INTERESTING GRAPHICS OF WHAT OUTPUT TO EXPECT>

<IN CASE OF HIGH COMPLEXITY: AN ARCHITECTURE DIAGRAM>

# 🖥 Run it locally

## ⏩ SuperQuick `generative_chat` run

## 👣 Step-by-Step

### 📄 Prerequisites

In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml[server]

# install ZenML integrations
zenml integration install langchain llama_index

# pull example
zenml example pull generative_chat
cd zenml_examples/generative_chat

# Initialize ZenML repo
zenml init

# Start the ZenServer to enable dashboard access
zenml up
```

### ▶️ Run the Code

Now we're ready. Execute:

```bash
python run.py
```

### 🧽 Clean up

In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```
