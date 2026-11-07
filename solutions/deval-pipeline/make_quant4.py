from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
for name,budget in [('deval-mdp-quant4',1),('deval-mdp-quant4x2',2)]:
 s=b
 s=s.replace('''    std::array<int, 4> radix{};''','''    std::array<int, 4> radix{}, type_colors{0,1,0,1};''',1)
 s=s.replace('''int iters, int max_length, long long max_full, long long max_sequences) {
        ok = false;''','''int iters, int max_length, long long max_full, long long max_sequences,
               std::array<int,4> colors={0,1,0,1}) {
        ok = false;type_colors=colors;''',1)
 s=s.replace('''        bool present[2] = {count[0] + count[2] > 0, count[1] + count[3] > 0};''','''        bool present[2] = {};for(int t=0;t<4;++t)present[type_colors[t]]|=count[t]>0;''',1)
 s=s.replace('full_first[2 * f + (s[j] & 1)]','full_first[2 * f + type_colors[s[j]]]')
 s=s.replace('(s[d] & 1) != b','type_colors[s[d]] != b',1)
 needle='''            for (int t = 0; t < 4; t++) rate[t] = count[t] ? weight[t] / count[t] / P : 0.0;'''
 assert needle in s;s=s.replace(needle,(P/'quant4.inc').read_text().replace('QUANT_BUDGET',str(budget)+'LL')+needle,1)
 s=s.replace('''                                 config.max_sequences))''','''                                 config.max_sequences,type_colors))''',1)
 # Remove only the now-stale descriptions of fixed frequency/color classes.
 s=s.replace('// A column paper has type 2 * (paired target) + handle color. States are type sequences.','// A column paper has one of four fitted weight classes, each with a fixed handle color. States are type sequences.',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-ordered8`。\n\n列MDPの紙の4種類をfiller込みの重みから選ぶ。同色内で重み順に分割し、2色へ1+3・2+2・3+1（または少ない群）の割り振りを比べ、群内二乗誤差を最小にする。完全状態数・部分状態数は各列の元の分類の{budget}倍以内、かつ既存上限以内とする。状態遷移の色は種類ごとに明示し、紙の個別重みを使う1注文先モデルは変えない。全予算固定、時計による切り替えなし。\n')
 print(name,len(s.encode()))
