from pathlib import Path
r=Path(__file__).resolve().parents[2];b=(r/'solutions/deval-seven-wide/main.cpp').read_text()
for name,extra_count,kind in [('deval-warm9',5,'j>=3'),('deval-warm7',3,'j==1'),('deval-warm10',6,'j%2==1')]:
 s=b
 # Current selected physical design is held in the enclosing state. A warm pass
 # keeps its exact assignment and holes; the natural mask permits restoration.
 s=s.replace('''    if(!raw) {
    if (climb_iters''','''    if(!raw && extra!=2) {
    if (climb_iters''',1)
 needle='''    Solver solver = make_solver(state);
    // Sacrifice a few printed handles'''
 warm='''    Solver solver = make_solver(state);
    const auto natural_opacity=solver.h_opq;
    if(extra==2 && !warm_state.papers.empty()) {
        for(const auto& unit:des->unit) {
            const int k=state.ded[unit.a],old=warm_state.ded[unit.a];
            solver.paper[k]=warm_state.papers[old];
            solver.h_opq[k]=solver.handle_bits(solver.paper[k].opaque);
            solver.h_blk[k]=solver.handle_bits(solver.paper[k].black);
        }
    }
    // Sacrifice a few printed handles'''
 assert needle in s;s=s.replace(needle,warm,1)
 s=s.replace('''        Perforation<Capacity> perforation(solver);
        perforation.run(0.7);''','''        Perforation<Capacity> perforation(solver);
        if(extra==2)perforation.allowed=natural_opacity;
        perforation.run(0.7);''',1)
 s=s.replace('''    auto finish = [&](Design* des,bool raw=false,int extra=0) {''','''    DesignState warm_state;
    auto finish = [&](Design* des,bool raw=false,int extra=0) {''',1)
 s=s.replace('''    for(int j=0;j<3;++j) {''',f'''    for(int j=0;j<{extra_count};++j) {{''',1)
 s=s.replace('''        complete(id,1);''',f'''        const bool warm={kind};
        if(warm)warm_state=state;
        complete(id,warm?2:1);''',1)
 p=r/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'''改良元: `solutions/deval-seven-wide`\n\n最良完成配置の穴あけを保存し、その状態から穴あけと穴あけ後の再割当てだけをやり直す候補を加える。穴の復元も試せるよう、穴あけで変更可能な窓は自然な印刷マスクに戻す。紙の列と対象の対応を使って物理紙を対応付ける。通常の仕上げと同じV16で選ぶ。\n\n最初の4分岐は同じ。追加候補数は{extra_count}、0起算の追加候補jで `{kind}` のとき穴を保存する仕上げを行い、他は元の25k climb＋再割当て＋穴あけ＋最終再割当て。全予算は固定で時間不足による切り替えはない。\n''')
 print(name,len(s.encode()))
