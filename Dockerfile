FROM node:23-alpine3.20 AS build-frontend
COPY frontend /frontend
RUN cd frontend && yarn install && yarn run build

FROM alpine:edge AS build-backend
RUN apk --no-cache add python3 uv poppler-utils tesseract-ocr tesseract-ocr-data-ces
COPY pyproject.toml uv.lock *.py README.md /app/
COPY templates /app/templates/
RUN cd /app && uv sync --no-cache --no-dev
COPY --from=build-frontend /frontend/dist/index.html /app/index.html
WORKDIR "/app"
ENTRYPOINT ["uv", "run", "--no-sync", "fastapi", "run"]
