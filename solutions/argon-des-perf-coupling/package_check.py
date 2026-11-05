"""Read-only source/build/package checks for this continuation's new directories."""
import hashlib
import json
import re
from pathlib import Path

here = Path(__file__).resolve().parent
solutions = here.parent
base_name = 'argon-des-perf-latew105'
names = [
    'argon-des-perf-coupling', 'argon-des-perf-alternate',
    'argon-des-perf-altfocus', 'argon-des-perf-alternate2',
    'argon-des-perf-modelprobe', 'argon-des-perf-altcache',
    'argon-des-perf-modelcolumn', 'argon-des-perf-altbefore',
    'argon-des-perf-altwarm', 'argon-des-colmdp', 'argon-des-colmdp-full',
    'argon-des-genvalue', 'argon-des-genvalue-tie',
    'argon-des-rollout', 'argon-des-rollout-s16',
]
base = (solutions / base_name / 'main.cpp').read_bytes()
marker = re.compile(r'^\s*// ==== (.+) ====$', re.M)
toc = re.compile(r'^//   (.+)$', re.M)
metric = re.compile(r'(?:"|\\n)([A-Za-z_][A-Za-z_0-9]*) = ')
env = re.compile(r'(?:getenv|env_real)\("([A-Z_0-9]+)"')
base_text = base.decode()
base_markers = marker.findall(base_text)
base_metrics = set(metric.findall(base_text))
base_env = set(env.findall(base_text))
rows = []
for name in names:
    directory = solutions / name
    source = (directory / 'main.cpp').read_bytes()
    text = source.decode()
    markers = marker.findall(text)
    assert toc.findall(text.split('#include', 1)[0]) == markers, (name, 'TOC')
    assert [m for m in markers if m in base_markers] == base_markers, (name, 'base markers')
    assert base_metrics <= set(metric.findall(text)), (name, 'metrics removed')
    assert base_env <= set(env.findall(text)), (name, 'switches removed')
    assert (directory / 'README.md').read_text().splitlines()[0] == '改良元: solutions/' + base_name
    for token in ['CLOCK_SCALE', 'LOCAL_BENCH', 'DesignStore', '@paper', '@ops',
                  'COLFAST_PROFILE', 'AF_PROFILE', 'F3_PROFILE', 'DESIGN_PROFILE', 'POSET_VERIFY']:
        assert token in text, (name, token)
    assert 'bits/stdc++.h' not in text
    for path in directory.rglob('*'):
        if path.is_file():
            with path.open('rb') as f:
                assert f.read(4) != b'\x7fELF', (name, 'compiled binary', str(path))
    identical = source == base
    row = dict(directory=name, base_identical=identical,
               sha256=hashlib.sha256(source).hexdigest(),
               markers_added=[m for m in markers if m not in base_markers],
               metrics_retained=len(base_metrics), switches_retained=len(base_env))
    if not identical:
        build = json.loads((directory / 'build-results.json').read_text())
        assert build['sha256'] == row['sha256'], (name, 'build source hash')
        assert len(build['results']) == 4
        assert all(r['exit'] == 0 and r['warnings'] == 0 for r in build['results'])
        assert build['temporary_binaries_removed']
        row['warning_free_builds'] = 4
    rows.append(row)
result = dict(base=base_name, directories=len(rows),
              modified_sources=sum(not row['base_identical'] for row in rows),
              warning_free_builds=sum(row.get('warning_free_builds', 0) for row in rows),
              no_elf_binaries=True, rows=rows)
(here / 'package-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, ensure_ascii=False))
