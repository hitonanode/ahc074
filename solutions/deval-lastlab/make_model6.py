from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
def emit(n,text,d):
 p=root/'solutions'/n;p.mkdir();(p/'main.cpp').write_text(text)
 (p/'README.md').write_text('改良元: `solutions/deval-trim6b`。\n\n'+d+'\n\n設計と候補数・探索回数は同じ。新しい注文列は参照せず、バーコードと現在の状態から評価する。時計による切替えはない。\n')
 assert len(text.encode())<=522000,(n,len(text.encode()))
 print(n,len(text.encode()))
for weight in [.5,1.,2.]:
 x=s.replace('std::vector<double> adaptive_weights;','std::vector<double> adaptive_weights, head_utility;')
 x=x.replace('        double square = 0;','        head_utility=utility;\n        double square = 0;')
 a=x.index('    double adaptive_next_cost(');b=x.index('    // Lexicographic permutation rank',a)
 z=x[a:b].replace('        double cost = 0;','        double cost = 0, head_credit = 0;')
 z=z.replace('                const auto& np=next_paper[key[i]];','                const auto& np=next_paper[key[i]];\n                if(depth==0)head_credit+=head_utility[key[i]];')
 z=z.replace('        cached.size = key_size;',f'        cost-={weight}*head_credit;\n        cached.size = key_size;')
 x=x[:a]+z+x[b:]
 emit('deval-headvalue'+str(int(weight*100)),x,f'列の先頭紙のfiller価値を計画末端に明示する。add_filler_demandで既に求める紙別utilityを保存し、列内の先頭紙の合計×{weight}を費用から引く。取り出し中の紙は除く。既存の重み付き深さ・MDPも残す。')
for w in [.75,1.]:
 emit('deval-genvalue'+str(int(w*100)),s.replace('return 0.5*future[rank];',f'return {w}*future[rank];'),f'汎用紙の末端価値の重みを0.5から{w}にする。')
x=s.replace('Pick best(int s, const Helper& h) const {','Pick best(int s, const Helper& h,const std::vector<double>& future) const {')
x=x.replace('if (d < b.distance || (d == b.distance && g.depth > b.depth)) b = {h.paper, g.state, g.depth, d};','if(d<b.distance || (d==b.distance && (future[g.state]<future[b.goal] || (future[g.state]==future[b.goal] && g.depth>b.depth))))b={h.paper,g.state,g.depth,d};')
x=x.replace('interleave->best(s, h)','interleave->best(s, h, future)')
emit('deval-helper-future',x,'単独helperの汎用紙の到達状態を、移動数が同じなら1注文先の平均費用が小さい方にする。その費用も同じなら従来通り深い挿入先を優先する。')
x=s.replace('if (pk.distance >= base_generic) continue;','if (pk.distance > base_generic) continue;')
emit('deval-helper-equal',x,'単独helperの候補で、汎用紙の移動数がhelperなしと同じ場合も許す。ハンドルの節約を含めて既存の費用で計画を比較する。')
