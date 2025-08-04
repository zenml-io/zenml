"""Step for loading sample data."""

from typing import List

from zenml import step


@step
def load_sample_articles() -> List[str]:
    """Load sample articles to demonstrate prompt usage.

    Returns:
        List of article texts for summarization
    """
    articles = [
        """
        Machine learning is a subset of artificial intelligence that focuses on 
        algorithms that can learn and make decisions from data. Unlike traditional 
        programming where explicit instructions are given, machine learning systems 
        improve their performance through experience. The field has revolutionized 
        industries from healthcare to finance, enabling applications like image 
        recognition, natural language processing, and predictive analytics. Common 
        approaches include supervised learning, unsupervised learning, and 
        reinforcement learning, each suited to different types of problems and data.
        """.strip(),
        """
        Python has become one of the most popular programming languages due to its 
        simplicity and versatility. Created by Guido van Rossum in 1991, Python 
        emphasizes code readability and allows developers to express concepts in 
        fewer lines compared to languages like C++ or Java. Its extensive standard 
        library and vast ecosystem of third-party packages make it suitable for 
        web development, data science, automation, and artificial intelligence. 
        Major companies like Google, Netflix, and Instagram rely heavily on Python 
        for their core systems and data processing pipelines.
        """.strip(),
        """
        Cloud computing has transformed how businesses approach IT infrastructure 
        and software deployment. Instead of maintaining physical servers and 
        hardware, organizations can leverage remote computing resources provided 
        by companies like Amazon Web Services, Microsoft Azure, and Google Cloud 
        Platform. This shift offers benefits including cost reduction, scalability, 
        improved security, and faster deployment cycles. Cloud services range from 
        basic storage and computing power to sophisticated machine learning platforms 
        and serverless computing environments that automatically scale based on demand.
        """.strip(),
    ]

    return articles
