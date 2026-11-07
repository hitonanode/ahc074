from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6/main.cpp').read_text()
a=s.index('        std::vector<int> targets(K, 0);',s.index('    void init_colmdp()'))
b=s.index('        for (int c = 0; c < H; c++) {',a)
s=s[:a]+s[b:]
a=s.index('            for (int k = 0; k < K; k++) {',s.index('    void init_colmdp()'))
b=s.index('            // Two weight classes per color',a)
s=s[:a]+s[b:]
s=s.replace('            count.fill(0);weight.fill(0.);\n','')
a=s.index('    // A ColumnMdp per column (init_colmdp, after the adaptive weights; ColMdpConfig).')
b=s.index('    std::vector<ColumnMdp> colmdp;',a)
s=s[:a]+'''    // Four rate classes: two fitted weight groups per color. The MDP uses the
    // actual filler-aware rates; insertion/terminal weights and rate units remain
    // configurable through ColMdpConfig. One-step paper weights stay exact.
'''+s[b:]
def emit(n,text,d):
 p=root/'solutions'/n;p.mkdir();(p/'main.cpp').write_text(text)
 (p/'README.md').write_text('改良元: `solutions/deval-trim6`。\n\n'+d+'\n\n列MDPの旧分類を作って直後に全て上書きしていたループを除き、古い分類のコメントを更新。実験スイッチ・ログ・プロファイラ・目次は保つ。全予算固定、時刻による切替えはない。\n')
 assert len(text.encode())<=522000,(n,len(text.encode()))
 print(n,len(text.encode()))
emit('deval-trim6b',s,'旧分類の不要な初期化だけを除く。呼出し側・型分類・MDPの計算順は同じ。')
x=s.replace('    std::mt19937_64 rng(0x181ba71c83ULL ^ deval_seed_salt());','    const bool whole=search_mode&8;\n    std::mt19937_64 rng(0x181ba71c83ULL ^ deval_seed_salt());')
x=x.replace('        std::vector<int> anchor(d.U, -1), mobile(d.U), color(d.U);','        const auto units=d.unit;\n        std::vector<int> anchor(d.U, -1), mobile(d.U), color(d.U);')
x=x.replace('            int c = d.unit[i].c, a = anchor[i];\n            for (int j = 0; j < d.U; j++) {\n                int b = mobile[j];', '''            int c=d.unit[i].c;
            for (int j = 0; j < d.U; j++) {
                int a=whole?units[j].b:anchor[i],b=whole?units[j].a:mobile[j];''')
x=x.replace('if ((!flexible && int(d.hb[b] >> c & 1) != color[i]) || (a >= 0 && !d.ok[a][b])) continue;',
'''if(whole ? !d.valid({b,a,c},c) : ((!flexible && int(d.hb[b]>>c&1)!=color[i]) || (a>=0 && !d.ok[a][b])))continue;''')
x=x.replace('                cost[i][j] = v - weight * profit;', '''                if(whole) {
                    // Column sizes stay fixed, but pairs may change slots/colors.
                    const int nt=d.nt[c]+d.weight(units[j])-d.weight(units[i]);
                    const int p1=d.pairOne[c]+(a>=0)*int(d.hb[b]>>c&1)-(units[i].b>=0)*color[i];
                    v+=.5*(Design::least_depths2(d.nc[c],nt,p1)-Design::least_depths2(d.nc[c],d.nt[c],d.pairOne[c]));
                }
                cost[i][j] = v - weight * profit;''')
x=x.replace('                d.unit[x].a = mobile[assigned[x]];\n                d.unit[x].b = anchor[x];','''                if(whole){d.unit[x]=units[assigned[x]];d.unit[x].c=old.back().c;}
                else {d.unit[x].a=mobile[assigned[x]];d.unit[x].b=anchor[x];}''')
# Each accepted/rejected cycle must use reset rates of the current pair counts.
a=x.index('MatchStats rematch_probability(');b=x.index('// ==== Helper tables:',a)
section=x[a:b].replace('d.rebuild();','d.rebuild();if(whole)d.refresh_reset();')
x=x[:a]+section+x[b:]
x=x.replace('    const int late_iterations = int(env_real("ARGON_D2_LATE_ITERS", 1));','    const bool whole_units=extra==2;\n    const int late_iterations = int(env_real("ARGON_D2_LATE_ITERS", 1));')
x=x.replace('const int extra_mode=4;','const int extra_mode=4|(whole_units?8:0);')
emit('deval-unit-warm',x,'穴を保持する2回の再仕上げでは、最終Hungarianの割当てを1目標ずつでなく紙全体にする。単独/ペア構成とペア色をslotに固定しない。ペア互換性・列の両色・紙数は保ち、列のペア数変化を模型に反映する。巡回は通常の仕上げ目的で受理し、完成8候補をVで選ぶ。')
y=x.replace('const int extra_mode=4|(whole_units?8:0);','const int extra_mode=4|((whole_units && deval_salt==first_salt+7)?8:0);')
emit('deval-unit-last',y,'最後のwarm再仕上げ1回だけ、最終Hungarianで紙全体を再配置する。単独/ペア構成とペア色のslot固定を解除する。模型・合法性検査はdeval-unit-warmと同じ。完成8候補からVで選ぶ。')
