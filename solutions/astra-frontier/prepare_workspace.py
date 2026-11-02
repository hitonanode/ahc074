#!/usr/bin/env python3
"""Prepare an isolated reproducible evaluation checkout without replacing existing inputs."""
import argparse
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--out', type=pathlib.Path, required=True, help='A new directory that does not exist')
t = p.add_mutually_exclusive_group(required=True)
t.add_argument('--tester', type=pathlib.Path, help='Existing official tester binary to copy')
t.add_argument('--portable-tester', action='store_true', help='Build the audited C++ translation')
p.add_argument('--end', type=int, default=2000)
a = p.parse_args()
out = a.out.resolve()
if out.exists():
    raise SystemExit(f'refusing to replace an existing directory: {out}')
out.mkdir(parents=True)
for name in ('AGENTS.md','README.md','.gitignore','pahcer_config.toml'):
    shutil.copyfile(ROOT/name,out/name)
shutil.copytree(ROOT/'scripts',out/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
(out/'tools').mkdir()
shutil.copytree(ROOT/'tools/src',out/'tools/src')
for name in ('Cargo.toml','Cargo.lock'):
    shutil.copyfile(ROOT/'tools'/name,out/'tools'/name)
selected = ['astra-search4','astra-frontier','astra-structural','astra-structural-fast','astra-earlytable',
            'astra-architecture','astra-sparsegate','astra-sparse12','astra-research','astra-research-look',
            'astra-research-escape','astra-research-g40','astra-cayley','astra-privategate']
allowed = {'.cpp','.hpp','.h','.inc','.py','.md','.json','.csv','.txt'}
for name in selected:
    source=ROOT/'solutions'/name
    if not source.exists(): continue
    for file in source.rglob('*'):
        if file.is_file() and file.suffix in allowed:
            target=out/'solutions'/name/file.relative_to(source)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(file,target)
subprocess.run(['git','init','-b','frontier-evaluation',str(out)],check=True)
tester=out/'tools/target/release/tester'
tester.parent.mkdir(parents=True)
if a.tester:
    shutil.copyfile(a.tester.resolve(),tester)
    tester.chmod(0o755)
else:
    subprocess.run(['g++','-std=c++23','-O2','-pthread',
                    str(out/'solutions/astra-frontier/portable_tester.cpp'),'-o',str(tester)],check=True)
subprocess.run([sys.executable,str(out/'solutions/astra-frontier/generate_cases.py'),
                '--out',str(out/'tools/in'),'--end',str(a.end),
                '--manifest',str(out/'solutions/astra-frontier/cases-manifest.json')],check=True)
print('Ready:',out)
