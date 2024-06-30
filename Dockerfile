FROM python:3.12-slim-bookworm as build-stage

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN touch README.md

RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

FROM python:3.12-slim-bookworm as runtime

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
     && apt-get -y install tesseract-ocr

WORKDIR /app

COPY --from=build-stage /app .

ENV PATH="/app/.venv/bin:$PATH"

COPY templates ./templates

COPY *.py .

EXPOSE 443

CMD ["fastapi", "run", "--port", "443"]
