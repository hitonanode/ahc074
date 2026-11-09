"""集計 JSON を PROGRESS に転記する。符号は候補−基準。"""
import argparse
import json
from pathlib import Path

def pm(x,n=3): return f"{x['mean']:+.{n}f} ± {x['se']:.{n}f}"

def render(data,title,decision):
    out=[f'\n## {title}\n']
    for x in data:
        out.append(f"- {x['n']} 件: `{x['base']}` → `{x['candidate']}`。WA {x['wa']}。")
    out.extend(['','|候補|score % ± SE|W/T/L|dv_best 差 ± SE|helper ms ± SE|req ms ± SE|end ms ± SE|時間料 % / 差引改善 %|',
                '|---|---:|---|---:|---:|---:|---:|---:|'])
    for x in data:
        m=x['metrics']; name=x['candidate'].split('_',1)[1]
        out.append('|'+name+'|'+pm(x['score_pct'],5)+'|'+'/'.join(map(str,x['wtl']))+'|'+
                   (pm(m['dv_best']['difference'],6) if 'dv_best' in m else '-')+'|'+
                   '|'.join(pm(m[k]['difference'],2) for k in ['helper_end_sec','req_sec','end_sec'])+
                   f"|{x['time_charge_pct']:+.5f} / {x['net_improvement_pct']:+.5f}|")
    out.extend(['','時間 p99（基準 → 候補、helper / req / end、ms）:',''])
    for x in data:
        m=x['metrics']; name=x['candidate'].split('_',1)[1]
        out.append('- '+name+': '+', '.join(f"{m[k]['base_p99']:.2f} → {m[k]['candidate_p99']:.2f}" for k in ['helper_end_sec','req_sec','end_sec'])+'。')
    out.extend(['',decision,''])
    return '\n'.join(out)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('json',type=Path);p.add_argument('title');p.add_argument('decision')
    args=p.parse_args();s=render(json.loads(args.json.read_text()),args.title,args.decision)
    with (Path(__file__).resolve().parent/'PROGRESS.md').open('a') as f:f.write(s)
    print(s)
