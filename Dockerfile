FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       unzip \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry==1.6.1 \
    && poetry config virtualenvs.create false

COPY build/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app

ARG INSTALL_DEV=false

COPY pyproject.toml .
COPY src/ ./src/
COPY .env .

RUN if [ "$INSTALL_DEV" = "true" ]; then \
        poetry install --no-interaction --no-ansi; \
    else \
        poetry install --no-interaction --no-ansi --without dev; \
    fi

ENTRYPOINT ["/entrypoint.sh"]
CMD ["poetry", "run", "python", "./src/main.py"]
