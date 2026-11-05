"""Four sequential warning checks; the caller holds the evaluation lock. Binaries are temporary."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('directory')
a = p.parse_args()
directory = Path(a.directory).resolve()
rows = []
with tempfile.TemporaryDirectory(prefix='argon-des-build-') as temporary:
    for compiler in ['/usr/bin/g++', '/usr/bin/clang++']:
        for local in [False, True]:
            name = ('clang' if 'clang' in compiler else 'gcc') + ('-local' if local else '-judge')
            command = [compiler, '-std=c++23', '-O2', '-Wall', '-Wextra']
            if local:
                command += ['-DLOCAL_BENCH', '-DCLOCK_SCALE=1.1']
            command += [str(directory / 'main.cpp'), '-o', str(Path(temporary) / name)]
            result = subprocess.run(command, capture_output=True, text=True)
            (directory / ('build-' + name + '.log')).write_text(result.stdout + result.stderr)
            row = dict(name=name, exit=result.returncode, warnings=result.stderr.count('warning:'), command=command)
            rows.append(row)
            print(name, row['exit'], row['warnings'], flush=True)
out = dict(sha256=hashlib.sha256((directory / 'main.cpp').read_bytes()).hexdigest(), results=rows,
           temporary_binaries_removed=True)
(directory / 'build-results.json').write_text(json.dumps(out, indent=2) + '\n')
assert all(r['exit'] == 0 and r['warnings'] == 0 for r in rows)
