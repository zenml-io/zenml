FROM python:3.12-slim
WORKDIR /app
# Broken file: missing closing paren on the print call
RUN printf 'print("success"\n' > /app/app.py
