from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-t11-interval-replace/main.cpp').read_text()
cond='''                    (interval_tie_mode && std::abs(best[cand[c][i].lvl]+cand[c][i].gain-best[c+1])<=1e-9)) {''';assert B.count(cond)==1
for name,score,desc in [
 ('few','cd.kind==0?-1:0','新たに取り出すfillerが少ない組'),
 ('many','cd.kind==0?1:0','新たに取り出すfillerが多い組'),
 ('wide','cd.c-cd.lvl+1','fillerがカバーできる取っ手区間の合計が長い組'),
 ('stay','cd.kind==2?1:0','そのまま再利用する旧fillerが多い組')]:
 start=B.index('    std::vector<Cand> best_intervals(');end=B.index('    // A filler from a column costs',start)
 s=B[start:end].replace('''        std::vector<int> pick(H + 1, -1);
        for (int c = 0; c < H; c++) {''','''        std::vector<int> pick(H + 1, -1);
        std::array<int,65> secondary{};
        auto tie_score=[](const Cand& cd){return '''+score+''';};
        for (int c = 0; c < H; c++) {''')
 s=s.replace('''            best[c + 1] = best[c];
            for (int i = 0; i < (int)cand[c].size(); i++)''','''            best[c + 1] = best[c];secondary[c+1]=secondary[c];
            for (int i = 0; i < (int)cand[c].size(); i++)''')
 s=s.replace(cond,'''                    (interval_tie_mode && std::abs(best[cand[c][i].lvl]+cand[c][i].gain-best[c+1])<=1e-9 &&
                     secondary[cand[c][i].lvl]+tie_score(cand[c][i])>=secondary[c+1])) {''')
 x='''                    pick[c + 1] = i;
                }''';assert s.count(x)==1
 s=s.replace(x,'''                    pick[c + 1] = i;
                    secondary[c+1]=secondary[cand[c][i].lvl]+tie_score(cand[c][i]);
                }''')
 s=B[:start]+s+B[end:]
 d=R/'solutions'/('dcomp-t11-interval-'+name)
 if d.exists():assert (d/'main.cpp').read_text()==s
 else:d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-interval-replace\n\njoint fillerの区間DPの一次目的は変えず、その目的値が同じ場合だけ'+desc+'を優先する。二次目的も同じなら後の区間を選ぶ。追加の計画は作らない。weighted/complete-valueのDPは元の選択を維持する。\n\n既存固定予算・両コンパイラ共通設定・ログ・実験スイッチ・profiler・目次と段・DesignStoreを保持する。\n')
