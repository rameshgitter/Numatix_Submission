#!/bin/bash
# Unset PYTHONPATH to avoid picking up global packages from different Python versions
export PYTHONPATH=""

# Activate virtual environment
source ./venv/bin/activate

# Execute the passed command
exec "$@"
