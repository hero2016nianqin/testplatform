#!/bin/bash
# Run Alembic migrations with proper Python path setup
# This avoids the naming conflict between the local 'alembic/' directory and the installed alembic package

export PYTHONPATH="$(dirname "$0"):$PYTHONPATH"

python3 -c "
import sys
import os

# Change to backend directory
os.chdir('$(dirname "$0")')

# Add user site-packages
import site
site.addsitedir(site.getusersitepackages())

from alembic.config import main
sys.argv = ['alembic'] + ${@:1}
main(prog='alembic')
"
