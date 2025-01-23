FROM node:23-alpine3.20 AS build-frontend
COPY frontend /frontend
RUN cd frontend && yarn install && yarn run build

FROM python:3.13-alpine3.20 AS build-backend
RUN apk add poppler-utils tesseract-ocr tesseract-ocr-data-ces
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock /app/
RUN cd /app && poetry install --no-directory --no-cache --without dev && rm -rf /root/.cache/pypoetry/{artifacts,cache}
COPY templates /app/templates/
COPY *.py /app/
COPY --from=build-frontend /frontend/dist/index.html /app/index.html
WORKDIR "/app"
ENTRYPOINT ["poetry", "run", "fastapi", "run"]
