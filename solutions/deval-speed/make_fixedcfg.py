"""Compile the normal request configuration as constants (no algorithm change)."""
from pathlib import Path
import argparse
ROOT=Path(__file__).resolve().parents[2]
VALUES=dict(mode=1,rounds=2,short_rounds=0,post_candidates=3,interior=0,pair_filter=1,
one=True,two=True,triples=False,recheck=False,trace=False,predict=False,new_only=True,alternate=False,
delete_only=False,alternate_gap=.75,plan_limit=1,plan_ejects=2,plan_priority=0,plan_gap=1e9,plan_reuse=True,
plan_stop=False,plan_trace=False,memo=True,prefix=True,joint_limit=0,joint_stop=False,three_hidden=False,
plan_skip_edited=True,plan_screen=True,refine_best=0,collect=True,plan_distinct=True,candidate_mode=2,
candidate_priority=1,one_limit=0,plan_shortlist=2,repeat_min=0.,lazy_tail=True,one_anchors=2,three_extra=False,
pair_owners=True,hidden_rank=True,promising_slack=.75)
def transform(s,values=VALUES):
    start=s.index('    struct SearchConfig {');end=s.index('    static const SearchConfig& search_config()',start)
    code='    // Fixed request budgets enable constant propagation of the ordinary search.\n    struct SearchConfig {\n'
    for k,v in values.items():
        typ='bool' if isinstance(v,bool) else 'int' if isinstance(v,int) else 'double'
        val=str(v).lower()
        code+=f'        static constexpr {typ} {k} = {val};\n'
    return s[:start]+code+'    };\n'+s[end:]
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--parent',default='deval-vbranch-o3');p.add_argument('--name',default='deval-fixedcfg');a=p.parse_args()
    d=ROOT/'solutions'/a.name;d.mkdir(exist_ok=True)
    s=transform((ROOT/'solutions'/a.parent/'main.cpp').read_text())
    (d/'main.cpp').write_text(s)
    (d/'README.md').write_text(f'''# {a.name}

改良元: solutions/{a.parent}。

SearchConfigを通常設定と同じコンパイル時定数に置き換える。実行時のF3_*設定を読み込む経路を除き、通常設定では使わない分岐をコンパイラが消せるようにする。探索の列挙順、予算、評価式は通常設定のまま。SearchConfigのF3_*環境変数はこの版では使えず、設定を変える場合は再生成する。提出用の時間ガードとLOCAL_BENCH時の固定予算を維持する。
''')
    print(d,len(s.encode()))
