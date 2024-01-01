#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

pip3 install . -vv --extra-index-url https://__token__:glpat-fq6C-NTr45Z_Te4BV4kC@git.fiblab.net/api/v4/projects/26/packages/pypi/simple
