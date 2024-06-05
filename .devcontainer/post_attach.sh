#!/bin/sh
set -ex
pre-commit install --install-hooks --overwrite
cd frontend
yarn install --frozen-lockfile
