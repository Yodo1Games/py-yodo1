#!/usr/bin/env bash

set -e
set -x

flake8 yodo1 --count --show-source --statistics --config .config.ini
mypy yodo1 --config-file=.config.ini
