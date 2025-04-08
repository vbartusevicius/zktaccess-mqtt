FROM tobix/pywine:3.8

RUN wine python -m pip install --no-cache-dir poetry==1.6.1 \
    && wine poetry config virtualenvs.create false

COPY build/pull_sdk.zip .
RUN unzip -q pull_sdk.zip -d /sdk_temp \
    && cp /sdk_temp/SDK-Ver2.2.0.220/pl*.dll ${WINEPREFIX}/drive_c/windows/system32/ \
    && rm -rf /sdk_temp pull_sdk.zip

COPY build/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh


WORKDIR /app

ARG INSTALL_DEV=false

COPY pyproject.toml .
COPY src/ ./src/
COPY .env .

# Conditionally install development dependencies
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        wine poetry install --no-interaction --no-ansi; \
    else \
        wine poetry install --no-interaction --no-ansi --without dev; \
    fi

ENTRYPOINT ["/entrypoint.sh"]
CMD ["wine", "poetry", "run", "python", "./src/main.py"]
