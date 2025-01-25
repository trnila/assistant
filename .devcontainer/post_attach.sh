#!/bin/sh
set -ex
uv sync
uv run pre-commit install --install-hooks --overwrite
cd frontend
yarn install --frozen-lockfile
