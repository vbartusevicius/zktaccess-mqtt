FROM tobix/pywine:3.8

RUN wine python -m pip install --no-cache-dir poetry==1.6.1

COPY pyproject.toml .

RUN wine poetry config virtualenvs.create false \
    && wine poetry install --no-interaction --no-ansi


COPY build/pull_sdk.zip .
RUN unzip -q pull_sdk.zip -d /sdk_temp \
    && cp /sdk_temp/SDK-Ver2.2.0.220/pl*.dll ${WINEPREFIX}/drive_c/windows/system32/ \
    && rm -rf /sdk_temp pull_sdk.zip

WORKDIR /app

COPY src/ ./src/
COPY .env .

CMD ["wine", "poetry", "run", "python", "./src/main.py"]
