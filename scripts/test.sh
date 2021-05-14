#!/usr/bin/env bash

set -e
set -x

export PYTHONPATH=`pwd`
pytest --cov=yodo1 --cov=example_api --cov-report term tests/
