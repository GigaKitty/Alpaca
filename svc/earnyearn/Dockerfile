# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11.5-slim-bullseye

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# So we don't get version warnings
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY ./ /app/

RUN pip install --upgrade pip

RUN python -m pip install --trusted-host pypi.python.org -r requirements.txt

CMD ["python", "main.py"]
