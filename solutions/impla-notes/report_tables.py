"""REPORT用。保存済み集計から転記し、数値の手入力を避ける。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def pm(x,n=4):return f"{x['mean']:+.{n}f} ± {x['se']:.{n}f}"

def rows(specs,with_v=False):
    out=[]
    for file,indices,reference in specs:
        data=json.loads((ROOT/(file+'.json')).read_text())
        for i in indices:
            x=data[i];m=x['metrics']
            out.append('|`'+x['candidate']+'`|'+reference+'|'+str(x['n'])+'|'+pm(x['score_pct'])+'|'+'/'.join(map(str,x['wtl']))+'|'+(pm(m['dv_best']['difference'],6)+'|' if with_v else '')+' / '.join(pm(m[k]['difference'],2) for k in ['helper_end_sec','req_sec','end_sec'])+'|')
    return '\n'.join(out)

HEADER='|候補 run-id|基準|件数|score % ± SE|W/T/L|時間差 ms ± SE（helper / req / end）|\n|---|---|---:|---:|---|---|\n'

def table(specs,with_v=False):
    header=HEADER
    if with_v:
        header=header.replace('|時間差','|dv_best 差 ± SE|時間差').replace('|---|---|---:|---:|---|---|','|---|---|---:|---:|---|---:|---|')
    return header+rows(specs,with_v)

if __name__=='__main__':
    import sys
    specs=json.loads(sys.argv[1]);print(table(specs))
