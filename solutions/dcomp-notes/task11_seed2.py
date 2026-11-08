from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-t11-neutral-seed03/main.cpp').read_text()
def rep(s,a,b,n=1):assert s.count(a)==n,(s.count(a),a[:100]);return s.replace(a,b)
def write(name,s,desc):
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-neutral-seed03\n\n'+desc+'\n\n二つ目の完成計画をgap .3以内から選ぶ。固定回数を両コンパイラで共用し、時計による切替はない。既存ログ・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
# A scoped flag only changes which neighborhood is enumerated at the second parent.
for name,disable,width,distinct,extra_count in [('seed-one','two',0,False,1),('seed-two','one',0,False,1),('seed-width4','',4,False,1),('seed-width5','',5,False,1),('seed-distinct','',0,True,1),('seed-three','',0,False,2)]:
 s=B
 s=rep(s,'                if(round==1) {\n                    std::stable_sort(neutral_seeds', '                bool used_second=false;\n                if(round==1) {\n                    int second_count=0;\n                    std::stable_sort(neutral_seeds')
 if disable:
  x='    bool neutral_collect = false;';assert s.count(x)==1
  s=s.replace(x,x+'\n    bool secondary_neutral=false;')
  x=' && cfg.'+disable+')';assert s.count(x)==1
  s=s.replace(x,' && cfg.'+disable+' && !secondary_neutral)')
  s=rep(s,'                        neutral_collect=true;\n                        second_path=post_optimize','                        neutral_collect=true;secondary_neutral=true;\n                        second_path=post_optimize')
  s=rep(s,'                        neutral_collect=false;\n                        const double second_value','                        neutral_collect=false;secondary_neutral=false;\n                        const double second_value')
 if distinct:
  s=rep(s,'if(second.state.order==parent_order || second.cost>parent_value+0.3)continue;',
        'if(second.state.order==parent_order || same_family(second.path,parent_path) || second.cost>parent_value+0.3)continue;')
 s=rep(s,'                        restore(incumbent);break;',f'                        used_second=true;restore(incumbent);if(++second_count=={extra_count})break;')
 if width:
  s=rep(s,'                auto proposals = std::move(neutral_candidates);',f'                if(used_second && neutral_candidates.size()>{width})neutral_candidates.resize({width});\n                auto proposals = std::move(neutral_candidates);')
 desc={'seed-one':'追加の親は1→1だけを列挙し、2→2を省く。','seed-two':'追加の親は2→2だけを列挙し、1→1を省く。','seed-width4':'追加の親を使った第一roundだけ、本修復する統合候補を6→4にする。','seed-width5':'追加の親を使った第一roundだけ、本修復する統合候補を6→5にする。','seed-distinct':'元の親と移動紙列が同じ追加親は除き、別の移動紙列を使う。','seed-three':'gap .3内の追加親を最大2個に増やし、元の親と合わせ3個から同じ6候補枠へ集める。'}[name]
 write('dcomp-t11-'+name,s,desc)
