#!/usr/bin/env python3
"""全計測の終了後、この研究ディレクトリのバイナリと非圧縮出力だけを消す。"""
from pathlib import Path
import gzip,json
ROOT=Path(__file__).resolve().parent
for label in ['baseline','oracle255-t1','expanded128-k2']:
    files=list((ROOT/'results'/label).glob('*.jsonl'))
    assert len(files)==64
    assert all(len(f.read_text().splitlines())==5 for f in files)
removed=[]
for f in ROOT.rglob('*'):
    if not f.is_file() or f.is_symlink():continue
    with f.open('rb') as stream:head=stream.read(4)
    if head==b'\x7fELF':
        removed.append({'path':str(f.relative_to(ROOT)),'bytes':f.stat().st_size})
        f.unlink()
for f in (ROOT/'results').rglob('*.out'):
    compressed=f.with_suffix(f.suffix+'.gz')
    if compressed.exists():assert gzip.decompress(compressed.read_bytes())==f.read_bytes()
    removed.append({'path':str(f.relative_to(ROOT)),'bytes':f.stat().st_size})
    f.unlink()
(ROOT/'results/cleanup.json').write_text(json.dumps({'removed':removed},ensure_ascii=False,indent=2)+'\n')
print('Removed',len(removed),'binaries / plain outputs,',sum(x['bytes'] for x in removed),'bytes.')
