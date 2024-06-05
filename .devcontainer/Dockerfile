FROM alpine:latest
RUN apk add --no-cache python3 py3-pip git yarn poppler-utils tesseract-ocr tesseract-ocr-data-ces redis bash
COPY ../requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt --break-system-packages
RUN pip3 install ruff pre-commit --break-system-packages

RUN mkdir /assistant
WORKDIR /assistant
