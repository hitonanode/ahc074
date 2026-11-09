#!/usr/bin/env python3
"""Check submit.cpp against main.cpp under the two production builds (run it under the evaluation lock).

usage: check_submit.py [DIR]   (DIR: this directory; it holds main.cpp and submit.cpp)

For each build (GCC: g++ -std=gnu++23 -O2 -march=native -ftrivial-auto-var-init=zero; Clang: clang++
-std=gnu++23 -O2 -march=native -stdlib=libc++ -ftrivial-auto-var-init=zero):
- the -E -P outputs of main.cpp and submit.cpp, compared as token streams (solutions/dcomp-notes/
  trim_tool.py's token_stream: whitespace normalized, literals kept byte for byte);
- the warnings of a full -Wall compile (-c to /dev/null) of each file, and the ones only submit.cpp has.
The temporary outputs go to a temporary directory (nothing is written in DIR).
"""
import importlib.util
import re
import subprocess
import sys

sys.dont_write_bytecode = True  # no __pycache__ next to trim_tool.py
import tempfile
from pathlib import Path

here = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent).resolve()
root = here.parents[1]
spec = importlib.util.spec_from_file_location('trim_tool', root / 'solutions/dcomp-notes/trim_tool.py')
trim = importlib.util.module_from_spec(spec)
sys.modules['trim_tool'] = trim  # its dataclasses look the module up while it loads
spec.loader.exec_module(trim)

BUILDS = {
    'gcc': ['g++', '-std=gnu++23', '-O2', '-march=native', '-ftrivial-auto-var-init=zero'],
    'clang': ['clang++', '-std=gnu++23', '-O2', '-march=native', '-stdlib=libc++', '-ftrivial-auto-var-init=zero'],
}
WARN = re.compile(r'^[^:\n]*:(\d+):(\d+): warning: (.*)$', re.M)


def run(cmd):
    return subprocess.run(['nice', '-n', '10'] + cmd, capture_output=True, text=True)


def warnings(text):
    # the warning texts without their positions (the positions move with the trimmed comments)
    return sorted(m.group(3) for m in WARN.finditer(text))


ok = True
with tempfile.TemporaryDirectory() as tmp:
    for name, cmd in BUILDS.items():
        streams = {}
        for f in ('main.cpp', 'submit.cpp'):
            out = Path(tmp) / f'{name}-{f}.i'
            r = run(cmd + ['-E', '-P', str(here / f), '-o', str(out)])
            if r.returncode:
                print(name, f, 'preprocess failed', r.stderr[-2000:]); ok = False; continue
            streams[f] = trim.token_stream(out.read_text(errors='surrogateescape'))
        same = streams.get('main.cpp') == streams.get('submit.cpp')
        print('%s: -E -P token streams %s (%d tokens)' % (name, 'identical' if same else 'DIFFERENT', len(streams.get('main.cpp', []))))
        ok &= same
        warns = {}
        for f in ('main.cpp', 'submit.cpp'):
            r = run(cmd + ['-Wall', '-c', str(here / f), '-o', '/dev/null'])
            if r.returncode:
                print(name, f, 'compile failed', r.stderr[-2000:]); ok = False
            warns[f] = warnings(r.stderr)
        extra = list(warns['submit.cpp'])
        for w in warns['main.cpp']:
            if w in extra: extra.remove(w)
        missing = list(warns['main.cpp'])
        for w in warns['submit.cpp']:
            if w in missing: missing.remove(w)
        print('%s: -Wall warnings main.cpp %d, submit.cpp %d; only in submit.cpp: %s; only in main.cpp: %s' % (
            name, len(warns['main.cpp']), len(warns['submit.cpp']), extra or 'none', missing or 'none'))
print('all identical' if ok else 'CHECK FAILED')
sys.exit(0 if ok else 1)
