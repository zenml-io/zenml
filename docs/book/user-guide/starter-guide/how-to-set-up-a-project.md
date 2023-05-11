---
description: Recommended repository structure and best practices.
---

# How to set up a Project

Until now, you probably have kept all your code in one single file. In production it is recommended to split up your steps and pipelines into separate files.

```markdown
.
├── steps
│   ├── loader_step
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── loader_step.py
│   │   └── requirements.txt
│   └── training_step
│       └── ...
├── pipelines
│   ├── training_pipeline
│   │   ├── .dockerignore
│   │   ├── config.yaml
│   │   ├── Dockerfile
│   │   ├── training_pipeline.py
│   │   └── requirements.txt
│   └── deployment_pipeline
│       └── ...
├── notebooks
│   └── *.ipynb
├── .dockerignore
├── .gitignore
├── .zen
├── Dockerfile
├── README.md
├── requirements.txt
└── run.py
```

#### Steps

Keep your steps in separate python files. ...

#### Pipelines

Just like steps, keep your pipelines in separate python files. ...

#### Notebooks

Collect all your notebooks in one place.&#x20;





