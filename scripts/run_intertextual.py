#!/usr/bin/env python3
"""Run only the intertextual generator (for new book pairs)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from generators import run_generator
from lib.db import get_db

conn = get_db()
result = run_generator(conn, "Intertextual — Quotation Detection")
print(f"Status: {result.get('status', 'done')}")
print(f"Connections: {result.get('connections', 0)}")
if 'error' in result:
    print(f"Error: {result['error']}")
conn.close()
