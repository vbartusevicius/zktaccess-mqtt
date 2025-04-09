FROM sunpeek/poetry:py3.11-slim as build

RUN poetry config virtualenvs.create false

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

CMD ["poetry", "run", "python", "./src/main.py"]
