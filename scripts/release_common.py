"""DRAFT — NOT RELEASE-APPROVED. Candidate-only output helpers; not executed in S04A."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]

def source(relative):
    p = (ROOT / relative).resolve()
    if not p.is_relative_to(ROOT) or not p.is_file():
        raise RuntimeError(f"Required candidate source missing or outside candidate: {relative}")
    return p

def new_output(name):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name):
        raise RuntimeError("Output ID must contain only letters, digits, underscore or hyphen")
    base = ROOT / "_runs"
    if base.is_symlink() or not base.resolve().is_relative_to(ROOT):
        raise RuntimeError("Output base escapes candidate")
    base.mkdir(exist_ok=True)
    out = base / name
    out.mkdir(exist_ok=False)
    (out / "tmp").mkdir()
    return out.resolve()

def write_json(path, obj):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")

def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def tool(name):
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"Missing external tool: {name}; configure its CLI option or PATH")
    return str(Path(found).resolve())

def run(argv, out, label, cwd=None, expected=0, reject_warnings=False):
    env = os.environ.copy()
    env.pop("VERILATOR_ROOT", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT),
               TMPDIR=str(out / "tmp"), TMP=str(out / "tmp"), TEMP=str(out / "tmp"),
               XDG_CACHE_HOME=str(out / "tmp"), CCACHE_DISABLE="1", LC_ALL="C")
    work = (cwd or out).resolve()
    if not work.is_relative_to(out):
        raise RuntimeError("Working directory must be within the fresh output directory")
    command = [str(x) for x in argv]
    write_json(out / (label + ".command.json"), {"argv": command, "cwd": str(work)})
    with (out / (label + ".log")).open("x", encoding="utf-8") as log:
        proc = subprocess.run(command, cwd=work, env=env, stdout=log,
                              stderr=subprocess.STDOUT, timeout=600, check=False)
    text = (out / (label + ".log")).read_text(encoding="utf-8", errors="replace")
    if proc.returncode != expected:
        raise RuntimeError(f"{label}: exit {proc.returncode}, expected {expected}; inspect log")
    if reject_warnings and re.search(r"%Warning|warning:|clock skew", text, re.I):
        raise RuntimeError(f"{label}: warning diagnostics require review; inspect log")
    return text
