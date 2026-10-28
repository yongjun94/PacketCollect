import re
import os
from pathlib import Path
import subprocess


def secure_directory(path: Path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        path.chmod(0o700)
    else:
        # Restrict to the current SID; inherited access to new bodies/CA files.
        output = subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"])
        match = re.search(rb"S-1-[0-9-]+", output)
        if match is None:
            raise RuntimeError("Cannot determine current user SID")
        sid = match.group().decode("ascii")
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r",
                        f"*{sid}:(OI)(CI)F"], check=True, capture_output=True)
