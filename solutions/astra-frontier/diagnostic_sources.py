#!/usr/bin/env python3
"""Make transparent diagnostic copies with complete query processing after fixed design work.

These copies exceed the contest time limit. They measure structural potential, not submission score.
All design iteration counts are still supplied via the solvers' existing environment variables.
"""
import argparse
import hashlib
import json
import pathlib
import re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--out', type=pathlib.Path, required=True)
p.add_argument('solutions', nargs='+', type=pathlib.Path)
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
manifest = []
for source in a.solutions:
    original = (source / 'main.cpp').read_text()
    text = original
    changes = []
    for name in ('kFastAfter', 'kHelperGiveUp'):
        text, count = re.subn(r'\b' + name + r'\s*=\s*[0-9.]+', name + ' = 1000000.0', text)
        if count != 1:
            raise SystemExit(f'{source}: expected one {name}, found {count}')
        changes.append(name)
    dest = a.out / ('diag-' + source.name)
    dest.mkdir()
    (dest / 'main.cpp').write_text(text)
    (dest / 'README.md').write_text(
        f'# 固定仕事量診断: {source.name}\n\n改良元: {source.as_posix()}\n\n'
        '提出用ではない。設計の反復数を環境変数で固定し、kFastAfterとkHelperGiveUpだけを1000000秒へ延長する。'
        '後続の注文を設計で読まず、実際の対話と全手の可視性・表示検査を維持する。'
        '結果を2秒制限内のスコアとは扱わない。\n')
    manifest.append({'source':str(source),'destination':str(dest),
                     'source_sha256':hashlib.sha256(original.encode()).hexdigest(),
                     'diagnostic_sha256':hashlib.sha256(text.encode()).hexdigest(),
                     'modified_constants':changes})
(a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
