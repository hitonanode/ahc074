from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-combo-dual30/main.cpp').read_text()
a=s.index('    __attribute__((target("avx2,popcnt"))) double adaptive_next_cost(');b=s.index('    // Lexicographic permutation rank',a);f=s[a:b]
old='const bool mdp_scan = colmdp_next && colmdp_columns == H;'
assert f.count(old)==1;f=f.replace(old,'''// With the default zero one-step subtraction, only type sequences
        // determine the MDP term, even when some columns exceed the state limit.
        const bool mdp_scan = colmdp_next && (colmdp_columns == H || colmdp_next_drop == 0);''')
f=f.replace('cost += colmdp_next_scanned(mdp_code, cost);','cost += colmdp_columns == H ? colmdp_next_scanned<true>(mdp_code, cost) : colmdp_next_scanned<false>(mdp_code, cost);')
s=s[:a]+f+s[b:]
a=s.index('    double colmdp_next_scanned(');b=s.index('    // A partial-coverage case',a);f=s[a:b]
old='''        double term = -colmdp_next_drop * cost;
        for (int c = 0; c < H; c++) {'''
new='''        // The partial formula starts at +0 and adds covered columns in order.
        // Its one-step terms are multiplied by exactly zero in this branch.
        double term = All ? -colmdp_next_drop * cost : 0.0;
        for (int c = 0; c < H; c++) {
            if constexpr (!All) if (!colmdp[c].ok) continue;'''
assert f.count(old)==1;f=f.replace(old,new);f=f.replace("    double colmdp_next_scanned(","    template<bool All=true> double colmdp_next_scanned(");s=s[:a]+f+s[b:]
p=r/'solutions/ia-mdp-types';p.mkdir(exist_ok=False);(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/dcomp-combo-dual30。

既定のCOLMDP_NEXTKEEP=1では、次状態の列MDPの加算時に1注文の費用を差し引かない（colmdp_next_drop=0）。このとき部分的にしか列MDPを用意できなかったケースでも、MDPの値は列内の紙の種類列だけで決まる。通常のnext_costの走査で種類列を符号化し、全列MDP用の正確な小cacheを、対応した列だけに使う。

従来の部分経路は、紙ID列を記録し、紙ごとの重みと色修復費用を計算した後に0を掛けていた。その計算を省く。列のMDPがない列は同じように無視する。加算する列の順と各列のF値、その他の1注文費用は不変。COLMDP_NEXTKEEPを変えた実験の非zero差引き経路は従来の計算を維持する。

NEXT_PREFIX_CHECKで全missの結果を元の費用関数とdouble全bit比較できる。乱数、探索量、設計、ログと操作属性、時計、DesignStoreを保つ。小さな速度probe用。全列/部分列はtemplateで分け、全列経路のloopに追加分岐を置かない。
''')
