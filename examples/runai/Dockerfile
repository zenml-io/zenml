FROM nvcr.io/nvidia/pytorch:25.02-py3

# Copy and install local ZenML from source
COPY . /zenml
RUN pip install --no-cache-dir /zenml numpy
