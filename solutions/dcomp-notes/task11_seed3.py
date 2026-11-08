from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-t11-seed-one/main.cpp').read_text()
def rep(s,a,b):assert s.count(a)==1,(a[:100],s.count(a));return s.replace(a,b)
def write(name,s,desc):
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-seed-one\n\n'+desc+'\n\n追加の親は1→1修復だけ。元の6候補枠を共用する。両コンパイラで共通の固定予算。時計による切替なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
for gap in ['0.15','0.75']:
 s=rep(B,'second.cost>parent_value+0.3','second.cost>parent_value+'+gap)
 write('dcomp-t11-seedone-g'+gap.replace('.',''),s,'追加親の完成費用gapを'+gap+'にする。')
a='''                    for (int pass = 0; pass < (earliest == latest ? 1 : 2); pass++) {
                        const int t = pass ? latest : earliest;'''
s=rep(B,a,'''                    for (int pass = 0; pass < (earliest == latest ? 1 : 2); pass++) {
                        if(secondary_neutral && pass)break;
                        const int t = pass ? latest : earliest;''')
write('dcomp-t11-seedone-early',s,'追加親でだけ、1→1の挿入タイミングを最も早い合法時点に限定する。二つの深さ端点は保つ。元の親はearliest/latestの両方を試す。')
a='''                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), cfg.plan_ejects);
                    ns_plan_calls++;'''
s=rep(B,a,'''                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), cfg.plan_ejects);
                    neutral_seeds.push_back({plan_cost(path.size()),save(),path OP_TAG(,tags)});
                    ns_plan_calls++;''')
write('dcomp-t11-seedone-expanded',s,'追加親の選択肢へ、既に本修復を終えたexpanded計画も加える。使う追加親は最大1個のまま。')
