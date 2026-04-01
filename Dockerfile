FROM python:3.12-slim AS base

LABEL org.opencontainers.image.source="https://github.com/simpli-support/simpli-core"
LABEL org.opencontainers.image.description="Simpli Core SDK"

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir . \
    && useradd --no-create-home --shell /bin/false appuser

USER appuser

ENTRYPOINT ["simpli-core"]
CMD ["version"]
