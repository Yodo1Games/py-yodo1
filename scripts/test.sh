#!/usr/bin/env bash

set -e
set -x

export PYTHONPATH=`pwd`
pytest --cov=api --cov-report term tests/
