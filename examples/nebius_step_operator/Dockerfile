FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime

# Install the checkout's wheel until the integration is in a released ZenML.
COPY wheels/*.whl /tmp/zenml-wheel/
RUN pip install --no-cache-dir /tmp/zenml-wheel/*.whl && rm -rf /tmp/zenml-wheel
