from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
for name,mode in [('deval-head-jitter15',1),('deval-head-jitter50',2),('deval-head-all1',3),('deval-head-all0',4)]:
 s=b.replace('    explicit Perforation(Solver& solver)','    int head_mode = 0;\n    explicit Perforation(Solver& solver, int mode=0)',1)
 s=s.replace('        assert(H <= Capacity);','        head_mode=mode;\n        assert(H <= Capacity);',1)
 s=s.replace('if (heads.empty() ? frequency[k] != max_frequency[c][b] : k != heads[c][b]) continue;','if (heads.empty() ? (head_mode<3 && frequency[k] != max_frequency[c][b]) : k != heads[c][b]) continue;',1)
 s=s.replace('''            if (frequency[k] == max_frequency[c][b] && (best[c][b] < 0 || utility[k] > utility[best[c][b]]))
                best[c][b] = k;''','''            auto score=[&](int x) {
                double v=utility[x];
                if(head_mode==3)v*=double(frequency[x])/max_frequency[c][b];
                if(head_mode==1 || head_mode==2) {
                    u64 z=(u64(x)+1)*0x9e3779b97f4a7c15ULL+deval_seed_salt();
                    z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;z=(z^(z>>27))*0x94d049bb133111ebULL;z^=z>>31;
                    v*=1+(head_mode==1?.15:.5)*(2*(z>>11)*0x1.0p-53-1);
                }
                return v;
            };
            if ((head_mode>=3 || frequency[k] == max_frequency[c][b]) &&
                (best[c][b] < 0 || score(k) > score(best[c][b]))) best[c][b]=k;''',1)
 s=s.replace('Perforation<Capacity> perforation(solver);',f'Perforation<Capacity> perforation(solver,extra==2?{mode}:0);',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-ordered8`。\n\n穴を保存する2回の再仕上げだけ、穴あけ対象の代表紙の選び方を変える。mode={mode}: 1/2は同色の最大頻度紙のfiller価値に固定ハッシュから±15%/50%の揺らぎを付ける。3/4は単独注文の紙も含め、価値×相対頻度/価値のみで選ぶ。残りの穴あけ・再割当ては同じ。Vで8候補から選ぶ。全探索量は固定で、時間不足による切り替えはない。\n')
 print(name,len(s.encode()))
for samples in [16,32]:
 name=f'deval-warm-s{samples}'
 s=b.replace('template<int Capacity>\nstruct Perforation {','template<int Capacity, int Samples=8>\nstruct Perforation {',1).replace('static constexpr int kSamples = 8;','static constexpr int kSamples = Samples;',1)
 s=s.replace('auto perforate = [&]<int Capacity>() {','auto perforate = [&]<int Capacity,int Samples=8>() {',1).replace('Perforation<Capacity> perforation(solver);','Perforation<Capacity,Samples> perforation(solver);',1)
 s=s.replace('''    if (solver.H <= 25) perforate.template operator()<25>();
    else perforate.template operator()<64>();''',f'''    if(extra==2) {{
        if(solver.H<=25)perforate.template operator()<25,{samples}>();
        else perforate.template operator()<64,{samples}>();
    }} else if (solver.H <= 25) perforate.template operator()<25>();
    else perforate.template operator()<64>();''',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-ordered8`。\n\n穴を保存する2回の再仕上げだけ、穴あけの色状態サンプルを8から{samples}に増やす。層化抽出と固定seedを維持。候補は全8個、Vで選ぶ。探索量は固定、時間不足による切り替えはない。\n')
 print(name,len(s.encode()))
