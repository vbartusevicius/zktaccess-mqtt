FROM tobix/pywine:3.8

RUN wine python -m pip install --no-cache-dir poetry==1.6.1 \
    && wine poetry config virtualenvs.create false

COPY build/pull_sdk.zip .
RUN unzip -q pull_sdk.zip -d /sdk_temp \
    && cp /sdk_temp/SDK-Ver2.2.0.220/pl*.dll ${WINEPREFIX}/drive_c/windows/system32/ \
    && rm -rf /sdk_temp pull_sdk.zip

RUN echo '#!/bin/bash\nexec "$@"' > /entrypoint.sh \
    && chmod +x /entrypoint.sh


WORKDIR /app

COPY pyproject.toml .
COPY src/ ./src/
COPY .env .

RUN wine poetry install --no-interaction --no-ansi

ENTRYPOINT ["/entrypoint.sh"]
CMD ["wine", "poetry", "run", "python", "./src/main.py"]
