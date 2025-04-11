FROM python:3.12-slim AS build

WORKDIR /app

ARG INSTALL_DEV=false

COPY requirements.txt .
COPY requirements-dev.txt .
COPY src/ ./src/
COPY .env .

# Install dependencies with optimized settings and increased verbosity
RUN pip install --no-cache-dir --verbose --timeout 300 \
    $(if [ "$INSTALL_DEV" = "true" ]; then echo "-r requirements-dev.txt"; else echo "-r requirements.txt"; fi)

CMD ["python", "./src/main.py"]
