# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11.9-slim-bullseye

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

ARG SVC_DIR

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ${SVC_DIR} /app/
RUN python -m pip install --upgrade pip
RUN python -m pip install --trusted-host pypi.python.org -r requirements.txt
CMD ["python", "main.py"]