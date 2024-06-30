#!/bin/sh
set -ex
pre-commit install --install-hooks --overwrite
poetry install --no-interaction
cd frontend
yarn install --frozen-lockfile
