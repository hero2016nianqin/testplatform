"""Run Alembic commands"""
import sys
from alembic.config import main

if __name__ == "__main__":
    main(prog="alembic", argv=sys.argv[1:] if len(sys.argv) > 1 else ["--help"])
