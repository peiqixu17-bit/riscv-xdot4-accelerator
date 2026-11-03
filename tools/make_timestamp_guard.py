#!/usr/bin/env python3
"""GNU Make adapter for freshly generated DrvFS inputs; never changes mtimes.

Pass this executable through the candidate's existing --make option.
All original GNU Make arguments and its eventual exit status are preserved.
"""
import json
import shutil
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
args = sys.argv[1:]
make = shutil.which(os.environ.get('GNU_MAKE', 'make'))
if not make: raise SystemExit('GNU Make missing; set GNU_MAKE')
if args == ['--version']:
    os.execv(make, [make, *args])
try:
    index = args.index('-C')
    directory = Path(args[index+1]).resolve(strict=True)
    if not directory.is_dir(): raise ValueError('Not a build directory')
except (ValueError, IndexError, OSError) as exc:
    raise SystemExit('MAKE_GUARD_ERROR: explicit existing -C directory required: '+str(exc))
start = time.monotonic()
initial_ahead = None
while True:
    files = [p for p in directory.rglob('*') if p.is_file()]
    newest = max((p.stat().st_mtime for p in files), default=0)
    ahead = newest - time.time()
    if initial_ahead is None: initial_ahead = ahead
    if ahead <= -1.0: break
    if time.monotonic()-start > 10:
        raise SystemExit('MAKE_GUARD_ERROR: generated input clock offset persists beyond ten seconds')
    time.sleep(0.1)
print('MAKE_TIMESTAMP_GUARD '+json.dumps({'initial_ahead_seconds':initial_ahead,
    'wait_seconds':round(time.monotonic()-start,3),'files_checked':len(files),
    'mtime_changes':0,'make_arguments_unchanged':True}),flush=True)
os.execv(make, [make, *args])
