#!/usr/bin/env python3
"""Build a byte-exact standalone C++ file from the pinned baseline and patches."""
import argparse,gzip,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def digest(data):return hashlib.sha256(data).hexdigest()
def apply(source,patch):
    old=source.decode('utf-8').splitlines(keepends=True)
    lines=patch.decode('utf-8').splitlines(keepends=True)
    result=[];cursor=0;i=0
    while i<len(lines):
        match=re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',lines[i])
        if not match:i+=1;continue
        start=int(match[1])-1;old_count=int(match[2] or 1);new_count=int(match[4] or 1)
        if not old_count:start+=1
        if start<cursor:raise ValueError('overlapping/out-of-order patch hunk')
        result.extend(old[cursor:start]);cursor=start;i+=1;used=added=0
        while i<len(lines) and not lines[i].startswith('@@ '):
            line=lines[i]
            if line.startswith('\\ No newline'):raise ValueError('unsupported missing final newline')
            if not line or line[0] not in ' +-':break
            tag,text=line[0],line[1:]
            if tag in ' -':
                if cursor>=len(old) or old[cursor]!=text:raise ValueError(f'patch context mismatch at line {cursor+1}')
                cursor+=1;used+=1
            if tag in ' +':result.append(text);added+=1
            i+=1
        if (used,added)!=(old_count,new_count):raise ValueError('patch hunk line count mismatch')
    result.extend(old[cursor:]);return ''.join(result).encode('utf-8')

def build(profile):
    manifest=json.loads((ROOT/'source-manifest.json').read_text())
    result=(ROOT/'baseline.cpp').read_bytes()
    if digest(result)!=manifest['baseline']['sha256']:raise ValueError('baseline hash mismatch')
    entry=manifest['profiles'][profile]
    for name in entry['patches']:
        data=((ROOT/name).read_bytes() if (ROOT/name).exists() else
              b''.join((ROOT/part).read_bytes() for part in manifest['patch_parts'][name]))
        if digest(data)!=manifest['patches'][name]:raise ValueError(f'patch hash mismatch: {name}')
        result=apply(result,gzip.decompress(data) if name.endswith('.gz') else data)
    if digest(result)!=entry['sha256']:raise ValueError('generated source hash mismatch')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',choices=['lean','research','wide']);p.add_argument('output',type=Path)
    p.add_argument('--force',action='store_true');a=p.parse_args();data=build(a.profile)
    if a.output.exists() and a.output.read_bytes()!=data and not a.force:p.error('output exists; choose a new path or pass --force')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(data)
    print(f'{a.output}: sha256={digest(data)}')
if __name__=='__main__':main()
