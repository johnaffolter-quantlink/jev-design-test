#!/usr/bin/env python3
"""Entry point: `python3 ledger.py <command>`. Logic lives in ledgerlib/."""
import sys
from ledgerlib.cli import main

if __name__ == "__main__":
    sys.exit(main())
