import json
import sys
from pathlib import Path


class EventWriter:
    def __init__(self, root: Path):
        self.root = root

    def emit(self, kind, **payload):
        # stdout is an inherited pipe, not a TCP listener. Never log secrets.
        sys.stdout.write(json.dumps({"type": kind, **payload}, ensure_ascii=True) + "\n")
        sys.stdout.flush()
