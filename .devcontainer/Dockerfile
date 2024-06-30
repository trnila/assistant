FROM alpine:latest
RUN apk add --no-cache python3 poetry py3-pip git yarn poppler-utils tesseract-ocr tesseract-ocr-data-ces redis bash openssh-client-default
RUN pip3 install ruff pre-commit --break-system-packages
